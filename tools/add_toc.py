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

JS = """
(function(){
  var toc=document.getElementById('toc'); if(!toc) return;
  var list=document.getElementById('tocList');
  var head=document.getElementById('tocHead');
  var fab=document.getElementById('tocFab');
  var links=[].slice.call(list.querySelectorAll('a'));
  // 滚动条只在滚动时出现，静置时隐藏
  var _st=null;
  function edge(){
    // 滚到底就不显示底部渐隐；不需要滚动时也算到底
    var atBottom = list.scrollTop + list.clientHeight >= list.scrollHeight - 2;
    toc.classList.toggle('at-bottom', atBottom);
  }
  if(list){
    list.addEventListener('scroll',function(){
      list.classList.add('is-scrolling');
      clearTimeout(_st);
      _st=setTimeout(function(){ list.classList.remove('is-scrolling'); },900);
      edge();
    },{passive:true});
  }
  edge();
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

BRAND_JS = """
(function(){
  var set=document.getElementById('brandSet'); if(!set) return;
  var btn=document.getElementById('brandBtn');
  function close(){ set.classList.remove('open'); btn.setAttribute('aria-expanded','false'); }
  btn.addEventListener('click',function(e){
    e.stopPropagation();
    var open=set.classList.toggle('open');
    btn.setAttribute('aria-expanded',open?'true':'false');
  });
  document.addEventListener('click',function(e){ if(!set.contains(e.target)) close(); });
  document.addEventListener('keydown',function(e){ if(e.key==='Escape') close(); });
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
        '<button class="toc-fab" id="tocFab" aria-label="目录">'
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.8" stroke-linecap="round" aria-hidden="true">'
        '<line x1="9" y1="6" x2="20" y2="6"/><line x1="9" y1="12" x2="20" y2="12"/>'
        '<line x1="9" y1="18" x2="20" y2="18"/>'
        '<circle cx="4.6" cy="6" r="1.2" fill="currentColor" stroke="none"/>'
        '<circle cx="4.6" cy="12" r="1.2" fill="currentColor" stroke="none"/>'
        '<circle cx="4.6" cy="18" r="1.2" fill="currentColor" stroke="none"/></svg></button>')



def strip_toc(doc):
    """把自己注入过的东西全部清干净（含重复注入的多份），保证可重复执行。"""
    # 目录结构：从 <nav class="toc" 一直剥到它的 </nav>，不依赖内部细节，
    # 否则旧版本注入的变体会漏网，越跑越多（曾出现 13 份重叠）
    doc = re.sub(r'<nav class="toc"[^>]*>.*?</nav>\s*', "", doc, flags=re.S)
    doc = re.sub(r'<button class="toc-fab"[^>]*>.*?</button>\s*', "", doc, flags=re.S)
    doc = re.sub(r'<button class="toc-tab"[^>]*>.*?</button>\s*', "", doc, flags=re.S)
    doc = re.sub(r'<a class="back-top".*?</a>', "", doc, flags=re.S)
    doc = re.sub(r'<button class="to-top"[^>]*>.*?</button>\s*', "", doc, flags=re.S)
    # 别的会话注入过的英文版浮动按钮
    doc = re.sub(r'<button class="toc-fab"[^>]*>.*?</button>', "", doc, flags=re.S)
    doc = re.sub(r'<button class="toc-tab"[^>]*>.*?</button>', "", doc, flags=re.S)
    # 注入的脚本块（可能有多份，全部清掉，稍后重新注入一次）
    for sig in ("brandSet", "backTop", "var toc=document.getElementById", "getElementById('toTop')"):
        pat = r"\n<script>\n\(function\(\)\{[^<]*?%s[\s\S]*?\}\)\(\);\n</script>" % re.escape(sig)
        doc = re.sub(pat, "", doc)
    # 站名下拉：还原成普通站名链接，稍后按当前文章分类重新生成
    mm = re.search(r'<div class="brandset" id="brandSet">.*?<a role="menuitem" href="([^"]*)\?tab=all"', doc, re.S)
    if mm:
        doc = re.sub(r'<div class="brandset" id="brandSet">.*?</div></div>',
                     '<a class="brand" href="%s">patrick</a>' % mm.group(1), doc, count=1, flags=re.S)
    # 清掉之前反复 strip 留下的空 script
    doc = re.sub(r"\n?<script></script>", "", doc)
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


TOP_BTN = ('<button class="to-top" id="toTop" data-threshold="half" aria-label="返回顶部" title="返回顶部">'
           '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
           'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
           '<path d="M12 19V5M5 12l7-7 7 7"/></svg></button>')

BRAND_RE = re.compile(r'<a class="brand" href="([^"]*)">patrick</a>')


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


def inject_brand(doc):
    """把导航里的 patrick 换成可下拉的站名，菜单直接跳到首页的分类。"""
    if 'id="brandSet"' in doc:
        return doc
    m = BRAND_RE.search(doc)
    if not m:
        return doc
    base = m.group(1)
    mk = re.search(r'<div class="meta">[^<]*·\s*(搬运|原创|个人)', doc)
    cur = {"搬运": "repost", "原创": "own", "个人": "own"}.get(mk.group(1) if mk else "", "")
    menu = "".join(
        '<a role="menuitem" href="%s?tab=%s"%s>%s</a>'
        % (base, f, ' class="on"' if f == cur else "", label)
        for f, label in (("all", "全部文章"), ("repost", "搬运"), ("own", "个人"))
    )
    block = ('<div class="brandset" id="brandSet">'
             '<button class="brand-btn" id="brandBtn" aria-haspopup="true" aria-expanded="false">patrick'
             '<svg class="caret" width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
             'stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
             '<path d="M6 9l6 6 6-6"/></svg></button>'
             '<div class="brand-menu" role="menu">%s</div></div>' % menu)
    return doc[:m.start()] + block + doc[m.end():]


def process(path):
    doc = open(path, encoding="utf-8").read()
    if 'class="body"' not in doc:
        return False
    doc = strip_toc(doc)
    doc = normalize_nav(doc)
    doc = inject_brand(doc)
    doc = inject_top_btn(doc)
    doc, li = build_toc(doc)
    if not li:
        doc = doc.replace("</body>", "<script>" + BRAND_JS + "</script>\n</body>", 1)
        open(path, "w", encoding="utf-8").write(doc)
        return False
    doc = doc.replace("</body>", "<script>" + BRAND_JS + "</script>\n</body>", 1)
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
