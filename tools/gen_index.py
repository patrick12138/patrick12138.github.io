#!/usr/bin/env python3
"""扫描 posts/ 生成首页 index.html。用法：python3 tools/gen_index.py"""
import os, re, glob, html
from datetime import datetime
from home_snippets import JS, THEME_ICONS
import dates

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(SITE, "index.html")

STYLE = ('<meta property="og:type" content="website">'
         '<meta property="og:site_name" content="patrick">'
         '<meta property="og:title" content="patrick">'
         '<meta property="og:description" content="写点东西，也搬运点好东西。">'
         '<meta property="og:url" content="https://patrick12138.github.io/">'
         '<link rel="alternate" type="application/rss+xml" title="patrick" href="feed.xml">'
         '<link rel="icon" href="favicon.svg" type="image/svg+xml"><meta name="theme-color" content="#f3f5f8" media="(prefers-color-scheme: light)"><meta name="theme-color" content="#0f1319" media="(prefers-color-scheme: dark)"><link rel="stylesheet" href="assets/base.css">'
         '<link rel="stylesheet" href="assets/home.css">')   # ?v= 由 tools/build.py 统一写

def trim_desc(s, limit=92):
    """首页只显示两行：在句末标点处截断并补省略号，别把半句话硬切。"""
    s = re.sub(r"\s+", " ", html.unescape(s or "")).strip()
    s = re.sub(r"\s*[-–—-]\s*(?:How-To|README|at main).*$", "", s)  # 抓正文带进来的尾巴
    if len(s) <= limit:
        return s
    cut = s[:limit]
    ends = max(cut.rfind(c) for c in "。！？；.!?;")
    comma = max(cut.rfind("，"), cut.rfind("、"))
    pos = ends if ends >= limit * 0.5 else (comma if comma >= limit * 0.6 else -1)
    if pos > 0:
        cut = cut[:pos + 1]
    return cut.rstrip("，、；,; ") + "…"


MONTHS = {m: i for i, m in enumerate(
    ["January","February","March","April","May","June","July",
     "August","September","October","November","December"], 1)}

def cn_date(meta):
    """首页用短日期：2026年10月26日 → 10月26日（非当年才补年份）"""
    m = re.match(r"(\d{4})年(\d{1,2})月(\d{1,2})日(.*)", meta or "")
    if not m:
        return meta
    year, mon, day, rest = int(m.group(1)), m.group(2), m.group(3), m.group(4)
    label = "%s月%s日" % (mon, day)
    if year != datetime.now().year:
        label = "%d年%s" % (year, label)
    return label + rest


def parse_date(s):
    """排序键 (年, 月, 日)；认不出来给 (0,0,0) 排到最后。解析逻辑在 tools/dates.py。"""
    d = dates.to_date(s)
    return ((d.year, d.month, d.day) if d else (0, 0, 0)), (s or "")


items = []
for path in glob.glob(os.path.join(SITE, "posts", "*", "index.html")):
    slug = os.path.basename(os.path.dirname(path))
    s = open(path, encoding="utf-8").read()
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", s, re.S)
    if not h1:
        continue
    title = re.sub(r"<[^>]+>", "", h1.group(1)).strip()
    meta = re.search(r'<div class="meta">(.*?)</div>', s, re.S)
    meta_txt = re.sub(r"<[^>]+>", "", meta.group(1)).strip() if meta else ""
    st = re.search(r'<span class="stats">([^<]*)</span>', s)
    word_count = ""
    if st:
        m_wc = re.search(r"(\d[\d,]*\s*字)", st.group(1))
        if m_wc:
            word_count = m_wc.group(1).strip()
    stat = word_count
    desc = re.search(r'<meta name="description" content="([^"]*)"', s)
    desc_txt = html.unescape(desc.group(1)) if desc else ""
    parts = [x.strip() for x in meta_txt.split(" · ") if x.strip()]
    parts = [x for x in parts if not re.search(r"字|分钟", x)]
    if len(parts) >= 2:
        meta_txt = parts[0] + " · " + parts[-1]
    elif parts:
        meta_txt = parts[0]
    if word_count:
        meta_txt += " · " + word_count
    key, date_txt = parse_date(meta_txt)
    kind = "own" if ("个人" in meta_txt or "原创" in meta_txt) else "repost"
    items.append({"slug": slug, "title": title, "meta": meta_txt,
                  "date": date_txt, "key": key, "desc": desc_txt, "kind": kind, "stat": stat})

items.sort(key=lambda x: x["slug"])                      # 先按 slug 定序，保证同日文章的先后稳定
items.sort(key=lambda x: x["key"], reverse=True)         # 再按日期倒序（稳定排序，同日保持 slug 顺序）

rows = []
for it in items:
    rows.append(
        '<li data-kind="%s"><a href="posts/%s/">'
        '<h2>%s</h2><p class="desc">%s</p><time>%s</time></a></li>'
        % (it["kind"], it["slug"], html.escape(it["title"]),
           html.escape(trim_desc(it["desc"])), html.escape(cn_date(it["meta"]))))

latest = cn_date(items[0]["meta"]).split(" · ")[0] if items else ""
meta_line = '<p class="page-meta">%d 篇 · 最新 %s</p>' % (len(items), latest)
body = ('<div class="wrap">' + meta_line +
        '<div class="tools"><div class="tabs" id="tabs">'
        '<button class="on" data-f="all">全部</button>'
        '<button data-f="repost">搬运</button>'
        '<button data-f="own">个人</button>'
        '</div>'
        '<input id="q" class="sinput" type="search" placeholder="搜索标题、摘要或正文…" autocomplete="off">'
        '<button class="sclr" id="qClear" aria-label="清空搜索" hidden>'
        '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" aria-hidden="true">'
        '<path d="M6 6l12 12M18 6L6 18"/></svg></button>'
        '<button class="sbtn" id="searchBtn" aria-label="搜索">'
        '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>'
        '</button></div>'
        '<ul class="posts" id="posts">' + "".join(rows) + '</ul>'
        '<div id="sentinel" aria-hidden="true"></div></div>')
# 样式统一写在 assets/home.css（页面已改为外链，这里不再往 <style> 里塞）
body += ('<div class="wrap"><p id="emptyHint" style="display:none;color:var(--text-muted);'
         'padding:0 0 60px">这个分类下还没有文章。</p></div>')


page = """<!DOCTYPE html>
<html lang="zh-CN" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="写点东西，也搬运点好东西。">
<title>patrick</title>
%s
</head>
<body>
<div class="bar"><div class="bar-in">
  <a class="brand" href="./">patrick</a>
  <nav class="nav">
    <a href="lab/" class="nav-lab">Lab</a>
    <a href="about/">About</a>
    %s
  </nav>
</div></div>
%s
<footer><div class="wrap"><div class="foot-in">
  © 2023–2026 <a href="about/">patrick</a>
</div></div></footer>
<button class="to-top" id="toTop" data-threshold="600" aria-label="返回顶部" title="返回顶部">
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 19V5M5 12l7-7 7 7"/></svg>
</button>

<script src="assets/site.js"></script>
%s
</body>
</html>""" % (STYLE, THEME_ICONS, body, JS)

open(OUT, "w", encoding="utf-8").write(page)
print("index built:", len(items), "posts")
for it in items[:6]:
    print(" ", it["meta"], "|", it["slug"])
