#!/usr/bin/env python3
"""把 Obsidian 的剪藏 md / 浓缩笔记 md 转成站点文章页。

用法：
  # 搬运文章（有 frontmatter：title / source / author / published / description）
  python3 tools/md2post.py "<md>" <slug> [--author 名字] [--date YYYY-MM-DD] [--kind repost]

  # 自己的浓缩笔记（没有 frontmatter，标题取第一个 H1，来源取“来源：”那段）
  python3 tools/md2post.py "<md>" <slug> --kind own [--date YYYY-MM-DD]

- 模板是 tools/post_template.html（纯占位符，不依赖任何一篇文章）。
- 图片下载到 assets/posts/<slug>/，正文里改成相对路径。
- 只生成 posts/<slug>/index.html；首页由 tools/gen_index.py 全自动扫描生成，不用手改。
- 生成后自动把记录同步进 tools/sources.json，rebuild.py 随时可全量重生成。
"""
import argparse
import hashlib
import html as htmllib
import os
import re
import dates
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime

import markdown
import yaml

from mdclean import (clean_author, first_paragraph, normalize_md,
                     pull_source_block, split_front, strip_clip_junk,
                     strip_title_heading, unwiki)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(ROOT, "tools", "post_template.html")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]


# ─── 图片 ──────────────────────────────────────────────────
def optimize_image(path, max_w=None, quality=None):
    """位图转 webp 并压到合理体积（svg/gif 原样保留）。参数默认值来自 tools/config.py 的 IMG。"""
    max_w = max_w or config.IMG["max_w"]
    quality = quality or config.IMG["quality"]
    if os.path.splitext(path)[1].lower() in (".svg", ".gif"):
        return path
    try:
        from PIL import Image
    except ImportError:
        return path
    try:
        im = Image.open(path)
        im.load()
        if im.width > max_w:
            im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
        im = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB")
        new_path = os.path.splitext(path)[0] + ".webp"
        im.save(new_path, "WEBP", quality=quality, method=config.IMG["method"])
        if os.path.abspath(new_path) != os.path.abspath(path):
            os.remove(path)
        return new_path
    except Exception as e:
        print("  ! 压缩失败保留原图 %s (%s)" % (os.path.basename(path), e), file=sys.stderr)
        return path


def fetch_asset(url, slug):
    ext = os.path.splitext(urllib.parse.urlparse(url).path)[1].lower()
    if ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"):
        ext = ".png"
    name = hashlib.sha1(url.encode()).hexdigest()[:12] + ext
    folder = os.path.join(ROOT, "assets", "posts", slug)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, name)
    webp = os.path.splitext(path)[0] + ".webp"
    if ext != ".webp" and os.path.exists(webp):
        return "../../assets/posts/%s/%s" % (slug, os.path.basename(webp)), os.path.getsize(webp)
    if not os.path.exists(path):
        p = urllib.parse.urlparse(url)
        req = urllib.request.Request(url, headers={"User-Agent": UA,
                                                  "Referer": "%s://%s/" % (p.scheme, p.netloc)})
        with urllib.request.urlopen(req, timeout=45) as r, open(path, "wb") as f:
            f.write(r.read())
    path = optimize_image(path)
    return "../../assets/posts/%s/%s" % (slug, os.path.basename(path)), os.path.getsize(path)


def localize_images(body, slug):
    sizes = []
    md_img = re.compile(r"!\[([^\]]*)\]\((https?://[^\s)]+)(?:\s+\"[^\"]*\")?\)")
    html_img = re.compile(r"(<img[^>]+src=\")(https?://[^\"]+)(\")")

    def repl_md(m):
        try:
            local, size = fetch_asset(m.group(2), slug)
            sizes.append(size)
            return "![%s](%s)" % (m.group(1), local)
        except Exception as e:
            print("  ! 图片失败保留远程: %s (%s)" % (m.group(2), e), file=sys.stderr)
            return m.group(0)

    def repl_html(m):
        try:
            local, size = fetch_asset(m.group(2), slug)
            sizes.append(size)
            return m.group(1) + local + m.group(3)
        except Exception as e:
            print("  ! 图片失败保留远程: %s (%s)" % (m.group(2), e), file=sys.stderr)
            return m.group(0)

    return html_img.sub(repl_html, md_img.sub(repl_md, body)), sizes


# ─── 时间 ──────────────────────────────────────────────────
def to_date(v):
    """任意写法 → date；认不出来 None。解析逻辑在 tools/dates.py。"""
    return dates.to_date(v)


def fmt_date(d):
    """中文日期：2026年10月15日"""
    return "%d年%d月%d日" % (d.year, d.month, d.day)


