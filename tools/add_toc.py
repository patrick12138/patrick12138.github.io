#!/usr/bin/env python3
"""给文章页加一个可折叠的右侧目录（PC 悬浮 / 手机浮动按钮）。

用法：
  python3 tools/add_toc.py                      # 处理所有 posts/*/index.html
  python3 tools/add_toc.py posts/xxx/index.html # 只处理指定页

可重复执行：已经加过的页面会先剥掉旧的 toc 标记再重算。
"""
import glob
import html as htmllib
import os
import re
import postbody
import sys

from post_snippets import BRAND_JS

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


HEAD = ('<nav class="toc" id="toc" aria-label="文章目录" aria-hidden="true">'
        '<ol class="toc-list" id="tocList">%s</ol></nav>'
        '<button class="toc-fab" id="tocFab" aria-label="目录" aria-expanded="false" aria-controls="toc">'
        + '<svg class="toc-ico" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.8" stroke-linecap="round" aria-hidden="true">'
        '<line x1="9" y1="6" x2="20" y2="6"/><line x1="9" y1="12" x2="20" y2="12"/>'
        '<line x1="9" y1="18" x2="20" y2="18"/>'
        '<circle cx="4.6" cy="6" r="1.2" fill="currentColor" stroke="none"/>'
        '<circle cx="4.6" cy="12" r="1.2" fill="currentColor" stroke="none"/>'
        '<circle cx="4.6" cy="18" r="1.2" fill="currentColor" stroke="none"/></svg>' + '</button>'
        '<button class="toc-handle" id="tocHandle" aria-label="目录" tabindex="-1">'
        '<span class="toc-bars">%s</span></button>')


def strip_toc(doc):
    """把自己注入过的东西全部清干净（含重复注入的多份），保证可重复执行。"""
    # 目录结构：从 <nav class="toc" 一直剥到它的 </nav>，不依赖内部细节，
    # 否则旧版本注入的变体会漏网，越跑越多（曾出现 13 份重叠）
    doc = re.sub(r'<nav class="toc"[^>]*>.*?</nav>\s*', "", doc, flags=re.S)
    doc = re.sub(r'<button class="toc-fab"[^>]*>.*?</button>\s*', "", doc, flags=re.S)
    doc = re.sub(r'<button class="toc-tab"[^>]*>.*?</button>\s*', "", doc, flags=re.S)
    doc = re.sub(r'<button class="toc-handle"[^>]*>.*?</button>\s*', "", doc, flags=re.S)
    doc = re.sub(r'<button class="to-top"[^>]*>.*?</button>\s*', "", doc, flags=re.S)
    # 别的会话注入过的英文版浮动按钮
    doc = re.sub(r'<button class="toc-fab"[^>]*>.*?</button>', "", doc, flags=re.S)
    doc = re.sub(r'<button class="toc-tab"[^>]*>.*?</button>', "", doc, flags=re.S)
    # 注入的脚本块（可能有多份，全部清掉，稍后重新注入一次）
    for sig in ("brandSet", "backTop", "var toc=document.getElementById", "getElementById('toTop')"):
        pat = r"\n<script>\n\(function\(\)\{[^<]*?%s[\s\S]*?\}\)\(\);\n</script>" % re.escape(sig)
        doc = re.sub(pat, "", doc)
    # 清掉之前反复 strip 留下的空 script
    doc = re.sub(r"\n?<script></script>", "", doc)
    return doc


