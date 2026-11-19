#!/usr/bin/env python3
"""把一本 EPUB 原样挂到站点上，生成 /read/<slug>/ 阅读页。

正文一个字都不进上下文：只读 EPUB 的 OPF 拿书名，其余原样拷过去，
由前端的 epub.js 在浏览器里解包渲染。

    python3 tools/newbook.py --file ~/book.epub
    python3 tools/newbook.py --file ~/book.epub --slug k3f9x2 --title "书名"

产物：
    read/<slug>/book.epub       原文件
    read/<slug>/index.html      阅读页（tools/read_template.html 填出来的）
    read/index.html             书架，扫 read/*/ 自动重建
"""
import argparse
import os
import re
import secrets
import shutil
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
READ = os.path.join(ROOT, "read")
TPL = os.path.join(ROOT, "tools", "read_template.html")


def die(msg):
    print("✗ " + msg, file=sys.stderr)
    sys.exit(1)


def epub_title(path):
    """只解析 container.xml → OPF 取 <dc:title>，不碰正文。"""
    try:
        with zipfile.ZipFile(path) as z:
            cont = z.read("META-INF/container.xml").decode("utf-8", "ignore")
            m = re.search(r'full-path="([^"]+)"', cont)
            if not m:
                return None
            opf = z.read(m.group(1)).decode("utf-8", "ignore")
            t = re.search(r"<dc:title[^>]*>(.*?)</dc:title>", opf, re.S | re.I)
            if not t:
                return None
            return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", t.group(1))).strip() or None
    except Exception:
        return None


def check_epub(path):
    if not os.path.isfile(path):
        die("找不到文件：%s" % path)
    if not zipfile.is_zipfile(path):
        die("不是有效的 EPUB（zip 结构坏了）：%s" % path)
    with zipfile.ZipFile(path) as z:
        if "META-INF/container.xml" not in z.namelist():
            die("没有 META-INF/container.xml，这大概是 cbz/docx 而不是 epub")
        if not any(n.lower().endswith((".opf",)) for n in z.namelist()):
            die("包里没有 OPF，不是标准 EPUB")


def build_page(slug, title):
    tpl = open(TPL, encoding="utf-8").read()
    html = (tpl.replace("{{TITLE}}", title)
               .replace("{{SLUG}}", repr(slug).replace("'", '"')))
    left = set(re.findall(r"\{\{[A-Z_]+\}\}", html))
    if left:
        die("模板里还剩占位符：%s" % " ".join(sorted(left)))
    return html


def build_shelf():
    rows = []
    if os.path.isdir(READ):
        for name in sorted(os.listdir(READ)):
            idx = os.path.join(READ, name, "index.html")
            if not os.path.isfile(idx):
                continue
            s = open(idx, encoding="utf-8").read()
            m = re.search(r"<title>(.*?)</title>", s, re.S)
            t = re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else name
            size = os.path.getsize(os.path.join(READ, name, "book.epub")) if os.path.exists(
                os.path.join(READ, name, "book.epub")) else 0
            rows.append((name, t, size))
    li = "\n".join(
        '<a class="bk" href="%s/"><span class="t">%s</span><span class="m">%s MB</span></a>'
        % (n, t.replace("&", "&amp;").replace("<", "&lt;"), ("%.1f" % (s / 1048576.0)))
        for n, t, s in rows) or '<p class="empty">书架是空的。</p>'
    html = """<!doctype html>
<html lang="zh-CN" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>书架</title>
<style>
:root{--bg:#0a0c10;--text:#dfe5ec;--muted:#98a2b0;--border:#191d24;--accent:#6aa2d8;
--sans:-apple-system,BlinkMacSystemFont,"PingFang SC","Noto Sans CJK SC",system-ui,sans-serif;
--mono:ui-monospace,Menlo,monospace}
@media (prefers-color-scheme:light){:root{--bg:#f3f5f8;--text:#1e2935;--muted:#526070;--border:#dfe4ea;--accent:#2d6496}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:var(--sans);
 padding:calc(48px + env(safe-area-inset-top)) 20px calc(40px + env(safe-area-inset-bottom))}
h1{font-size:1.15rem;margin:0 0 4px;letter-spacing:-.01em}
.sub{font-family:var(--mono);font-size:.7rem;color:var(--muted);margin-bottom:26px}
.list{max-width:620px;margin:0 auto;display:flex;flex-direction:column;gap:2px}
.bk{display:flex;align-items:baseline;gap:12px;padding:15px 4px;text-decoration:none;
 color:inherit;border-bottom:1px solid var(--border);transition:padding-left .15s}
.bk:active{padding-left:10px}
.bk .t{flex:1;font-size:.94rem;line-height:1.4}
.bk .m{flex:none;font-family:var(--mono);font-size:.68rem;color:var(--muted)}
.empty{color:var(--muted);font-size:.85rem}
</style>
</head>
<body><div class="list"><h1>书架</h1><div class="sub">%d 本 · 链接不外传</div>
%s
</div></body></html>
""" % (len(rows), li)
    open(os.path.join(READ, "index.html"), "w", encoding="utf-8").write(html)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, help="epub 路径")
    ap.add_argument("--title", help="书名，默认从 EPUB 元数据取")
    ap.add_argument("--slug", help="目录名，默认随机 6 位（不可猜）")
    a = ap.parse_args()

    check_epub(a.file)
    title = a.title or epub_title(a.file) or os.path.splitext(os.path.basename(a.file))[0]
    slug = a.slug or secrets.token_hex(3)
    if not re.match(r"^[a-z0-9][a-z0-9-]{1,40}$", slug):
        die("slug 只能用小写字母/数字/连字符：%s" % slug)

    dst = os.path.join(READ, slug)
    os.makedirs(dst, exist_ok=True)
    shutil.copyfile(a.file, os.path.join(dst, "book.epub"))
    open(os.path.join(dst, "index.html"), "w", encoding="utf-8").write(build_page(slug, title))
    build_shelf()

    size = os.path.getsize(os.path.join(dst, "book.epub")) / 1048576.0
    print("✓ %s  (%.1f MB)" % (title, size))
    print("  read/%s/" % slug)
    print("  https://patrick12138.github.io/read/%s/" % slug)
    print("  https://patrick12138.github.io/read/  （书架）")


if __name__ == "__main__":
    main()
