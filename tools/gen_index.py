#!/usr/bin/env python3
"""扫描 posts/ 生成首页 index.html。用法：python3 tools/gen_index.py"""
import os, re, glob, html
from datetime import datetime

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(SITE, "index.html")

STYLE = ('<link rel="alternate" type="application/rss+xml" title="patrick" href="feed.xml">'
         '<link rel="stylesheet" href="assets/base.css">'
         '<link rel="stylesheet" href="assets/home.css">')   # ?v= 由 tools/build.py 统一写

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
    """支持中文 2026年10月15日 与英文 October 15, 2026 两种写法。"""
    s = s or ""
    m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", s)
    if m:
        return (int(m.group(1)), int(m.group(2)), int(m.group(3))), s
    m = re.search(r"([A-Z][a-z]+)\s+(\d+),\s+(\d{4})", s)
    if m:
        return (int(m.group(3)), MONTHS.get(m.group(1), 0), int(m.group(2))), s
    return (0, 0, 0), s

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
           html.escape(it["desc"][:150]), html.escape(cn_date(it["meta"]))))

latest = cn_date(items[0]["meta"]).split(" · ")[0] if items else ""
meta_line = '<p class="page-meta">%d 篇 · 最新 %s</p>' % (len(items), latest)
body = ('<div class="wrap">' + meta_line +
        '<div class="tools"><div class="tabs" id="tabs">'
        '<button class="on" data-f="all">全部</button>'
        '<button data-f="repost">搬运</button>'
        '<button data-f="own">个人</button>'
        '</div>'
        '<input id="q" class="sinput" type="search" placeholder="搜索标题或摘要…" autocomplete="off">'
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

JS = """<script>
(function(){
  var tabs=document.getElementById('tabs');
  var btn=document.getElementById('searchBtn');
  var tools=document.querySelector('.tools');
  var input=document.getElementById('q');
  var empty=document.getElementById('emptyHint');
  var sentinel=document.getElementById('sentinel');
  var state={f:'all',q:''};
  var BATCH=20, shown=BATCH, matched=[];

  try{
    var tf=(new URLSearchParams(location.search)).get('tab');
    if(tf && ['all','repost','own'].indexOf(tf)>=0){
      state.f=tf;
      if(tabs)[].forEach.call(tabs.children,function(x){ x.classList.toggle('on', x.dataset.f===tf); });
    }
  }catch(e){}

  function scan(){
    matched=[];
    [].forEach.call(document.querySelectorAll('#posts li'),function(li){
      var okKind=(state.f==='all'||li.dataset.kind===state.f);
      var okQ=(!state.q||li.textContent.toLowerCase().indexOf(state.q)>=0);
      if(okKind&&okQ){ matched.push(li); } else { li.style.display='none'; }
    });
  }
  function paint(){
    matched.forEach(function(li,i){ li.style.display = i<shown ? '' : 'none'; });
    if(empty) empty.style.display = matched.length ? 'none' : 'block';
    if(sentinel) sentinel.style.display = (shown < matched.length) ? 'block' : 'none';
  }
  function apply(reset){
    if(reset!==false) shown=BATCH;
    scan(); paint();
  }

  function syncUrl(){
    try{
      var u=new URL(location.href);
      if(state.f==='all'){ u.searchParams.delete('tab'); } else { u.searchParams.set('tab', state.f); }
      history.replaceState(null,'', u.pathname + u.search + u.hash);  // 只用相对路径，minis:// 下也安全
    }catch(err){}
  }

  if(tabs)tabs.addEventListener('click',function(e){
    var b=e.target.closest('button'); if(!b)return;
    [].forEach.call(tabs.children,function(x){x.classList.toggle('on',x===b);});
    state.f=b.dataset.f; apply(); syncUrl();
  });

  if(btn)btn.addEventListener('click',function(){
    var on=tools.classList.toggle('searching');
    btn.classList.toggle('on',on);
    if(on){ input.focus(); } else { input.value=''; state.q=''; apply(); }
  });

  if(qClear)qClear.addEventListener('click',function(){
    input.value=''; state.q=''; qClear.hidden=true; input.focus(); apply();
  });
  if(input)input.addEventListener('input',function(){
    if(qClear) qClear.hidden = !input.value;
    state.q=input.value.trim().toLowerCase(); apply();
  });

  // 下滑加载下一批
  function loadMore(){
    if(shown>=matched.length) return;
    shown=Math.min(shown+BATCH, matched.length);
    paint();
  }
  // 双保险：观察器 + 滚动兜底（部分 WebView 的 IO 不触发）
  if(sentinel && 'IntersectionObserver' in window){
    try{
      new IntersectionObserver(function(es){
        if(es.some(function(x){return x.isIntersecting;})) loadMore();
      },{rootMargin:'600px 0px', threshold:0}).observe(sentinel);
    }catch(e){}
  }
  window.addEventListener('scroll',function(){
    var nearBottom = window.innerHeight + window.pageYOffset > document.body.scrollHeight - 800;
    if(nearBottom) loadMore();
  },{passive:true});
  // 首屏内容不足一屏时也补一批
  setTimeout(function(){ if(shown>=matched.length) return;
    if(document.body.scrollHeight <= window.innerHeight + 200) loadMore(); }, 300);

  apply();
})();
</script>"""

THEME_ICONS = """<button class="theme-toggle" id="themeToggle" aria-label="Toggle theme">
<svg class="icon-sun" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
<svg class="icon-moon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
</button>"""

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
