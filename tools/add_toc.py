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
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CSS = """
/* ─── 目录（toc） ─── */
.back-top{font-family:var(--mono);font-size:.78rem;color:var(--text-muted);text-decoration:none;
  padding:26px 0 60px;margin-left:18px;transition:color .15s}
.back-top:hover{color:var(--accent)}
.body h2,.body h3{scroll-margin-top:84px}
.toc{position:fixed;top:104px;left:calc(50% + 392px);width:196px;z-index:30;
  font-family:var(--mono);font-size:.74rem;line-height:1.55;max-height:calc(100vh - 160px);
  display:flex;flex-direction:column;transition:opacity .2s ease}
.toc-head{display:flex;align-items:center;gap:6px;color:var(--text-muted);
  font-size:.68rem;letter-spacing:.1em;text-transform:uppercase;margin-bottom:10px;cursor:pointer;
  background:none;border:none;padding:0;font-family:var(--mono)}
.toc-head:hover{color:var(--accent)}
.toc-ico{display:block}
.toc-title{display:none}
@media (max-width:1180px){ .toc.is-open .toc-title{display:inline} }
.toc-list{list-style:none;margin:0;padding:0 0 0 1px;overflow-y:auto;scrollbar-width:thin;
  border-left:1px solid var(--border)}
.toc-list a{display:block;padding:5px 0 5px 12px;margin-left:-1px;color:var(--text-muted);
  text-decoration:none;border-left:1px solid transparent;transition:color .15s,border-color .15s}
.toc-list a:hover{color:var(--heading)}
.toc-list li.lvl3 a{padding-left:24px;font-size:.7rem;opacity:.85}
.toc-list a.on{color:var(--accent);border-left-color:var(--accent)}
.toc.is-collapsed .toc-list{display:none}

.toc-close{display:none;margin-left:auto;font-size:.95rem;line-height:1;opacity:.6}
/* 手机：浮动按钮 + 底部面板 */
.toc-fab{display:none;position:fixed;right:18px;bottom:18px;z-index:40;
  font-family:var(--mono);font-size:.72rem;letter-spacing:.06em;padding:9px 14px;
  background:color-mix(in srgb,var(--bg) 88%,var(--text) 8%);color:var(--text-muted);
  border:1px solid var(--border);cursor:pointer}
.toc-fab:hover{color:var(--accent);border-color:color-mix(in srgb,var(--accent) 45%,transparent)}
@media (max-width:1180px){
  .toc{display:none}
  .toc-fab{display:block}
  .toc.is-open{display:flex !important;left:16px;right:16px;width:auto;top:auto;bottom:70px;max-height:60vh;
    padding:16px 18px;background:color-mix(in srgb,var(--bg) 94%,transparent);
    backdrop-filter:blur(16px);border:1px solid var(--border);box-shadow:0 18px 40px rgba(0,0,0,.35);z-index:60}
  .toc.is-open .toc-head{font-size:.72rem;margin-bottom:8px;width:100%}
  .toc.is-open .toc-close{display:inline}
  .toc.is-open ~ .toc-fab{display:none}
  .toc.is-open .toc-list{display:block !important;font-size:.86rem}
  .toc.is-open .toc-list a{padding:7px 0 7px 12px}
}
"""

JS = """
(function(){
  var toc=document.getElementById('toc'); if(!toc) return;
  var list=document.getElementById('tocList');
  var head=document.getElementById('tocHead');
  var fab=document.getElementById('tocFab');
  var links=[].slice.call(list.querySelectorAll('a'));
  if(!links.length) return;

  var key='tocCollapsed';
  try{ if(localStorage.getItem(key)==='1') toc.classList.add('is-collapsed'); }catch(e){}
  function syncChev(){ head.setAttribute('aria-expanded', toc.classList.contains('is-collapsed')?'false':'true'); }

  var mobile=window.matchMedia('(max-width:1180px)');
  head.addEventListener('click',function(){
    if(mobile.matches){ toc.classList.remove('is-open'); return; }
    toc.classList.toggle('is-collapsed');
    try{ localStorage.setItem(key, toc.classList.contains('is-collapsed')?'1':'0'); }catch(e){}
    syncChev();
  });
  if(fab) fab.addEventListener('click',function(){ toc.classList.toggle('is-open'); });
  document.addEventListener('keydown',function(e){ if(e.key==='Escape') toc.classList.remove('is-open'); });

  // 原生 smooth 不支持（部分 WebView / 后台标签页 rAF 被暂停）时兜底直接跳
  function smoothTo(el){
    var target=el.getBoundingClientRect().top+window.pageYOffset-84;
    if(target<0) target=0;
    var before=window.pageYOffset;
    try{ window.scrollTo({top:target,behavior:'smooth'}); }
    catch(e){ window.scrollTo(0,target); }
    setTimeout(function(){
      if(Math.abs(window.pageYOffset-before)<4) window.scrollTo(0,target);
    },400);
  }

  links.forEach(function(a){
    a.addEventListener('click',function(e){
      var id=a.getAttribute('href').slice(1);
      var el=document.getElementById(id); if(!el) return;
      e.preventDefault();
      smoothTo(el);
      mark(id);
      toc.classList.remove('is-open');
      history.replaceState(null,'','#'+id);
    });
  });

  var targets=links.map(function(a){ return document.getElementById(a.getAttribute('href').slice(1)); });
  function mark(id){
    links.forEach(function(a){ a.classList.toggle('on', a.getAttribute('href')==='#'+id); });
  }
  var ticking=false;
  function onScroll(){
    if(ticking) return; ticking=true;
    requestAnimationFrame(function(){
      ticking=false;
      var best=null, bestTop=-1e9;
      for(var i=0;i<targets.length;i++){
        var t=targets[i]; if(!t) continue;
        var top=t.getBoundingClientRect().top;
        if(top-90<=0 && top>bestTop){ bestTop=top; best=t; }
      }
      if(!best && targets[0]) best=targets[0];
      if(best) mark(best.id);
    });
  }
  window.addEventListener('scroll',onScroll,{passive:true});
  syncChev();
  if(location.hash) mark(location.hash.slice(1));
  onScroll();
})();
"""

