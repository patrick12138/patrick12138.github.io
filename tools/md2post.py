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
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime

import markdown
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(ROOT, "tools", "post_template.html")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120 Safari/537.36")
MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]
WIKI = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")


# ─── md 解析 ───────────────────────────────────────────────
def split_front(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return {}, text
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        meta = {}
    return meta, text[m.end():]


def unwiki(s):
    return WIKI.sub(lambda m: (m.group(2) or m.group(1)).split("/")[-1], str(s))


def clean_author(v):
    if not v:
        return ""
    if isinstance(v, (list, tuple)):
        return "、".join([p for p in (clean_author(x) for x in v) if p])
    return unwiki(v).strip()


def norm(s):
    return re.sub(r"\s+", "", unwiki(s))


def strip_title_heading(body, title):
    lines = body.split("\n")
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines):
        m = re.match(r"^#{1,3}\s+(.+)$", lines[i].strip())
        if m and norm(m.group(1)) == norm(title):
            lines = lines[:i] + lines[i + 1:]
    return "\n".join(lines)


def pull_source_block(body):
    """把开头的“来源：”段落（可能是紧跟的列表）抽出来，返回 (来源文本, 去掉它的正文)。"""
    lines = body.split("\n")
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines) or not re.match(r"^(来源|Source)[:：]", lines[i].strip(), re.I):
        return "", body
    j = i + 1
    chunk = [lines[i]]
    while j < len(lines):
        s = lines[j].strip()
        if not s:
            j += 1
            continue
        if re.match(r"^[-*+]\s+", s) or s.startswith("[["):
            chunk.append(s)
            j += 1
            continue
        break
    items = []
    for ln in chunk:
        s = re.sub(r"^\s*[-*+]\s+", "", ln.strip())
        s = re.sub(r"^(来源|Source)[:：]\s*", "", s, flags=re.I)
        if s:
            items.append(s)
    text = " · ".join(items)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)   # 链接只留文字
    text = unwiki(text).replace("[[", "").replace("]]", "")
    text = re.sub(r"\s*·\s*·\s*", " · ", text)
    return re.sub(r"\s{2,}", " ", text).strip(), "\n".join(lines[:i] + lines[j:])



def strip_empty_svg(body):
    """删掉「空 path + textPath」的装饰 SVG：渲染不出内容，却白占 200px 高度。"""
    import re as _re

    def repl(m):
        svg = m.group(0)
        if _re.search(r'<path[^>]*id="[^"]*"[^>]*>\s*</path>', svg) and '<textPath' in svg:
            return ""
        return svg

    body = _re.sub(r"<svg\b[^>]*>.*?</svg>", repl, body, flags=_re.S)
    body = _re.sub(r"<p[^>]*>\s*</p>", "", body)
    return body


def video_to_link(body):
    """内嵌 <video> 改成外链文字，不做播放器。"""
    import re as _re

    def repl(m):
        m2 = _re.search(r'src="([^"]+)"', m.group(0))
        if not m2:
            return ""
        return '\n\n[观看视频 →](%s)\n\n' % m2.group(1)

    body = _re.sub(r"<video[^>]*>.*?</video>|<video[^>]*/?>", repl, body, flags=_re.S)
    body = _re.sub(r"<iframe[^>]*src=\"([^\"]+)\"[^>]*>.*?</iframe>", r"\n\n[打开嵌入内容 →](\1)\n\n", body, flags=_re.S)
    return body


def normalize_md(body):
    body = strip_empty_svg(body)
    body = video_to_link(body)
    """剪藏 md 的排版修补：反转义、给标题/列表补空行（跳过代码块）。"""
    body = body.replace("\r\n", "\n")
    body = re.sub(r"\\([`*_\[\]#()!+])", r"\1", body)
    out, fence = [], False
    for ln in body.split("\n"):
        st = ln.strip()
        if st.startswith("```") or st.startswith("~~~"):
            fence = not fence
            out.append(ln)
            continue
        if fence:
            out.append(ln)
            continue
        glued = re.search(r"(?<=[^\s|])(#{2,6}\s+\S)", ln)
        if glued and not st.startswith("#"):
            out.append("")
            ln = ln[:glued.start(1)] + "\n\n" + ln[glued.start(1):]
            st = ln.strip()
        is_head = re.match(r"^#{1,6}\s+\S", st)
        is_item = re.match(r"^([-*+]|\d+\.)\s+\S", st)
        if (is_head or is_item) and out:
            prev = out[-1]
            ps = prev.strip()
            if (ps and not re.match(r"^([-*+]|\d+\.)\s+", ps)
                    and not re.match(r"^#{1,6}\s", ps) and not ps.startswith("|")
                    and not prev.startswith("    ") and not ps.endswith("|")):
                out.append("")
        out.append(ln)
    return "\n".join(out)


def strip_clip_junk(body):
    out = []
    for line in body.split("\n"):
        s = line.strip()
        if re.match(r"^\[See all posts\]\(.*\)$", s):
            continue
        if re.match(r"^\[回到顶部\]", s):
            continue
        if s in ("本文由作者授权发布", "原文链接"):
            continue
        out.append(line)
    body = "\n".join(out)
    body = re.sub(r"(?m)^#{1,4}\s*(目录|目錄|Table of Contents)\s*\n(?=\s*(#{1,4}\s|\Z))", "", body)
    return body


def first_paragraph(body, limit=120):
    for block in re.split(r"\n\s*\n", body):
        b = block.strip()
        if not b or b.startswith("#") or b.startswith("|") or b.startswith("!["):
            continue
        b = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", b)
        b = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", b)
        b = re.sub(r"^[->*\s]+", "", b)
        b = unwiki(b).replace("**", "").replace("`", "")
        b = re.sub(r"\s+", "", b) if re.search(r"[\u4e00-\u9fff]", b) else re.sub(r"\s+", " ", b)
        if len(b) < 8:
            continue
        return b if len(b) <= limit else b[:limit].rstrip("，、, ") + "…"
    return ""


# ─── 图片 ──────────────────────────────────────────────────
def optimize_image(path, max_w=1400, quality=82):
    """位图转 webp 并压到合理体积（svg/gif 原样保留）。"""
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
        im.save(new_path, "WEBP", quality=quality, method=5)
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
    if isinstance(v, (datetime, date)):
        return v.date() if isinstance(v, datetime) else v
    if isinstance(v, str):
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", v.strip())
        if m:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return None


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
        vault_prefix = config.load()["vault_root"].rstrip("/") + "/"
        rel_md = md_path
        if md_path.startswith(vault_prefix):
            rel_md = md_path[len(vault_prefix):]
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