def build_toc(doc):
    """给正文 h2/h3 加 id，返回 (新文档, 目录 html)。"""
    start, end = postbody.body_span(doc)
    if end <= start:
        return doc, ""
    body = doc[start:end]
    items = []
    n = 0

    def repl(mo):
        nonlocal n
        tag, attrs, text = mo.group(1), mo.group(2), mo.group(3)
        plain = htmllib.unescape(re.sub(r"<[^>]+>", "", text)).strip()
        have = re.search(r'\sid="([^"]+)"', attrs)
        if have:
            items.append((tag, have.group(1), plain))
            return mo.group(0)
        n += 1
        hid = "h%d" % n
        items.append((tag, hid, plain))
        return '<%s%s id="%s">%s</%s>' % (tag, attrs, hid, text, tag)

    body2 = re.sub(r'<(h2|h3|h4)([^>]*)>(.*?)</\1>', repl, body, flags=re.S)
    if len(items) < 3:
        return doc, ""
    li = "".join(
        '<li class="lvl%s"><a href="#%s">%s</a></li>' % ({"h2": "2", "h3": "3"}.get(tag, "4"), hid, htmllib.escape(t))
        for tag, hid, t in items
    )
    bars = "".join(
        '<i class="b %s" data-h="%s"></i>' % ({"h2": "l2", "h3": "l3"}.get(tag, "l4"), hid)
        for tag, hid, _ in items
    )
    doc = doc[:start] + body2 + doc[end:]
    return doc, (li, bars)


TOP_BTN = ('<button class="to-top" id="toTop" data-threshold="half" aria-label="返回顶部" title="返回顶部">'
           '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
           'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
           '<path d="M12 19V5M5 12l7-7 7 7"/></svg></button>')



def normalize_nav(doc):
    """确保文章页右上角导航与首页一致：Lab 和 About，不放首页链接。"""
    doc = re.sub(
        r'<nav class="nav">\s*<a href="[^"]*"(?: class="[^"]*")?>首页</a>\s*<a href="([^"]*/lab/)"(?: class="[^"]*")?>Lab</a>',
        r'<nav class="nav">\n    <a href="\1">Lab</a><a href="../../about/">About</a>',
        doc
    )
    if '<a href="../../about/">About</a>' not in doc:
        doc = re.sub(
            r'(<a href="[^"]*/lab/"[^>]*>Lab</a>)(?!\s*<a href="[^"]*about/)',
            r'\1<a href="../../about/">About</a>',
            doc
        )
    return doc


def inject_top_btn(doc):
    """浮动「回到顶部」，下拉到文章一半再出现。"""
    if 'id="toTop"' in doc:
        return doc
    if '<a class="back"' in doc:
        doc = doc.replace('</body>', TOP_BTN + '\n</body>', 1)
    return doc


ICON_SVG = ('<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
           'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
           '<path d="M4 9V5.5A1.5 1.5 0 0 1 5.5 4H9M15 4h3.5A1.5 1.5 0 0 1 20 5.5V9'
           'M20 15v3.5A1.5 1.5 0 0 1 18.5 20H15M9 20H5.5A1.5 1.5 0 0 1 4 18.5V15"/></svg>')

# 入口按钮：固定在文章头部（标题右上角），普通态可见
READ_OPEN = ('<button class="read-open" id="readOpen" type="button" aria-label="沉浸阅读" title="沉浸阅读">'
             + ICON_SVG + '</button>')
READ_EXIT = '<a class="read-exit" id="readExit" href="#">读完 · 退出沉浸阅读</a>'


def ensure_readmode(doc):
    """注入沉浸阅读的三个元素（幂等，各管各的）：

    - `#readOpen`  文章标题右上角（普通态入口，绝对定位在文章容器内）
    - `#readExit`  文末文字出口（只在沉浸态显示）

    三个元素各自占一个固定位置，靠 display 切换显隐 —— 不需要搬 DOM，也就不会跳。
    """
    for pat in (r'<button class="read-open"[^>]*>.*?</button>',
                r'<button class="read-btn"[^>]*>.*?</button>',   # 旧版注入的（在顶栏里）一并清掉
                r'<button class="read-exit-btn"[^>]*>.*?</button>',
                r'\n*<a class="read-exit"[^>]*>.*?</a>'):
        doc = re.sub(pat, '', doc, flags=re.S)

    # 入口：紧跟在 <h1> 之后（.article 是定位容器）
    m = re.search(r'(<h1[^>]*>.*?</h1>)', doc, re.S)
    if m:
        doc = doc[:m.end(1)] + READ_OPEN + doc[m.end(1):]

    # 文末文字出口
    for anchor in ('<aside class="legal-note"', '<nav class="related"', '<nav class="pager"', '<a class="back"'):
        i2 = doc.find(anchor)
        if i2 > 0:
            doc = doc[:i2].rstrip("\n") + "\n" + READ_EXIT + "\n" + doc[i2:]
            break
    return doc


