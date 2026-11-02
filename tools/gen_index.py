#!/usr/bin/env python3
"""扫描 posts/ 生成首页 index.html。用法：python3 tools/gen_index.py"""
import os, re, glob, html
from datetime import datetime

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

JS = """<script>
(function(){
  var tabs=document.getElementById('tabs');
  var btn=document.getElementById('searchBtn');
  var tools=document.querySelector('.tools');
  var input=document.getElementById('q');
  var qClear=document.getElementById('qClear');
  var empty=document.getElementById('emptyHint');
  var sentinel=document.getElementById('sentinel');
  var meta=document.querySelector('.page-meta');
  var metaText=meta?meta.textContent:'';
  var list=document.getElementById('posts');
  var state={f:'all',q:''};
  var BATCH=20, shown=BATCH, matched=[];
  var IDX=null, loadingIdx=false;

  /* 缓存每条的原始 HTML，搜索时改写、清空时还原 */
  var rows=[].map.call(document.querySelectorAll('#posts li'),function(li){
    var a=li.querySelector('a'), h=li.querySelector('h2'), d=li.querySelector('.desc');
    return {el:li, kind:li.dataset.kind, a:a, h:h, d:d,
            hHtml:h?h.innerHTML:'', dHtml:d?d.innerHTML:''};
  });

  function esc(s){ return s.replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];}); }
  function mark(text,q){
    if(!q) return esc(text);
    var low=text.toLowerCase(), out='', i=0, k;
    while((k=low.indexOf(q,i))>=0){
      out += esc(text.slice(i,k)) + '<mark>' + esc(text.slice(k,k+q.length)) + '</mark>';
      i = k + q.length;
    }
    return out + esc(text.slice(i));
  }

  try{
    var sp=new URLSearchParams(location.search);
    var tf=sp.get('tab');
    if(tf && ['all','repost','own'].indexOf(tf)>=0){
      state.f=tf;
      if(tabs)[].forEach.call(tabs.children,function(x){ x.classList.toggle('on', x.dataset.f===tf); });
    }
    var sq=sp.get('q');
    if(sq){ state.q=sq.trim().toLowerCase(); openSearch(sq); }
  }catch(e){}

  /* ── 浏览模式（无关键词）：沿用分批渲染 ── */
  function scan(){
    matched=[];
    rows.forEach(function(r){
      var okKind=(state.f==='all'||r.kind===state.f);
      if(okKind){ matched.push(r.el); } else { r.el.style.display='none'; }
    });
  }
  function paint(){
    matched.forEach(function(li,i){ li.style.display = i<shown ? '' : 'none'; });
    setEmpty(matched.length);
    if(sentinel) sentinel.style.display = (shown < matched.length) ? 'block' : 'none';
  }
  function restoreOrder(){
    rows.forEach(function(r){
      if(r.h) r.h.innerHTML=r.hHtml;      // 去掉搜索高亮
      if(r.d) r.d.innerHTML=r.dHtml;
      list.appendChild(r.el); r.el.style.display='';
    });
  }
  function apply(reset){
    if(reset!==false) shown=BATCH;
    restoreOrder(); scan(); paint(); setMeta(matched.length);
  }

  function setEmpty(n){
    if(!empty) return;
    if(n){ empty.style.display='none'; return; }
    empty.style.display='block';
    empty.textContent = state.q ? '没有匹配到正文，换个更短的词试试。' : '这个分类下还没有文章。';
  }

  function setMeta(n){
    if(!meta) return;
    meta.textContent = state.q ? (n + ' 条匹配') : metaText;
  }

  /* ── 搜索模式：用构建期索引打分 ── */
  function loadIdx(){
    if(IDX||loadingIdx) return;
    if(window.__SEARCH){ IDX=window.__SEARCH; runSearch(); return; }
    loadingIdx=true;
    var el=document.createElement('script');
    el.src='search.js';
    el.onload=function(){ IDX=window.__SEARCH||[]; loadingIdx=false; runSearch(); };
    el.onerror=function(){ loadingIdx=false; };
    document.head.appendChild(el);
  }

  function score(p,q){
    var s=0;
    if(p.t.toLowerCase().indexOf(q)>=0) s+=5;
    if(p.t.toLowerCase().indexOf(q)===0) s+=3;
    if((p.d||'').toLowerCase().indexOf(q)>=0) s+=2;
    for(var i=0;i<(p.h||[]).length;i++){
      if(p.h[i].toLowerCase().indexOf(q)>=0){ s+=3; break; }
    }
    var bi=(p.b||'').toLowerCase().indexOf(q);
    if(bi>=0) s+=1;
    return {s:s, bi:bi};
  }
  function snippet(p,q){
    var b=p.b||'', i=b.toLowerCase().indexOf(q);
    if(i<0) return '';
    var a=Math.max(0,i-32), z=Math.min(b.length,i+q.length+56);
    return (a>0?'…':'')+b.slice(a,z)+(z<b.length?'…':'');
  }

  function runSearch(){
    var q=state.q;
    if(!q){ apply(); return; }
    if(!IDX){                    // 索引还没到，先用 DOM 里的文字顶着
      matched=[];
      rows.forEach(function(r){
        var okKind=(state.f==='all'||r.kind===state.f);
        var hit=okKind && (r.el.textContent.toLowerCase().indexOf(q)>=0);
        r.el.style.display=hit?'':'none';
        if(hit) matched.push(r.el);
      });
      setMeta(matched.length);
      setEmpty(matched.length);
      return;
    }
    var hits=[];
    IDX.forEach(function(p){
      var r=score(p,q);
      if(r.s>0) hits.push({p:p,s:r.s,bi:r.bi});
    });
    var bySlug={};
    rows.forEach(function(r){
      var parts=r.el.querySelector('a').getAttribute('href').split('/').filter(Boolean);
      bySlug[parts[parts.length-1]]=r;
    });
    hits.sort(function(a,b){ return b.s-a.s; });
    var shownN=0;
    rows.forEach(function(r){ r.el.style.display='none'; });
    hits.forEach(function(h){
      var r=bySlug[h.p.s]; if(!r) return;
      if(state.f!=='all' && r.kind!==state.f) return;
      var inDesc = (h.p.d||'').toLowerCase().indexOf(q)>=0;
      if(r.h) r.h.innerHTML = mark(h.p.t,q);
      if(r.d) r.d.innerHTML = mark(inDesc ? h.p.d : (snippet(h.p,q)||h.p.d||''), q);
      r.el.style.display='';
      list.appendChild(r.el);
      shownN++;
    });
    setEmpty(shownN);
    if(sentinel) sentinel.style.display='none';
    setMeta(shownN);
  }

  function syncUrl(){
    try{
      var u=new URL(location.href);
      if(state.f==='all'){ u.searchParams.delete('tab'); } else { u.searchParams.set('tab', state.f); }
      if(state.q){ u.searchParams.set('q', state.q); } else { u.searchParams.delete('q'); }
      history.replaceState(null,'', u.pathname + u.search + u.hash);
    }catch(err){}
  }

  function openSearch(v){
    if(!tools) return;
    tools.classList.add('searching');
    if(btn) btn.classList.add('on');
    if(input){ input.value = v || ''; }
    if(qClear) qClear.hidden = !(input && input.value);
  }
  function closeSearch(){
    tools.classList.remove('searching');
    if(btn) btn.classList.remove('on');
    if(input) input.value='';
    if(qClear) qClear.hidden=true;
    state.q='';
  }

  if(tabs)tabs.addEventListener('click',function(e){
    var b=e.target.closest('button'); if(!b)return;
    [].forEach.call(tabs.children,function(x){x.classList.toggle('on',x===b);});
    state.f=b.dataset.f; state.q?runSearch():apply(); syncUrl();
  });

  if(btn)btn.addEventListener('click',function(){
    if(tools.classList.contains('searching')){ closeSearch(); apply(); syncUrl(); }
    else { openSearch(''); loadIdx(); input && input.focus(); }
  });

  if(qClear)qClear.addEventListener('click',function(){
    if(input) input.value=''; state.q=''; qClear.hidden=true;
    if(input) input.focus();
    apply(); syncUrl();
  });

  if(input){
    input.addEventListener('focus',loadIdx);
    input.addEventListener('input',function(){
      if(qClear) qClear.hidden = !input.value;
      state.q=input.value.trim().toLowerCase();
      shown=BATCH;
      runSearch(); syncUrl();
    });
    input.addEventListener('keydown',function(e){
      if(e.key==='Escape'){ closeSearch(); apply(); syncUrl(); }
    });
  }

  /* “/” 直接开搜（正在输入时不抢） */
  document.addEventListener('keydown',function(e){
    if(e.key!=='/'||e.metaKey||e.ctrlKey||e.altKey) return;
    var t=e.target, tag=(t.tagName||'').toLowerCase();
    if(tag==='input'||tag==='textarea'||t.isContentEditable) return;
    e.preventDefault(); openSearch(''); loadIdx(); input && input.focus();
  });

  // 下滑加载下一批
  function loadMore(){
    if(state.q) return;
    if(shown>=matched.length) return;
    shown=Math.min(shown+BATCH, matched.length);
    paint();
  }
  if(sentinel && 'IntersectionObserver' in window){
    try{
      new IntersectionObserver(function(es){
        if(es.some(function(x){return x.isIntersecting;})) loadMore();
      },{rootMargin:'600px 0px', threshold:0}).observe(sentinel);
    }catch(e){}
  }
  window.addEventListener('scroll',function(){
    if(state.q) return;
    var nearBottom = window.innerHeight + window.pageYOffset > document.body.scrollHeight - 800;
    if(nearBottom) loadMore();
  },{passive:true});
  setTimeout(function(){ if(state.q) return; if(shown>=matched.length) return;
    if(document.body.scrollHeight <= window.innerHeight + 200) loadMore(); }, 300);

  if(state.q){ loadIdx(); } else { apply(); }   // 带 ?q= 打开时先把索引拉起来再筛
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
