(function(){
  var h=document.documentElement;
  // 默认暗色；只有用户手动切过才尊重选择
  try{var s=localStorage.getItem('theme'); h.dataset.theme=(s==='light'?'light':'dark');}catch(e){}
  var t=document.getElementById('themeToggle');
  if(t)t.addEventListener('click',function(){
    var n=h.dataset.theme==='dark'?'light':'dark';
    h.classList.add('theme-switching');h.dataset.theme=n;
    try{localStorage.setItem('theme',n);}catch(e){}
    setTimeout(function(){h.classList.remove('theme-switching');},300);
  });
})();
