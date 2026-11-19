#!/usr/bin/env python3
"""把一本 EPUB 拆成静态章节挂到站点上：/read/<slug>/。

不经过 epub.js —— 那套在部分 WebView 里会因为 srcdoc iframe 不发 load 事件
把渲染队列卡死。这里在构建时就把书拆开，正文一个字都不进上下文。

    python3 tools/newbook.py --file ~/book.epub
    python3 tools/newbook.py --file ~/book.epub --slug k3f9x2 --title "书名"

产物（每次覆盖重建）：
    read/<slug>/index.html      阅读器（单页滚读，目录/字号/三色底/进度记忆）
    read/<slug>/book.json       章节目录 + 每章字数
    read/<slug>/ch/<n>.html     章节正文片段（注入 #doc）
    read/<slug>/a/...           图片、字体等资源，保持原包内相对结构
    read/index.html             书架，扫 read/*/ 自动重建
"""
import argparse
import html as htmllib
import json
import os
import posixpath
import re
import secrets
import shutil
import sys
import unicodedata
import urllib.parse
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
READ = os.path.join(ROOT, "read")
TPL = os.path.join(ROOT, "tools", "read_template.html")

# 出版信息、内嵌目录这类章节对读者没有价值，直接不生成（目录走侧边抽屉）
JUNK_TITLE = re.compile(
    r"^\s*(版权|版权页|版权信息|目录|目\s*录|扉页|封面|书名页|出版信息|出版说明|"
    r"内容简介|内容提要|关于作者|Contents|Table of Contents|Cover|Title\s*Page|"
    r"Copyright|Colophon)\s*$", re.I)
JUNK_TEXT = re.compile(r"图书在版编目|CIP数据|责任编辑|装帧设计|出版发行|印刷厂|ISBN\s*978")

ATTR_RE = re.compile(r'\b(src|href|xlink:href|poster)\s*=\s*(["\'])(.*?)\2', re.I | re.S)
SCRIPT_RE = re.compile(r"<script\b[^>]*>.*?</script>", re.I | re.S)
STYLE_RE = re.compile(r"<style\b[^>]*>.*?</style>", re.I | re.S)
BODY_RE = re.compile(r"<body\b[^>]*>(.*?)</body>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")


def die(msg):
    print("✗ " + msg, file=sys.stderr)
    sys.exit(1)


def text_len(s):
    return len(re.sub(r"\s+", "", htmllib.unescape(TAG_RE.sub(" ", s))))


def parse_opf(z):
    """返回 (opf 所在目录, manifest{id: (href, type)}, spine[href], title, creator, ncx 路径)"""
    try:
        cont = z.read("META-INF/container.xml").decode("utf-8", "ignore")
    except KeyError:
        die("包里没有 META-INF/container.xml，不是标准 EPUB")
    m = re.search(r'full-path="([^"]+)"', cont)
    if not m:
        die("container.xml 里找不到 rootfile")
    opf_path = m.group(1)
    base = posixpath.dirname(opf_path)
    opf = z.read(opf_path).decode("utf-8", "ignore")

    manifest = {}
    for tag in re.findall(r"<item\b[^>]*>", opf):
        i = re.search(r'\bid="([^"]+)"', tag)
        h = re.search(r'\bhref="([^"]+)"', tag)
        if not (i and h):
            continue
        t = re.search(r'media-type="([^"]+)"', tag)
        manifest[i.group(1)] = (htmllib.unescape(h.group(1)), t.group(1) if t else "")

    spine = []
    for tag in re.findall(r"<itemref\b[^>]*>", opf):
        r = re.search(r'idref="([^"]+)"', tag)
        if r and r.group(1) in manifest:
            spine.append(manifest[r.group(1)][0])

    title = re.search(r"<dc:title[^>]*>(.*?)</dc:title>", opf, re.S | re.I)
    creator = re.search(r"<dc:creator[^>]*>(.*?)</dc:creator>", opf, re.S | re.I)
    toc = re.search(r'<spine\b[^>]*\btoc="([^"]+)"', opf)
    ncx = manifest.get(toc.group(1), ("", ""))[0] if toc else ""
    if not ncx:
        ncx = next((h for h, t in manifest.values() if t == "application/x-dtbncx+xml"), "")

    cover = ""
    mm = re.search(r'<meta\b[^>]*\bname=["\']cover["\'][^>]*\bcontent=["\']([^"\']+)["\']', opf)
    if mm:
        cover = manifest.get(mm.group(1), ("", ""))[0]
    if not cover:
        for tag in re.findall(r"<item\b[^>]*>", opf):
            if "cover-image" in tag:
                h = re.search(r'\bhref="([^"]+)"', tag)
                if h:
                    cover = h.group(1)
                    break
    if not cover:
        for h, t in manifest.values():
            if re.search(r"cover\.(jpe?g|png|gif)$", h, re.I):
                cover = h
                break

    return (base, manifest, spine,
            html_text(title.group(1)) if title else "",
            html_text(creator.group(1)) if creator else "", ncx, cover)


