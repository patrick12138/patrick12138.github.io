/* 文章页：目录面板 / 站名下拉 / 回顶 / 沉浸阅读。由 add_toc 注入 <script src>。 */
(function(){
  var toc=document.getElementById('toc'); if(!toc) return;
  var list=document.getElementById('tocList');
  var fab=document.getElementById('tocFab');
  var links=[].slice.call(list.querySelectorAll('a'));
  if(!links.length) return;

  /* 手机：静置淡出，滚动时浮现（面板开着就一直显示） */
  var idleTimer=null;
  function pokeFab(){
    fab.classList.add('is-active');
    clearTimeout(idleTimer);
    idleTimer=setTimeout(function(){
      if(!toc.classList.contains('is-open')) fab.classList.remove('is-active');
    }, 1500);
  }

  /* 面板显隐 */
  function setOpen(open){
    toc.classList.toggle('is-open', open);
    toc.setAttribute('aria-hidden', open ? 'false' : 'true');
    fab.setAttribute('aria-expanded', open ? 'true' : 'false');
    if(open){ syncActive(); scrollActiveIntoView(); }
    else { pokeFab(); }
  }
  fab.addEventListener('click', function(e){ e.stopPropagation(); setOpen(!toc.classList.contains('is-open')); });

  /* PC（有鼠标、宽屏）：贴边把手悬停即展开，移开延时收起 */
  var handle=document.getElementById('tocHandle');
  var canHover = window.matchMedia('(hover:hover) and (min-width:1024px)').matches;
  if(handle){
    handle.addEventListener('click', function(e){ e.stopPropagation(); setOpen(!toc.classList.contains('is-open')); });
  }
  if(handle && canHover){
    var _closeTimer=null;
    function hoverOpen(){ clearTimeout(_closeTimer); setOpen(true); }
    function hoverClose(){ clearTimeout(_closeTimer); _closeTimer=setTimeout(function(){ setOpen(false); }, 220); }
    handle.addEventListener('mouseenter', hoverOpen);
    toc.addEventListener('mouseenter', hoverOpen);
    toc.addEventListener('mouseleave', hoverClose);
    handle.addEventListener('mouseleave', hoverClose);
  }
  document.addEventListener('click', function(e){ if(!toc.contains(e.target) && e.target!==fab) setOpen(false); });
  document.addEventListener('keydown', function(e){ if(e.key==='Escape') setOpen(false); });

  /* 滚动条只在滚动时出现 */
  var _st=null;
  list.addEventListener('scroll', function(){
    list.classList.add('is-scrolling');
    clearTimeout(_st);
    _st=setTimeout(function(){ list.classList.remove('is-scrolling'); }, 900);
  });

  /* 平滑跳转：实现收在 assets/site.js 的 window.siteUI.scrollTo，这里只算目标位置 */
  function goTo(el){
    var target=el.getBoundingClientRect().top+window.pageYOffset-84;
    if(target<0) target=0;
    window.siteUI.scrollTo(target);
  }

  links.forEach(function(a){
    a.addEventListener('click', function(e){
      var id=a.getAttribute('href').slice(1);
      var el=document.getElementById(id); if(!el) return;
      e.preventDefault();
      goTo(el); mark(id); setOpen(false);
      history.replaceState(null,'','#'+id);
    });
  });

  /* 当前所在小节高亮 */
  var targets=links.map(function(a){ return document.getElementById(a.getAttribute('href').slice(1)); });
  var bars=[].slice.call(document.querySelectorAll('.toc-bars .b'));
  var barsBox=document.querySelector('.toc-bars');
  if(barsBox && bars.length>30) barsBox.classList.add('compact');   // 标题太多时压缩，避免溢出被裁
  function mark(id){
    links.forEach(function(a){ a.classList.toggle('on', a.getAttribute('href')==='#'+id); });
    bars.forEach(function(b){ b.classList.toggle('on', b.dataset.h===id); });
  }
  function syncActive(){
    var best=null, bestTop=-1e9;
    for(var i=0;i<targets.length;i++){
      var t=targets[i]; if(!t) continue;
      var top=t.getBoundingClientRect().top;
      if(top-90<=0 && top>bestTop){ bestTop=top; best=t; }
    }
    if(!best && targets[0]) best=targets[0];
    if(best) mark(best.id);
  }
  function scrollActiveIntoView(){
    var on=list.querySelector('a.on'); if(!on) return;
    var r=on.getBoundingClientRect(), lr=list.getBoundingClientRect();
    if(r.top<lr.top || r.bottom>lr.bottom) list.scrollTop += r.top-lr.top-list.clientHeight/3;
  }
  var ticking=false;
  window.addEventListener('scroll', function(){
    if(ticking) return; ticking=true;
    requestAnimationFrame(function(){ ticking=false; syncActive(); });
  }, {passive:true});
  if(location.hash){ mark(location.hash.slice(1)); }
  syncActive();

  window.addEventListener('scroll', pokeFab, {passive:true});
  if(window.matchMedia('(max-width:1023px)').matches){ pokeFab(); setTimeout(function(){ if(!toc.classList.contains('is-open')) fab.classList.remove('is-active'); }, 2600); }
  else { fab.classList.add('is-active'); }


})();
