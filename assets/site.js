/* 全站共用：主题切换 + 回到顶部（阈值由 data-threshold 决定：数字像素，或 "half" 半程） */
(function () {
  var html = document.documentElement;

  // —— 主题：默认暗色，只有用户手动切过才尊重选择（放在最前面，避免闪白）
  try { html.dataset.theme = localStorage.getItem('theme') === 'light' ? 'light' : 'dark'; } catch (e) {}

  // —— Lab 暗门：长按主题图标 1.5s 解锁（再长按锁回去），或访问 /?u=lab 一次性打开
  var LAB_KEY = 'labUnlocked';
  function labOn() { try { return localStorage.getItem(LAB_KEY) === '1'; } catch (e) { return false; } }
  function applyLab() { html.classList.toggle('lab-on', labOn()); }
  applyLab();
  try {
    if (new URLSearchParams(location.search).get('u') === 'lab') {
      localStorage.setItem(LAB_KEY, '1');
      applyLab();
    }
  } catch (e) {}

  function init() {
    var toggle = document.getElementById('themeToggle');
    var longFired = false;
    var pressTimer = null;

    function startPress() {
      longFired = false;
      clearTimeout(pressTimer);
      pressTimer = setTimeout(function () {
        longFired = true;
        try { localStorage.setItem(LAB_KEY, labOn() ? '0' : '1'); } catch (e) {}
        applyLab();
        if (toggle) {
          toggle.classList.add('lab-pop');
          setTimeout(function () { toggle.classList.remove('lab-pop'); }, 560);
        }
      }, 1500);
    }
    function endPress() { clearTimeout(pressTimer); }

    if (toggle) {
      ['mousedown', 'touchstart', 'pointerdown'].forEach(function (ev) {
        toggle.addEventListener(ev, startPress, { passive: true });
      });
      ['mouseup', 'mouseleave', 'touchend', 'touchcancel', 'pointerup', 'pointercancel'].forEach(function (ev) {
        toggle.addEventListener(ev, endPress, { passive: true });
      });

      toggle.addEventListener('click', function (e) {
        if (longFired) { longFired = false; e.preventDefault(); return; }  // 长按不切主题
        var next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
        document.documentElement.classList.add('theme-switching');
        document.documentElement.dataset.theme = next;
        try { localStorage.setItem('theme', next); } catch (e) {}
        setTimeout(function () { document.documentElement.classList.remove('theme-switching'); }, 300);
      });
    }

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

  // —— 代码块复制按钮（文章页）
  function initCodeCopy() {
    var blocks = document.querySelectorAll('.body pre');
    if (!blocks.length) return;
    [].forEach.call(blocks, function (pre) {
      var btn = document.createElement('button');
      btn.className = 'code-copy';
      btn.setAttribute('aria-label', '复制代码');
      btn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
        'stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
        '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h8"/></svg>';
      btn.addEventListener('click', function () {
        var code = pre.querySelector('code');
        var text = (code || pre).innerText.replace(/\n$/, '');
        function done() {
          btn.classList.add('ok');
          setTimeout(function () { btn.classList.remove('ok'); }, 1200);
        }
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(text).then(done, done);
        } else {
          var ta = document.createElement('textarea');
          ta.value = text; document.body.appendChild(ta); ta.select();
          try { document.execCommand('copy'); } catch (e) {}
          document.body.removeChild(ta); done();
        }
      });
      pre.appendChild(btn);
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', function () { init(); initCodeCopy(); });
  else { init(); initCodeCopy(); }
})();

/* 阅读位置记忆：只存本地（localStorage），按文章路径记「当前标题 + 比例」
   刷新、关掉重开都能回到那个标题；从站内点进来则从顶部开始。 */
(function () {
  var body = document.querySelector('.body');
  if (!body || !window.localStorage) return;
  var key = 'readpos:' + location.pathname;
  var fromInside = false;
  try { fromInside = document.referrer && document.referrer.indexOf(location.origin) === 0; } catch (e) {}
  var heads = function () {
    return [].slice.call(body.querySelectorAll('h2[id],h3[id],h4[id]'));
  };
  function save() {
    var cur = null, hs = heads();
    for (var i = 0; i < hs.length; i++) {
      if (hs[i].getBoundingClientRect().top <= 96) cur = hs[i]; else break;
    }
    try {
      localStorage.setItem(key, JSON.stringify({
        id: cur ? cur.id : null,
        ratio: (window.scrollY / Math.max(1, document.body.scrollHeight - innerHeight)).toFixed(4),
        title: cur ? cur.textContent.trim().slice(0, 40) : null,
        t: Date.now()
      }));
    } catch (e) {}
  }
  var tm = null;
  window.addEventListener('scroll', function () {
    clearTimeout(tm); tm = setTimeout(save, 350);
  }, { passive: true });
  window.addEventListener('pagehide', save);

  var saved = null;
  try { saved = JSON.parse(localStorage.getItem(key) || 'null'); } catch (e) {}
  if (!saved || fromInside || location.hash) return;
  // 只恢复 30 天内的位置，且确实读到有内容的地方
  if (Date.now() - (saved.t || 0) > 30 * 864e5) return;
  if (saved.ratio < 0.03) return;

  function restore() {
    var y = 0, el = saved.id ? document.getElementById(saved.id) : null;
    if (el) y = el.getBoundingClientRect().top + window.scrollY - 88;
    else y = saved.ratio * (document.body.scrollHeight - innerHeight);
    window.scrollTo(0, y);
    var tip = document.createElement('div');
    tip.className = 'readpos-tip';
    tip.innerHTML = '已回到' + (saved.title ? '「' + saved.title + '」' : '上次位置') +
      ' · <a href="#top" data-top>从头读</a>';
    document.body.appendChild(tip);
    requestAnimationFrame(function () { tip.classList.add('on'); });
    tip.querySelector('[data-top]').addEventListener('click', function (e) {
      e.preventDefault(); window.scrollTo({ top: 0, behavior: 'smooth' }); hide();
    });
    function hide() { tip.classList.remove('on'); setTimeout(function () { tip.remove(); }, 300); }
    setTimeout(hide, 6000);
  }
  if (document.readyState === 'complete') restore();
  else window.addEventListener('load', restore);
})();

/* 代码块/表格：滑动时短暂显示横向滚动条，停下就收起来 */
(function () {
  var boxes = document.querySelectorAll('.body pre, .body .tablewrap');
  for (var i = 0; i < boxes.length; i++) {
    (function (el) {
      var t = null;
      el.addEventListener('scroll', function () {
        el.classList.add('is-scrolling');
        clearTimeout(t);
        t = setTimeout(function () { el.classList.remove('is-scrolling'); }, 900);
      }, { passive: true });
    })(boxes[i]);
  }
})();