def ensure_icon(doc):
    """文章页补 favicon / theme-color（幂等）：老页面不用整篇重建也能带上。"""
    if "favicon.svg" in doc:
        return doc
    return doc.replace('<link rel="stylesheet" href="../../assets/base.css',
                       ICON_TAGS + '<link rel="stylesheet" href="../../assets/base.css', 1)


def wrap_tables(doc):
    """把表格包进可横滑的容器。

    table 自己当滚动容器（display:block + overflow-x）时，宽度一旦按内容撑开，
    它就不再溢出自己，手机上怎么拖都拖不动。所以表格保持 table 语义，
    外面套一个定宽的滚动层。
    """
    if 'class="tablewrap"' in doc:
        return doc
    return re.sub(r"<table(\s[^>]*)?>.*?</table>", lambda m: _wrap(m.group(0)), doc, flags=re.S)


NUM_RE = re.compile(r"^[\s\d.,%/×x~+\-—–$¥€£元个条次天小时月年]*\d[\s\d.,%/×x~+\-—–$¥€£元个条次天小时月年]*$")


def _wrap(table_html):
    """包一层滚动容器；顺手给「数字列」打上 n2/n3 之类的类，让它们右对齐。"""
    cells = postbody.table_rows(table_html)
    num = []
    if cells:
        ncol = max(len(c) for c in cells)
        for i in range(ncol):
            col = [re.sub(r"<[^>]+>", "", c[i]).strip() for c in cells if len(c) > i]
            col = [v for v in col if v]
            if col and sum(1 for v in col if NUM_RE.match(v)) / len(col) >= 0.6:
                num.append("n%d" % (i + 1))
    if num:
        table_html = re.sub(r"<table([^>]*)>", lambda m: "<table%s class=\"%s\""
                            % (m.group(1) if "class=" not in m.group(1) else m.group(1), " ".join(num)),
                            table_html, count=1)
    return '<div class="tablewrap">' + table_html + "</div>"


def process(path):
    doc = open(path, encoding="utf-8").read()
    if 'class="body"' not in doc:
        return False
    doc = strip_toc(doc)
    doc = normalize_nav(doc)
    doc = inject_top_btn(doc)
    doc = wrap_tables(doc)
    doc = ensure_icon(doc)
    doc = ensure_readmode(doc)
    doc, toc_parts = build_toc(doc)
    li, bars = toc_parts if toc_parts else ("", "")
    doc = doc.replace("</body>", "<script>" + BRAND_JS + "</script>\n</body>", 1)
    if not toc_parts:
        open(path, "w", encoding="utf-8").write(doc)
        return False
    # 目录标记：放在 body 之前（正文起点前）
    doc = doc.replace('<div class="body">', HEAD % (li, bars) + '<div class="body">', 1)
    # 脚本：外链（之前是把整段 JS 内联进每个页面）
    if 'assets/post.js' not in doc:                 # 幂等：已经引过就不再插
        doc = doc.replace("</body>", '<script src="../../assets/post.js"></script>\n</body>', 1)
    open(path, "w", encoding="utf-8").write(doc)
    return True


def main():
    args = sys.argv[1:]
    paths = args if args else sorted(glob.glob(os.path.join(ROOT, "posts", "*", "index.html")))
    ok = 0
    for p in paths:
        if process(p):
            ok += 1
            print("  ✓ %s" % os.path.relpath(p, ROOT))
        else:
            print("  · 跳过（标题不足 3 个）%s" % os.path.relpath(p, ROOT))
    print("完成：%d/%d" % (ok, len(paths)))


if __name__ == "__main__":
    main()
