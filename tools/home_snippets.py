"""首页 index.html 的内嵌常量：搜索/标签页脚本与主题切换图标。

gen_index.py 生成时原样拼入，内容改这里即可。
"""

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