BACKTOP_JS = """
(function(){
  var b=document.getElementById('backTop'); if(!b) return;
  b.addEventListener('click',function(e){
    e.preventDefault();
    var before=window.pageYOffset;
    try{ window.scrollTo({top:0,behavior:'smooth'}); }catch(err){ window.scrollTo(0,0); }
    setTimeout(function(){ if(Math.abs(window.pageYOffset-before)<4) window.scrollTo(0,0); },400);
  });
})();
"""

HEAD = ('<nav class="toc" id="toc" aria-label="文章目录">'
        '<button class="toc-head" id="tocHead" aria-label="目录" aria-expanded="true">'
        '<svg class="toc-ico" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.8" stroke-linecap="round" aria-hidden="true">'
        '<line x1="9" y1="6" x2="20" y2="6"/><line x1="9" y1="12" x2="20" y2="12"/>'
        '<line x1="9" y1="18" x2="20" y2="18"/>'
        '<circle cx="4.6" cy="6" r="1.2" fill="currentColor" stroke="none"/>'
        '<circle cx="4.6" cy="12" r="1.2" fill="currentColor" stroke="none"/>'
        '<circle cx="4.6" cy="18" r="1.2" fill="currentColor" stroke="none"/></svg>'
        '<span class="toc-title">目录</span>'
        '<span class="toc-close" aria-hidden="true">\u00d7</span></button>'
        '<ol class="toc-list" id="tocList">%s</ol></nav>'
        '<button class="toc-fab" id="tocFab" aria-label="文章目录">目录</button>')

HEAD_RE = re.compile(r'<nav class="toc" id="toc".*?<button class="toc-fab"[^>]*>目录</button>', re.S)


def strip_toc(doc):
    doc = HEAD_RE.sub("", doc)
    doc = re.sub(r'<a class="back-top".*?</a>', "", doc, flags=re.S)
    doc = re.sub(r"\n<script>\n\(function\(\)\{\n  var b=document\.getElementById\('backTop'\).*?\}\)\(\);\n</script>", "", doc, flags=re.S)
    doc = re.sub(r'\n/\* ─── 目录（toc） ─── \*/.*?(?=</style>)', "", doc, flags=re.S)
    doc = re.sub(r'\n\(function\(\)\{\n  var toc=document\.getElementById\(\'toc\'\).*?\}\)\(\);\n', "", doc, flags=re.S)
    return doc


def build_toc(doc):
    """给正文 h2/h3 加 id，返回 (新文档, 目录 html)。"""
    m = re.search(r'<div class="body">(.*?)<a class="back"', doc, re.S)
    if not m:
        return doc, ""
    body = m.group(1)
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

    body2 = re.sub(r'<(h2|h3)([^>]*)>(.*?)</\1>', repl, body, flags=re.S)
    if len(items) < 3:
        return doc, ""
    li = "".join(
        '<li class="lvl%s"><a href="#%s">%s</a></li>' % ("3" if tag == "h3" else "2", hid, htmllib.escape(t))
        for tag, hid, t in items
    )
    doc = doc[:m.start(1)] + body2 + doc[m.end(1):]
    return doc, li


def process(path):
    doc = open(path, encoding="utf-8").read()
    if 'class="body"' not in doc:
        return False
    doc = strip_toc(doc)
    doc, li = build_toc(doc)
    if not li:
        doc = doc.replace("</style>", CSS + "</style>", 1)
        doc = re.sub(r'(<a class="back"[^>]*>.*?</a>)',
                     r'\1<a class="back-top" href="#" id="backTop">↑ 回到顶部</a>', doc, count=1, flags=re.S)
        doc = doc.replace("</body>", "<script>" + BACKTOP_JS + "</script>\n</body>", 1)
        open(path, "w", encoding="utf-8").write(doc)
        return False
    # CSS
    doc = doc.replace("</style>", CSS + "</style>", 1)
    # 「↑ 回到顶部」放在「← 返回首页」旁边
    doc = re.sub(r'(<a class="back"[^>]*>.*?</a>)',
                 r'\1<a class="back-top" href="#" id="backTop">↑ 回到顶部</a>', doc, count=1, flags=re.S)
    doc = doc.replace("</body>", "<script>" + BACKTOP_JS + "</script>\n</body>", 1)
    # 目录标记：放在 body 之前（正文起点前）
    doc = doc.replace('<div class="body">', HEAD % li + '<div class="body">', 1)
    # JS
    doc = doc.replace("</body>", "<script>" + JS + "</script>\n</body>", 1)
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