def html_text(s):
    return re.sub(r"\s+", " ", htmllib.unescape(TAG_RE.sub("", s or ""))).strip()


def parse_ncx(z, base, ncx):
    """{epub 内路径: 标题}，只取最外层，够用。"""
    out = {}
    if not ncx:
        return out
    try:
        s = z.read(posixpath.join(base, ncx) if base else ncx).decode("utf-8", "ignore")
    except KeyError:
        return out
    for np in re.findall(r"<navPoint\b.*?</navPoint>", s, re.S):
        lab = re.search(r"<navLabel>.*?<text>(.*?)</text>", np, re.S)
        src = re.search(r'<content\b[^>]*src="([^"]+)"', np)
        if lab and src:
            p = posixpath.normpath(posixpath.join(base, htmllib.unescape(src.group(1)).split("#")[0]))
            out.setdefault(p, html_text(lab.group(1)))
    return out


ESCAPE = ("#", "data:", "http://", "https://", "mailto:", "tel:", "javascript:", "//")
RES_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ttf", ".otf", ".woff", ".woff2")


def rewrite(chapter_path, body, spine_map):
    """把 src/href 重写成站点内路径；指向别的章节的改成 #chN 交给前端处理。"""
    def repl(m):
        attr, q, val = m.group(1), m.group(2), m.group(3)
        v = val.strip()
        if not v or v.lower().startswith(ESCAPE):
            return m.group(0)
        p = urllib.parse.unquote(v.split("#")[0])
        if not p:
            return m.group(0)
        target = posixpath.normpath(posixpath.join(posixpath.dirname(chapter_path), p))
        if target in spine_map:
            return "%s=%s#ch%d%s" % (attr, q, spine_map[target], q)
        return "%s=%s%s%s" % (attr, q, "a/" + urllib.parse.quote(target), q)
    return ATTR_RE.sub(repl, body)


def build_shelf():
    """书架：封面网格，进度从 localStorage 读（阅读页写的是 rd:<slug>:pos）。"""
    books = []
    if os.path.isdir(READ):
        for name in sorted(os.listdir(READ)):
            cfg = os.path.join(READ, name, "book.json")
            if not os.path.isfile(cfg):
                continue
            try:
                meta = json.load(open(cfg, encoding="utf-8"))
            except Exception:
                continue
            chs = meta.get("chapters", [])
            cover = meta.get("cover", "")
            if cover and not os.path.isfile(os.path.join(READ, name, cover)):
                cover = ""
            books.append({
                "slug": name,
                "title": meta.get("title", name),
                "author": meta.get("author", ""),
                "cover": cover,
                "sizes": [c.get("n", 0) for c in chs],
                "mtime": os.path.getmtime(cfg),
            })
    books.sort(key=lambda b: -b["mtime"])

    cards = []
    for b in books:
        sizes = ",".join(str(x) for x in b["sizes"])
        if b["cover"]:
            art = ('<img src="%s/%s" alt="" loading="lazy" decoding="async">'
                   % (b["slug"], urllib.parse.quote(b["cover"])))
        else:
            art = '<span class="ph">%s</span>' % htmllib.escape((b["title"] or "?")[:1])
        cards.append(
            '<a class="bk" href="%s/" data-slug="%s" data-sizes="%s">'
            '<div class="cv">%s<i class="pg"></i></div>'
            '<div class="mt"><b>%s</b><span>%s</span></div></a>'
            % (b["slug"], b["slug"], sizes, art,
               htmllib.escape(b["title"]), htmllib.escape(b["author"] or "　")))

    body = "\n".join(cards) or '<p class="empty">书架是空的。</p>'
    page = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex,nofollow">
<title>书架</title>
<script>document.documentElement.dataset.theme =
window.matchMedia && window.matchMedia('(prefers-color-scheme:dark)').matches ? 'dark' : 'light';</script>
<style>
html[data-theme="light"]{--bg:#f3f5f8;--text:#1e2935;--muted:#526070;--border:#dfe4ea;--card:#fff;
--sh:0 1px 2px rgba(0,0,0,.06),0 8px 20px rgba(0,0,0,.07)}
html[data-theme="dark"]{--bg:#0a0c10;--text:#dfe5ec;--muted:#98a2b0;--border:#191d24;--card:#12151b;
--sh:0 1px 2px rgba(0,0,0,.35),0 8px 20px rgba(0,0,0,.3)}
:root{--sans:'Figtree',-apple-system,BlinkMacSystemFont,"PingFang SC","Noto Sans CJK SC",system-ui,sans-serif;
--mono:'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{margin:0;background:var(--bg);color:var(--text);font-family:var(--sans);
 padding:calc(26px + env(safe-area-inset-top)) 18px calc(40px + env(safe-area-inset-bottom))}
