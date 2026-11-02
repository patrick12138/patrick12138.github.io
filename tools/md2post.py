#!/usr/bin/env python3
"""把 Obsidian 剪藏/笔记 md 转成站点文章页。

用法：
  python3 tools/md2post.py <md路径> <slug> [--date YYYY-MM-DD] [--author 名字]
                                      [--kind repost|own] [--no-images]

- 模板直接从已有的 posts/git-worktree/index.html 里切，保证样式永远一致。
- 图片下载到 assets/posts/<slug>/，正文里改成相对路径。
- 只生成 posts/<slug>/index.html，首页列表要手动加一条 <li>。
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
TEMPLATE = os.path.join(ROOT, "posts", "git-worktree", "index.html")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
MONTHS = ["January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]


def split_front(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return {}, text
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        meta = {}
    return meta, text[m.end():]


def clean_author(v):
    if not v:
        return ""
    if isinstance(v, (list, tuple)):
        parts = [clean_author(x) for x in v]
        return "、".join([p for p in parts if p])
    s = str(v)
    s = re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", lambda m: (m.group(2) or m.group(1)), s)
    return s.strip()


def norm(s):
    s = re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", lambda m: (m.group(2) or m.group(1)), s)
    return re.sub(r"\s+", "", s)


def strip_title_heading(body, title):
    """去掉正文开头与标题重复的那一行（剪藏常把标题再写一遍）。"""
    lines = body.split("\n")
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines):
        ln = lines[i].strip()
        m = re.match(r"^#{1,3}\s+(.+)$", ln)
        if m and norm(m.group(1)) == norm(title):
            lines = lines[:i] + lines[i + 1:]
            body = "\n".join(lines)
    return body


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
    # 干掉只剩标题没有内容的「目录 / Table of Contents」
    body = "\n".join(out)
    body = re.sub(r"(?m)^#{1,4}\s*(目录|目錄|Table of Contents)\s*\n(?=\s*(#{1,4}\s|\Z))", "", body)
    return body


def optimize_image(path, max_w=1400, quality=82):
    """位图转 webp 并压到合理体积（svg/gif 原样保留）。"""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".svg", ".gif"):
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
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
        else:
            im = im.convert("RGB")
        new_path = os.path.splitext(path)[0] + ".webp"
        im.save(new_path, "WEBP", quality=quality, method=5)
        if os.path.getsize(new_path) < os.path.getsize(path) or new_path != path:
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
    if not os.path.exists(path):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": urllib.parse.urlparse(url).scheme + "://" + urllib.parse.urlparse(url).netloc + "/"})
        with urllib.request.urlopen(req, timeout=45) as r, open(path, "wb") as f:
            f.write(r.read())
    path = optimize_image(path)
    name = os.path.basename(path)
    return "../../assets/posts/%s/%s" % (slug, name), os.path.getsize(path)


def localize_images(body, slug):
    stats = []
    md_img = re.compile(r"!\[([^\]]*)\]\((https?://[^\s)]+)(?:\s+\"[^\"]*\")?\)")
    html_img = re.compile(r"(<img[^>]+src=\")(https?://[^\"]+)(\")")

    def repl_md(m):
        alt, url = m.group(1), m.group(2)
        try:
            local, size = fetch_asset(url, slug)
            stats.append(size)
            return "![%s](%s)" % (alt, local)
        except Exception as e:  # 下载失败就保留远程地址，不要中断
            print("  ! 图片失败保留远程: %s (%s)" % (url, e), file=sys.stderr)
            return m.group(0)

    def repl_html(m):
        try:
            local, size = fetch_asset(m.group(2), slug)
            stats.append(size)
            return m.group(1) + local + m.group(3)
        except Exception as e:
            print("  ! 图片失败保留远程: %s (%s)" % (m.group(2), e), file=sys.stderr)
            return m.group(0)

    body = md_img.sub(repl_md, body)
    body = html_img.sub(repl_html, body)
    return body, stats


def to_date(v, fallback=None):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if isinstance(v, str):
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", v.strip())
        if m:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    return fallback


def fmt_date(d):
    return "%s %d, %d" % (MONTHS[d.month - 1], d.day, d.year)


def build(md_path, slug, date_arg=None, author_arg=None, kind="repost", images=True):
    raw = open(md_path, encoding="utf-8").read()
    meta, body = split_front(raw)
    title = str(meta.get("title") or os.path.splitext(os.path.basename(md_path))[0]).strip()
    source = str(meta.get("source") or "").strip()
    desc = re.sub(r"^\s*-\s*", "", str(meta.get("description") or "")).strip()
    author = author_arg or clean_author(meta.get("author")) or ""
    d = to_date(date_arg) or to_date(meta.get("published")) or date.today()

    body = strip_clip_junk(strip_title_heading(body, title))
    if images:
        body, sizes = localize_images(body, slug)
        if sizes:
            print("  图片 %d 张，共 %.1f MB" % (len(sizes), sum(sizes) / 1048576))
    html_body = markdown.markdown(
        body, extensions=["extra", "sane_lists", "fenced_code", "tables", "nl2br"], output_format="html5"
    )
    html_body = re.sub(r"</p>\s*<p>", "</p>\n<p>", html_body)

    tpl = open(TEMPLATE, encoding="utf-8").read()
    head, rest = tpl.split('<div class="wrap"><article class="article">', 1)
    tail = rest[rest.index('<a class="back"'):]
    head = re.sub(r"<title>.*?</title>", "<title>%s · patrick</title>" % htmllib.escape(title), head, flags=re.S)
    head = re.sub(r'<meta name="description" content="[^"]*">',
                  '<meta name="description" content="%s">' % htmllib.escape(desc or title), head, count=1)
    head = head.replace('href="../../" class=""', 'href="../../"')

    meta_bits = [fmt_date(d)]
    if author:
        meta_bits.append(htmllib.escape(author))
    meta_bits.append("搬运" if kind == "repost" else "原创")
    meta_line = " · ".join(meta_bits)

    src_block = ""
    if source:
        src_block = ('<aside class="source"><span class="src-label">搬运自</span>'
                     '<a class="src-url" href="%s" target="_blank" rel="noopener">%s</a></aside>'
                     % (htmllib.escape(source), htmllib.escape(source)))

    out = (head + '<div class="wrap"><article class="article"><h1>' + htmllib.escape(title) + "</h1>"
           + '<div class="meta">' + meta_line + "</div>" + src_block
           + '<div class="body">' + html_body.rstrip() + "</div>\n" + tail)

    page_dir = os.path.join(ROOT, "posts", slug)
    os.makedirs(page_dir, exist_ok=True)
    out_path = os.path.join(page_dir, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out)
    print("  → posts/%s/index.html  %.1f KB" % (slug, len(out.encode()) / 1024))
    return {"slug": slug, "title": title, "desc": desc, "date": d, "author": author, "kind": kind}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("md")
    ap.add_argument("slug")
    ap.add_argument("--date")
    ap.add_argument("--author")
    ap.add_argument("--kind", default="repost", choices=["repost", "own"])
    ap.add_argument("--no-images", action="store_true")
    a = ap.parse_args()
    print("· %s" % a.md)
    info = build(a.md, a.slug, a.date, a.author, a.kind, not a.no_images)
    print("  %s | %s | %s" % (fmt_date(info["date"]), info["author"] or "-", info["title"]))


if __name__ == "__main__":
    main()
