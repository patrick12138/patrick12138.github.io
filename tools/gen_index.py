#!/usr/bin/env python3
"""扫描 posts/ 生成首页 index.html。用法：python3 tools/gen_index.py"""
import os, re, glob, html

SITE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(SITE, "index.html")

STYLE = '<link rel="stylesheet" href="assets/home.css">'   # ?v= 由 tools/build.py 统一写

MONTHS = {m: i for i, m in enumerate(
    ["January","February","March","April","May","June","July",
     "August","September","October","November","December"], 1)}


def parse_date(s):
    m = re.search(r"([A-Z][a-z]+)\s+(\d+),\s+(\d{4})", s or "")
    if not m:
        return (0, 0, 0), ""
    return (int(m.group(3)), MONTHS.get(m.group(1), 0), int(m.group(2))), s


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
    desc = re.search(r'<meta name="description" content="([^"]*)"', s)
    desc_txt = html.unescape(desc.group(1)) if desc else ""
    key, date_txt = parse_date(meta_txt)
    kind = "own" if ("个人" in meta_txt or "原创" in meta_txt) else "repost"
    items.append({"slug": slug, "title": title, "meta": meta_txt,
                  "date": date_txt, "key": key, "desc": desc_txt, "kind": kind})

items.sort(key=lambda x: x["key"], reverse=True)

rows = []
for it in items:
    rows.append(
        '<li data-kind="%s"><a href="posts/%s/">'
        '<h2>%s</h2><p class="desc">%s</p><time>%s</time></a></li>'
        % (it["kind"], it["slug"], html.escape(it["title"]),
           html.escape(it["desc"][:150]), html.escape(it["meta"])))

body = ('<div class="wrap"><h1 class="page-title">首页</h1>'
        '<div class="tools"><div class="tabs" id="tabs">'
        '<button class="on" data-f="all">全部</button>'
        '<button data-f="repost">搬运</button>'
        '<button data-f="own">个人</button>'
        '</div><button class="sbtn" id="searchBtn" aria-label="搜索">'
        '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg>'
        '</button></div>'
        '<div class="sbox" id="searchBox"><input id="q" type="search" placeholder="搜索标题…" autocomplete="off"></div>'
        '<ul class="posts" id="posts">%s</ul></div>' % "".join(rows))
# 样式统一写在 assets/home.css（页面已改为外链，这里不再往 <style> 里塞）
body += ('<div class="wrap"><p id="emptyHint" style="display:none;color:var(--text-muted);'
         'padding:0 0 60px">这个分类下还没有文章。</p></div>')

JS = """<script>
(function(){
  var tabs=document.getElementById('tabs');
  var btn=document.getElementById('searchBtn');
  var box=document.getElementById('searchBox');
  var input=document.getElementById('q');
  var empty=document.getElementById('emptyHint');
  var state={f:'all',q:''};
  // ?tab=repost|own|all 直达分类（文章页站名下拉会带过来）
  try{
    var tf=(new URLSearchParams(location.search)).get('tab');
    if(tf && ['all','repost','own'].indexOf(tf)>=0){
      state.f=tf;
      if(tabs)[].forEach.call(tabs.children,function(x){ x.classList.toggle('on', x.dataset.f===tf); });
    }
  }catch(e){}

  function apply(){
    var shown=0;
    [].forEach.call(document.querySelectorAll('#posts li'),function(li){
      var okKind=(state.f==='all'||li.dataset.kind===state.f);
      var okQ=(!state.q||li.textContent.toLowerCase().indexOf(state.q)>=0);
      var show=okKind&&okQ;
      li.style.display=show?'':'none';
      if(show)shown++;
    });
    if(empty)empty.style.display=shown?'none':'block';
  }

  if(tabs)tabs.addEventListener('click',function(e){
    var b=e.target.closest('button'); if(!b)return;
    [].forEach.call(tabs.children,function(x){x.classList.toggle('on',x===b);});
    state.f=b.dataset.f; apply();
  });

  if(btn)btn.addEventListener('click',function(){
    var on=box.classList.toggle('on');
    btn.classList.toggle('on',on);
    if(on){ input.focus(); } else { input.value=''; state.q=''; apply(); }
  });

  if(input)input.addEventListener('input',function(){
    state.q=input.value.trim().toLowerCase(); apply();
  });
  apply();   // 初始渲染（带 ?tab= 时直接落到对应分类）
})();
</script>"""

THEME_ICONS = """<button class="theme-toggle" id="themeToggle" aria-label="Toggle theme">
<svg class="icon-sun" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
<svg class="icon-moon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
</button>"""

THEME_JS = """<script>
(function(){
  var h=document.documentElement;
  try{var s=localStorage.getItem('theme');var d=window.matchMedia('(prefers-color-scheme: dark)').matches;
      h.dataset.theme=s||(d?'dark':'light');}catch(e){}
  var t=document.getElementById('themeToggle');
  if(t)t.addEventListener('click',function(){
    var n=h.dataset.theme==='dark'?'light':'dark';
    h.classList.add('theme-switching');h.dataset.theme=n;
    try{localStorage.setItem('theme',n);}catch(e){}
    setTimeout(function(){h.classList.remove('theme-switching');},300);
  });
})();
</script>"""

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
    <a href="./" class="on">首页</a>
    <a href="lab/">Lab</a>
    %s
  </nav>
</div></div>
%s
<footer><div class="wrap"><div class="foot-in">
  © 2026 <a href="about/">patrick</a>
</div></div></footer>
<button class="to-top" id="toTop" aria-label="返回顶部" title="返回顶部">
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 19V5M5 12l7-7 7 7"/></svg>
</button>
<div class="to-top-link"><a href="#" id="toTopLink">↑ 回到顶部</a></div>
%s
%s
</body>
</html>""" % (STYLE, THEME_ICONS, body, THEME_JS, JS)

open(OUT, "w", encoding="utf-8").write(page)
print("index built:", len(items), "posts")
for it in items[:6]:
    print(" ", it["meta"], "|", it["slug"])