h1{max-width:900px;margin:0 auto 4px;font-size:1.25rem;letter-spacing:-.01em;text-align:center}
.sub{max-width:900px;margin:0 auto 28px;font-family:var(--mono);font-size:.68rem;
 color:var(--muted);text-align:center}
/* 书少的时候整行居中，多了自然铺成 2/4 列 */
.grid{max-width:880px;margin:0 auto;display:flex;flex-wrap:wrap;justify-content:center;gap:28px 18px}
.bk{flex:0 0 calc((100% - 18px) / 2);max-width:210px}
.bk{text-decoration:none;color:inherit;display:block;transition:transform .16s ease}
.bk:active{transform:scale(.97)}
.cv{position:relative;aspect-ratio:3/4;border-radius:6px;overflow:hidden;background:var(--card);
 box-shadow:var(--sh);display:flex;align-items:center;justify-content:center}
.cv img{width:100%;height:100%;object-fit:cover;display:block}
.cv .ph{font-size:2.4rem;font-weight:600;color:var(--muted);opacity:.55;
 background:linear-gradient(140deg,#2b3138,#1a1e24);width:100%;height:100%;
 display:flex;align-items:center;justify-content:center}
html[data-theme="light"] .cv .ph{background:linear-gradient(140deg,#e9edf2,#d8dee6);opacity:1}
.pg{position:absolute;right:7px;bottom:7px;padding:2px 8px;border-radius:11px;
 font-size:.6rem;font-family:var(--mono);color:#f2f5f8;font-style:normal;
 background:rgba(8,10,14,.62);backdrop-filter:blur(6px);display:none;letter-spacing:.02em}
.pg.on{display:block}
.mt{margin-top:9px;line-height:1.45}
.mt b{display:block;font-size:.82rem;font-weight:500;
 display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.mt span{display:block;font-size:.68rem;color:var(--muted);margin-top:3px;white-space:nowrap;
 overflow:hidden;text-overflow:ellipsis}
.empty{max-width:900px;margin:0 auto;color:var(--muted);font-size:.85rem}
</style>
</head>
<body>
<h1>书架</h1>
<div class="sub">共 __N__ 本</div>
<div class="grid" id="grid">
__CARDS__
</div>
<script>
(function () {
  var TOTAL = {};
  [].forEach.call(document.querySelectorAll('.bk'), function (a) {
    var sizes = (a.dataset.sizes || '').split(',').filter(Boolean).map(Number);
    var total = sizes.reduce(function (x, y) { return x + y; }, 0);
    if (!total) return;
    var pos = null;
    try { pos = JSON.parse(localStorage.getItem('rd:' + a.dataset.slug + ':pos') || 'null'); } catch (e) {}
    if (!pos || typeof pos.ch !== 'number' || pos.ch >= sizes.length) return;
    var before = 0;
    for (var i = 0; i < pos.ch && i < sizes.length; i++) before += sizes[i];
    var n = sizes[pos.ch] || 0;
    var pct = (before + n * Math.min(pos.r || 0, 1)) / total * 100;
    if (isNaN(pct)) return;
    var p = Math.max(1, Math.round(pct));
    var tag = a.querySelector('.pg');
    tag.textContent = p >= 99 ? '已读完' : '读至 ' + p + '%';
    tag.classList.add('on');
  });
})();
</script>
</body></html>
""".replace("__CARDS__", body).replace("__N__", str(len(books)))
    open(os.path.join(READ, "index.html"), "w", encoding="utf-8").write(page)


def build_book(epub, slug, title_override):
    with zipfile.ZipFile(epub) as z:
        base, manifest, spine, title, creator, ncx, cover_href = parse_opf(z)
        labels = parse_ncx(z, base, ncx)

        dst = os.path.join(READ, slug)
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        os.makedirs(os.path.join(dst, "ch"))
        os.makedirs(os.path.join(dst, "a"), exist_ok=True)

        paths = [posixpath.normpath(posixpath.join(base, h)) for h in spine]
        spine_map = {p: i for i, p in enumerate(paths)}

        # 章节 = NCX 目录项覆盖的那一段 spine（一个标题常对应「标题页 + 正文页」两个文件）
        anchors = sorted([(spine_map[q], lab) for q, lab in labels.items() if q in spine_map])
        if not anchors:
            anchors = [(i, None) for i in range(len(paths))]
        chunks = []
        for k, (si, lab) in enumerate(anchors):
            start = 0 if k == 0 else si
            end = anchors[k + 1][0] if k + 1 < len(anchors) else len(paths)
            if end > start:
                chunks.append((lab, paths[start:end]))

        chapters = []
        for ci, (lab, files) in enumerate(chunks):
            if lab and JUNK_TITLE.match(lab):
                continue
            parts, n = [], 0
            for p in files:
                try:
                    raw = z.read(p).decode("utf-8", "ignore")
                except KeyError:
                    continue
                m = BODY_RE.search(raw)
                body = m.group(1) if m else raw
                body = SCRIPT_RE.sub("", body)
                body = STYLE_RE.sub("", body)
                body = body.strip()
                if not body:
                    continue
                n += text_len(body)
                parts.append(rewrite(p, body, spine_map))
            if n < 20 or not parts:          # 空页 / 纯图页
                continue
            label = lab or ""
            if not label or re.match(r"^第 \d+ 节$", label):
                h = re.search(r"<h[1-3][^>]*>(.*?)</h[1-3]>", parts[0], re.S | re.I)
                label = html_text(h.group(1)) if h else ("第 %d 节" % (len(chapters) + 1))
            frag = "\n".join(parts)
            # 标题不像正文、内容又是一整套出版信息的，整章丢掉
            if n < 3000 and len(JUNK_TEXT.findall(frag)) >= 2:
                continue
            idx = len(chapters)
            fn = "%03d.html" % idx
            open(os.path.join(dst, "ch", fn), "w", encoding="utf-8").write(frag)
            skip = n < 400
            chapters.append({"t": label, "f": "ch/" + fn, "n": n, "_h": frag, "skip": skip})

        # 资源：只拷图片和字体，保持包内相对结构
        for name in z.namelist():
            if name.endswith("/") or not name.lower().endswith(RES_EXT):
                continue
            out = os.path.join(dst, "a", name)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with z.open(name) as src, open(out, "wb") as fh:
                shutil.copyfileobj(src, fh)

    if not chapters:
        die("这本书拆不出任何正文（可能全是图片页或加密了）")

    cover_path = ""
    if cover_href:
        cp = posixpath.normpath(posixpath.join(base, htmllib.unescape(cover_href)))
        if os.path.isfile(os.path.join(dst, "a", cp)):
            cover_path = "a/" + cp

    meta = {"title": title_override or title or slug,
            "author": creator, "cover": cover_path, "chapters": chapters}

    # 正文直接内嵌：页面不发任何额外请求，minis:// 之类不支持 fetch 的环境也能读
    holder = "\n".join(
        '<template id="ch%d" data-t="%s" data-n="%d"%s>%s</template>'
        % (i, htmllib.escape(c["t"]), c["n"], ' data-skip="1"' if c.get("skip") else "", c.pop("_h"))
        for i, c in enumerate(chapters))
    json.dump(meta, open(os.path.join(dst, "book.json"), "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))

    page = open(TPL, encoding="utf-8").read()
    page = page.replace("{{TITLE}}", htmllib.escape(meta["title"]))
    page = page.replace("{{SLUG}}", json.dumps(slug))
    page = page.replace("{{CHAPTERS}}", holder)
    left = set(re.findall(r"\{\{[A-Z_]+\}\}", page))
    if left:
        die("模板里还剩占位符：%s" % " ".join(sorted(left)))
    open(os.path.join(dst, "index.html"), "w", encoding="utf-8").write(page)

    build_shelf()
    words = sum(c["n"] for c in chapters)
    print("✓ %s（%s）" % (meta["title"], meta["author"] or "未知"))
    print("  %d 章 · %.1f 万字 · %s" % (len(chapters), words / 10000.0, slug))
    print("  https://patrick12138.github.io/read/%s/" % slug)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, help="epub 路径")
    ap.add_argument("--title", help="书名，默认取 EPUB 元数据")
    ap.add_argument("--slug", help="目录名，默认随机 6 位")
    a = ap.parse_args()

    if not os.path.isfile(a.file):
        die("找不到文件：%s" % a.file)
    if not zipfile.is_zipfile(a.file):
        die("不是有效的 EPUB（zip 结构坏了）：%s" % a.file)
    slug = a.slug or secrets.token_hex(3)
    if not re.match(r"^[a-z0-9][a-z0-9-]{1,40}$", slug):
        die("slug 只能用小写字母/数字/连字符：%s" % slug)
    os.makedirs(READ, exist_ok=True)
    build_book(a.file, slug, a.title)


if __name__ == "__main__":
    main()
