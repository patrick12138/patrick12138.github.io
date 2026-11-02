/* 全站共用：主题切换 + 回到顶部（阈值由 data-threshold 决定：数字像素，或 "half" 半程） */
(function () {
  var html = document.documentElement;

  // —— 主题：默认暗色，只有用户手动切过才尊重选择（放在最前面，避免闪白）
  try { html.dataset.theme = localStorage.getItem('theme') === 'light' ? 'light' : 'dark'; } catch (e) {}

  function init() {
    var toggle = document.getElementById('themeToggle');
    if (toggle) toggle.addEventListener('click', function () {
      var next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
      document.documentElement.classList.add('theme-switching');
      document.documentElement.dataset.theme = next;
      try { localStorage.setItem('theme', next); } catch (e) {}
      setTimeout(function () { document.documentElement.classList.remove('theme-switching'); }, 300);
    });

    var btn = document.getElementById('toTop');
    if (!btn) return;
    var mode = btn.getAttribute('data-threshold') || '600';

    function threshold() {
      if (mode !== 'half') return parseInt(mode, 10) || 600;
      var docH = Math.max(document.body.scrollHeight, document.documentElement.scrollHeight);
      var max = docH - window.innerHeight;
      return max > 0 ? max / 2 : 600;
    }
    function update() { btn.classList.toggle('show', window.pageYOffset > threshold()); }

    // 静置淡出：滚动/移动鼠标/触摸才浮现，1.5s 没动作就隐去（与目录按钮同一套体感）
    var idleTimer = null;
    function poke() {
      btn.classList.remove('is-idle');
      clearTimeout(idleTimer);
      idleTimer = setTimeout(function () {
        if (btn.classList.contains('show')) btn.classList.add('is-idle');
      }, 1500);
    }
    function goTop() {
      var before = window.pageYOffset;
      try { window.scrollTo({ top: 0, behavior: 'smooth' }); } catch (e) { window.scrollTo(0, 0); }
      // WebView 里 smooth 可能被忽略，400ms 没动就硬跳
      setTimeout(function () { if (Math.abs(window.pageYOffset - before) < 4) window.scrollTo(0, 0); }, 400);
    }
    window.addEventListener('scroll', function () { update(); poke(); }, { passive: true });
    window.addEventListener('resize', function () { update(); poke(); }, { passive: true });
    window.addEventListener('mousemove', poke, { passive: true });
    window.addEventListener('touchstart', poke, { passive: true });
    btn.addEventListener('click', goTop);
    update(); poke();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