# ─── 生成 ──────────────────────────────────────────────────
def build(md_path, slug, date_arg=None, author_arg=None, kind="repost",
          images=True, title_arg=None, desc_arg=None):
    raw = open(md_path, encoding="utf-8").read().replace("\ufeff", "")   # 去 BOM，否则首个 H1 识别不到
    meta, body = split_front(raw)

    title = str(title_arg or meta.get("title") or "").strip()
    if not title:
        m = re.search(r"(?m)^#\s+(.+)$", body)
        title = m.group(1).strip() if m else os.path.splitext(os.path.basename(md_path))[0]
    source = str(meta.get("source") or "").strip()
    desc = re.sub(r"^\s*-\s*", "", str(desc_arg or meta.get("description") or "")).strip()
    author = author_arg or clean_author(meta.get("author")) or ""

    body = strip_title_heading(body, title)
    source_note, body = pull_source_block(body)
    body = unwiki(strip_clip_junk(normalize_md(body)))
    if not desc:
        desc = first_paragraph(body)

    d = to_date(date_arg) or to_date(meta.get("published")) or to_date(meta.get("created")) \
        or datetime.fromtimestamp(os.path.getmtime(md_path)).date()

    if images:
        body, sizes = localize_images(body, slug)
        if sizes:
            print("  图片 %d 张，共 %.1f MB" % (len(sizes), sum(sizes) / 1048576))

    html_body = markdown.markdown(
        body, extensions=["extra", "sane_lists", "fenced_code", "tables", "nl2br"],
        output_format="html5")
    html_body = re.sub(r"</p>\s*<p>", "</p>\n<p>", html_body)
    # 排版收尾：空段落、中文句中硬换行、中文标点前的空格
    html_body = re.sub(r"<p>(?:\s|&nbsp;)*</p>", "", html_body)
    html_body = re.sub(r"(?<=[\u4e00-\u9fff，。；：！？、）])[ \t]*<br ?/?>[ \t]*(?=[\u4e00-\u9fff])", "", html_body)
    html_body = re.sub(r"(?<=[\u4e00-\u9fff>])[ \t]+(?=[，。；：！？、])", "", html_body)
    html_body = re.sub(r"\n[ \t]+\n", "\n\n", html_body)
    html_body = re.sub(r"\n{3,}", "\n\n", html_body)
    # 移动端 WebView（含 Minis 内置浏览器）不处理 target=_blank，点了没反应；一律同窗跳转
    html_body = re.sub(r'\s+target="_blank"', "", html_body)

    tpl = open(TEMPLATE, encoding="utf-8").read()
    kind_repost_on = "on" if kind == "repost" else ""
    kind_own_on = "on" if kind == "own" else ""

    bits = [fmt_date(d)]
    if author:
        bits.append(htmllib.escape(author))
    bits.append("搬运" if kind == "repost" else "个人")

    src_block = ""
    if source:
        src_block = ('<aside class="source"><span class="src-label">搬运自</span>'
                     '<a class="src-url" href="%s">%s</a></aside>'
                     % (htmllib.escape(source), htmllib.escape(source)))
    elif source_note:
        src_block = ('<aside class="source"><span class="src-label">来源</span>%s</aside>'
                     % htmllib.escape(source_note))

    out = (tpl
           .replace("{{TITLE}}", htmllib.escape(title))
           .replace("{{DESCRIPTION}}", htmllib.escape(desc or title))
           .replace("{{META}}", " · ".join(bits))
           .replace("{{SOURCE_BLOCK}}", (src_block + "\n") if src_block else "")
           .replace("{{BODY}}", html_body.rstrip())
           .replace("{{BACK_HREF}}", "../../")
           .replace("{{KIND_REPOST_ON}}", kind_repost_on)
           .replace("{{KIND_OWN_ON}}", kind_own_on)
           .replace("{{SLUG}}", slug))

    page_dir = os.path.join(ROOT, "posts", slug)
    os.makedirs(page_dir, exist_ok=True)
    with open(os.path.join(page_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(out)
    print("  → posts/%s/index.html  %.1f KB" % (slug, len(out.encode()) / 1024))
    
    # 自动同步记录进 tools/sources.json，保证 rebuild.py 随时可用
    sync_to_sources_json(slug, md_path, author, d, kind, title_arg)

    return {"slug": slug, "title": title, "desc": desc, "date": d, "author": author, "kind": kind}


def sync_to_sources_json(slug, md_path, author, d, kind, title_arg=None):
    """把这篇登记进 sources.json（只写显式 --title，不把推导出的 H1 写脏）。"""
    import json
    json_path = os.path.join(ROOT, "tools", "sources.json")
    if not os.path.exists(json_path):
        return
    try:
        rows = json.load(open(json_path, encoding="utf-8"))
        import config
        # 归一再比：Windows 上 os.path.join 会给出混合分隔符（C:/a\b），
        # 直接 startswith 比不过，整条绝对路径就会写进 sources.json（换机器即废）。
        vault_root = os.path.normpath(config.load()["vault_root"])
        if os.path.normcase(os.path.normpath(md_path)).startswith(
                os.path.normcase(vault_root) + os.sep):
            rel_md = os.path.relpath(md_path, vault_root).replace(os.sep, "/")
        else:
            rel_md = md_path
        date_str = "%s %d, %d" % (MONTHS[d.month - 1], d.day, d.year) if d else ""
        found = False
        for r in rows:
            if r.get("slug") == slug:
                r["md"] = rel_md
                if author: r["author"] = author
                if date_str: r["date"] = date_str
                r["kind"] = kind
                if title_arg: r["title"] = str(title_arg).strip()
                found = True
                break
        if not found:
            rows.append({
                "slug": slug,
                "md": rel_md,
                "author": author or "",
                "date": date_str,
                "kind": kind,
                "title": str(title_arg).strip() if title_arg else ""
            })
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False, indent=1)
            f.write("\n")
        print("  ✓ 已自动同步至 tools/sources.json (当前共 %d 篇)" % len(rows))
    except Exception as e:
        print("  ! 同步 sources.json 失败: %s" % e, file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("md")
    ap.add_argument("slug")
    ap.add_argument("--date")
    ap.add_argument("--author")
    ap.add_argument("--title", help="覆盖标题（爬下来的页面标题往往很脏）")
    ap.add_argument("--desc", help="覆盖摘要（首页列表用）")
    ap.add_argument("--kind", default="repost", choices=["repost", "own"])
    ap.add_argument("--no-images", action="store_true")
    a = ap.parse_args()
    print("· %s" % a.md)
    info = build(a.md, a.slug, a.date, a.author, a.kind, images=not a.no_images, title_arg=a.title)
    print("  %s | %s | %s" % (fmt_date(info["date"]), info["author"] or "-", info["title"]))


if __name__ == "__main__":
    main()
