/* 全站共用：主题切换 + 回到顶部（阈值由 data-threshold 决定：数字像素，或 "half" 半程） */
// 公共小工具：平滑滚动（WebView 里 smooth 可能被忽略，400ms 没动就硬跳）
// 文章页内联的目录脚本会调 window.siteUI.scrollTo，别再各写一份
window.siteUI = window.siteUI || {
  scrollTo: function (y) {
    var before = window.pageYOffset;
    try { window.scrollTo({ top: y, behavior: 'smooth' }); } catch (e) { window.scrollTo(0, y); }
    setTimeout(function () { if (Math.abs(window.pageYOffset - before) < 4) window.scrollTo(0, y); }, 400);
  }
};

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
        document.documentElement.dataset.theme = next;
        try { localStorage.setItem('theme', next); } catch (e) {}
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
      // 立刻重置：不让按钮带着 hover/focus 的强调色停在顶部，也别等滚动事件
      btn.blur();
      btn.classList.remove('is-idle', 'show');
      window.siteUI.scrollTo(0);
      setTimeout(update, 420);   // 兜底：程序化滚动不一定派发 scroll
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
      // 按钮不能放进 pre：pre 是横向滚动容器，绝对定位的子元素会跟着内容滚走，
      // 一横滑按钮就跑到左边界外面去了。所以外面包一层只负责定位。
      var wrap = document.createElement('div');
      wrap.className = 'codewrap';
      pre.parentNode.insertBefore(wrap, pre);
      wrap.appendChild(pre);

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
      wrap.appendChild(btn);

      // 会横滑的代码块，右侧留一条通道，按钮不压到代码
      var mark = function () {
        // 先摘掉再量：is-wide 会给 pre 加 44px 右内边距，留着量会自我维持
        wrap.classList.remove('is-wide');
        if (pre.scrollWidth > pre.clientWidth + 2) wrap.classList.add('is-wide');
      };
      mark();
      window.addEventListener('resize', mark, { passive: true });
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
    document.body.classList.add('readpos-on');
    requestAnimationFrame(function () { tip.classList.add('on'); });
    tip.querySelector('[data-top]').addEventListener('click', function (e) {
      e.preventDefault(); window.scrollTo({ top: 0, behavior: 'smooth' }); hide();
    });
    function hide() {
      tip.classList.remove('on');
      document.body.classList.remove('readpos-on');
      setTimeout(function () { tip.remove(); }, 300);
    }
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

/* 沉浸阅读：只留标题、正文、目录。状态记在 localStorage，跨文章跨刷新保持。
   进入时尝试真全屏；系统手势/Esc 退出全屏后同步退出沉浸态。 */
(function () {
  var KEY = 'readmode';
  var btn = document.getElementById('readBtn');
  if (!btn || !document.querySelector('.article')) return;

  var html = document.documentElement;
  var meta = document.querySelector('.article .meta');
  var home = btn.parentNode;                    // 普通态：留在 .meta 里
  var exitLink = document.getElementById('readExit');
  var bar = document.querySelector('.bar');

  function paint(on) {
    html.classList.toggle('readmode', on);
    btn.setAttribute('aria-pressed', on ? 'true' : 'false');
    btn.setAttribute('aria-label', on ? '退出沉浸阅读' : '沉浸阅读');
    btn.setAttribute('title', on ? '退出沉浸阅读（Esc）' : '沉浸阅读');
    if (on) { document.body.appendChild(btn); } else if (home) { home.appendChild(btn); }
  }

  function save(on) { try { localStorage.setItem(KEY, on ? '1' : '0'); } catch (e) {} }

  /* 切换时保住阅读位置：以正文里第一个标题为锚，算它在文档里的位移再补回滚动。
     隐藏顶栏/元信息/来源块会让它们下方的所有内容整体上移，光补顶栏高度不够。 */
  function keepPosition(mutate) {
    var ref = document.querySelector('.body h2, .body h3, .body p');
    var before = ref ? ref.getBoundingClientRect().top + window.pageYOffset : 0;
    mutate();
    if (!ref) return;
    var after = ref.getBoundingClientRect().top + window.pageYOffset;
    var delta = after - before;
    if (delta) window.scrollTo(0, Math.max(0, window.pageYOffset + delta));
  }

  function enter() {
    keepPosition(function () { paint(true); });
    save(true);
  }

  function leave() {
    html.classList.remove('no-ui');
    clearTimeout(hideTimer);
    keepPosition(function () { paint(false); });
    save(false);
  }

  function toggle() { html.classList.contains('readmode') ? leave() : enter(); }

  btn.addEventListener('click', toggle);
  if (exitLink) exitLink.addEventListener('click', function (e) { e.preventDefault(); leave(); });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && html.classList.contains('readmode') && !document.fullscreenElement) leave();
  });

  /* 第二层：沉浸态里「手在动就退场」——滚动立刻隐藏控件，静止也不回来；
     轻点空白处（移动端）或移动鼠标（桌面）才临时召出。 */
  var hideTimer = null;
  function uiOff() { if (html.classList.contains('readmode')) html.classList.add('no-ui'); }
  function uiOn(ms) {
    if (!html.classList.contains('readmode')) return;
    html.classList.remove('no-ui');
    clearTimeout(hideTimer);
    hideTimer = setTimeout(uiOff, ms || 2600);
  }
  window.addEventListener('scroll', uiOff, { passive: true });
  document.addEventListener('mousemove', function () { uiOn(2600); }, { passive: true });
  document.addEventListener('click', function (e) {
    if (!html.classList.contains('readmode')) return;
    if (e.target.closest('a,button,input,pre,table')) return;   // 点在可交互元素上不拦截
    uiOn(3000);
  });

  // 恢复上次状态（全屏必须由用户手势触发，所以这里只恢复样式）
  var on = false;
  try { on = localStorage.getItem(KEY) === '1'; } catch (e) {}
  if (on) { paint(true); uiOn(2600); }
})();
