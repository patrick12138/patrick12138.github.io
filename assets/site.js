/* 全站共用：主题切换 + 回到顶部（阈值由 data-threshold 决定：数字像素，或 "half" 半程） */
// 公共小工具：平滑滚动（WebView 里 smooth 可能被忽略，400ms 没动就硬跳）
// 文章页内联的目录脚本会调 window.siteUI.scrollTo，别再各写一份

/* 右下热区：PC 上只有鼠标移到这块区域，浮动控件（回到顶部 / 沉浸阅读）才浮现。
   之前是“动一下鼠标就出现”，阅读时太吵。 */
window.siteUI = window.siteUI || {};
window.siteUI.hot = function (e, size) {
  var z = size || 240;
  return e.clientX > window.innerWidth - z && e.clientY > window.innerHeight - z;
};

window.siteUI = window.siteUI || {
  scrollTo: function (y) {
    var before = window.pageYOffset;
    try { window.scrollTo({ top: y, behavior: 'smooth' }); } catch (e) { window.scrollTo(0, y); }
    setTimeout(function () { if (Math.abs(window.pageYOffset - before) < 4) window.scrollTo(0, y); }, 400);
  }
};

(function () {
  var html = document.documentElement;
  function hasPointer() {
    try { return window.matchMedia('(hover:hover) and (pointer:fine)').matches; } catch (e) { return false; }
  }

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
      if (mode !== 'half') { var n = parseInt(mode, 10); return isNaN(n) ? 600 : n; }
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
    // 桌面（有鼠标）滚动不再点亮控件——只有鼠标进右下热区才出现；触屏没有光标，保持滚动浮现
    var canHover = true;
    try { canHover = window.matchMedia('(hover:hover)').matches; } catch (e) {}
    window.addEventListener('scroll', function () {
      update();
      if (!canHover) poke();                                  // 触屏：滚动浮现
      else if (!hotOn && btn.classList.contains('show')) btn.classList.add('is-idle');  // 桌面：只有热区才亮
    }, { passive: true });
    window.addEventListener('resize', function () { update(); poke(); }, { passive: true });
    var hotOn = false;
    window.addEventListener('mousemove', function (e) {
      hotOn = window.siteUI.hot(e);
      if (hotOn) poke();
      else if (btn.classList.contains('show')) btn.classList.add('is-idle');
    }, { passive: true });
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

/* 沉浸阅读：只留标题、正文、目录。
   两个按钮各有固定位置（入口在标题右上、出口在视口右上），只切 display，
   全程不搬 DOM、不改定位 —— 因此不可能出现“按钮在跳”。
   状态记在 localStorage，跨文章、跨刷新保持。 */
(function () {
  var KEY = 'readmode';
  var open = document.getElementById('readOpen');
  var exitLink = document.getElementById('readExit');
  if (!open || !document.querySelector('.article')) return;

  var html = document.documentElement;

  function paint(on) {
    html.classList.toggle('readmode', on);
    if (open) {
      open.setAttribute('aria-pressed', on ? 'true' : 'false');
      open.setAttribute('aria-label', on ? '退出沉浸阅读' : '沉浸阅读');
      open.setAttribute('title', on ? '退出沉浸阅读（Esc）' : '沉浸阅读');
    }
  }
  function save(on) { try { localStorage.setItem(KEY, on ? '1' : '0'); } catch (e) {} }

  /* 顶栏/元信息被隐藏会让下方内容整体上移，用正文首个标题做锚把位置补回来 */
  function keepPosition(mutate) {
    var ref = document.querySelector('.body h2, .body h3, .body p');
    var before = ref ? ref.getBoundingClientRect().top + window.pageYOffset : 0;
    mutate();
    if (!ref) return;
    var delta = (ref.getBoundingClientRect().top + window.pageYOffset) - before;
    if (delta) window.scrollTo(0, Math.max(0, window.pageYOffset + delta));
  }

  // 真全屏只在桌面（有精确指针、能悬停、宽度够）；手机平板不碰视口，避免转屏
  function desktop() {
    try { return window.matchMedia('(hover:hover) and (pointer:fine)').matches && window.innerWidth >= 1024; }
    catch (e) { return false; }
  }
  function fsEnter() {
    if (!desktop()) return;
    try {
      if (html.requestFullscreen) html.requestFullscreen().catch(function () {});
      else if (html.webkitRequestFullscreen) html.webkitRequestFullscreen();
    } catch (e) {}
  }
  function fsExit() {
    try {
      if (document.fullscreenElement && document.exitFullscreen) document.exitFullscreen();
      else if (document.webkitFullscreenElement && document.webkitExitFullscreen) document.webkitExitFullscreen();
    } catch (e) {}
  }

  var hideTimer = null;
  function uiOff() { if (html.classList.contains('readmode')) html.classList.add('no-ui'); }
  function uiOn(ms) {
    if (!html.classList.contains('readmode')) return;
    html.classList.remove('no-ui');
    clearTimeout(hideTimer);
    hideTimer = setTimeout(uiOff, ms || 2600);
  }

  function enter() {
    keepPosition(function () { paint(true); });
    save(true);
    fsEnter();
    if (!hasPointer()) uiOn(2600);   // 触屏：先露 2.6 秒提示出口；桌面交给热区逻辑，别闪
    else uiOff();
    document.body.classList.remove('readpos-on');
    var tip = document.querySelector('.readpos-tip');
    if (tip) tip.remove();
  }
  function leave() {
    if (autoEntered) optedOut = true;
    html.classList.remove('no-ui');
    clearTimeout(hideTimer);
    keepPosition(function () { paint(false); });
    save(false);
    fsExit();
  }

  /* PC 浏览器全屏（F11）无法用 Fullscreen API 事件感知，用「浏览器 chrome 高度」推断：
     outerHeight - innerHeight 在窗口态约 80~120px，进 F11 后降到 0~8px。
     同时把 innerHeight ≈ screen.height 作为第二判据（Firefox / 部分 Linux 桌面）。 */
  var autoEntered = false;      // 这次沉浸是不是被全屏自动打开的
  var optedOut = false;         // 全屏期间用户主动退出过
  var chromeBase = null;        // 窗口态下 chrome 的基准高度

  function chromeH() {
    var o = window.outerHeight || 0, i = window.innerHeight || 0;
    if (!o || !i) return -1;
    return o - i;
  }
  function fsLike() {
    try {
      if (!desktop()) return false;
      var c = chromeH();
      if (c >= 0 && c <= 8) return true;                        // 没有 chrome = 全屏
      if (window.innerHeight >= screen.height - 2) return true;  // 高度顶满 = 全屏
      if (chromeBase !== null && c >= 0 && c < chromeBase - 40) return true;  // chrome 掉了 40px 以上
      return false;
    } catch (e) { return false; }
  }

  var resizeTimer = null;
  window.addEventListener('resize', function () {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(function () {
      var c = chromeH(), f = fsLike();
      if (!f && c > 20) chromeBase = Math.max(chromeBase || 0, c);  // 只在窗口态更新基准
      if (f && !html.classList.contains('readmode') && !optedOut) {
        autoEntered = true;
        enter();
        save(false);              // 全屏是环境状态，不写进 localStorage
      } else if (!f) {
        if (autoEntered && html.classList.contains('readmode')) leave();
        autoEntered = false;
        optedOut = false;
      }
    }, 220);
  }, { passive: true });
  chromeBase = chromeH() > 20 ? chromeH() : null;
  window.__fsLike = fsLike;      // 调试：控制台里 __fsLike() 可看当前判定
  window.__fsInfo = function () { return { chrome: chromeH(), inner: innerHeight, screen: screen.height, base: chromeBase }; };

  // 有些浏览器按 F11 不会派发 resize（或有延迟），键帽也补一次
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'F11') return;
    setTimeout(function () { window.dispatchEvent(new Event('resize')); }, 350);
  });

  /* 沉浸按钮也要“停一下就消失”（PC 端常驻太吵） */
  var readIdle = null;
  function pokeRead() {
    if (!open) return;
    open.classList.remove('is-idle');
    clearTimeout(readIdle);
    readIdle = setTimeout(function () { open.classList.add('is-idle'); }, 1500);
  }
  window.addEventListener('mousemove', function (e) {
    if (window.siteUI.hot(e)) pokeRead();
    else if (open) open.classList.add('is-idle');
  }, { passive: true });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Tab') pokeRead();     // 键盘用户走 Tab 时也让它出现
  });
  if (!hasPointer()) pokeRead(); else open.classList.add('is-idle');

  open.addEventListener('click', function () {
    html.classList.contains('readmode') ? leave() : enter();
    open.blur();               // 触屏点完不留悬停/焦点
  });
  if (exitLink) exitLink.addEventListener('click', function (e) { e.preventDefault(); leave(); });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && html.classList.contains('readmode')) leave();
  });

  // 滚动即隐；轻点空白/移动鼠标召出
  window.addEventListener('scroll', uiOff, { passive: true });
  document.addEventListener('mousemove', function (e) {
    if (!html.classList.contains('readmode')) return;
    // 桌面：光标不在右下热区就不唤醒（沉浸态尤其不能一动鼠标就冒出控件）
    var hover = true;
    try { hover = window.matchMedia('(hover:hover)').matches; } catch (err) {}
    if (hover && !window.siteUI.hot(e)) return;
    uiOn(2600);
  }, { passive: true });
  document.addEventListener('click', function (e) {
    if (!html.classList.contains('readmode')) return;
    if (e.target.closest('a,button,input,pre,table')) return;
    uiOn(3000);
  });

  var on = false;
  try { on = localStorage.getItem(KEY) === '1'; } catch (e) {}
  if (on) { paint(true); if (hasPointer()) uiOff(); else uiOn(2600); }
})();
