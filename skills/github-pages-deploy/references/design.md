# 设计规范：交互元素、目录、主题、组件

## 外链一律同窗跳转（移动端硬性要求）

**不要在 `<a>` 上写 `target="_blank"`。** Android WebView（含 Minis 内置浏览器、微博/微信/闲鱼内置浏览器）
不处理新窗口请求，点了**毫无反应**——PC 上正常，手机上像坏掉。2026-11 的 about 页 GitHub / Telegram
按钮就是这么被反馈「点了不跳转」的。

- 正确写法：`<a href="https://..." rel="noopener">`
- `md2post.py` 已经在生成后统一剥掉 `target="_blank"`，粘进来的 md 里写了也没事
- 一定要新标签页，只能靠 JS `window.open()`，但同样有被 WebView 拦的风险，不值得

## 按钮只放图标（Patrick 硬性要求）

- **按钮里尽量不放文字。** 浮动/工具按钮（目录、返回顶部、主题、关闭）一律
  「图标 + `aria-label`」，最多配 `title`。文字说明交给页面本身，不塞进按钮。
- 浮动图标按钮统一：**圆形 36×36、`border-radius:999px`**、1px 边 `var(--border)`，
  静止 `var(--text-muted)` → hover/focus `var(--accent)`（边色取 45% accent）。
  手机端 `right:18px;bottom:24px`。同页同类按钮尺寸必须一致。
- **要文字就用文字链接**：`← 返回首页`、`Lab →` 这类是 `.back` 的等宽字体链接，不是按钮。
  回到顶部只用右下角圆形箭头按钮，正文末尾不再放「↑ 回到顶部」文字链接。
- 只有表单/命令类按钮（`复制结果`、`只看想玩`、`重来`）可以带文字，那是动作名。
- 不用 emoji 当图标；线性图标 stroke 1.7–2，和现有风格一致。

## 目录（toc）

`tools/add_toc.py` 注入，可重复执行，正文 h2/h3 少于 3 个自动跳过。

**PC（≥1024，有鼠标）—— 悬停即出，参考 Notion / 少数派：**

- 屏幕右缘是**标题横杠序列**：每个 h2/h3 一条横杠（h2 长 18px、h3 短 11px），
  **读到哪条亮哪条**（强调色 + 加宽到 24px），其余 muted；整体从 `top:88px` 往下排，
  高 `calc(100vh - 160px)`，标题超过 30 条自动切到 compact（gap 3px / 2px 高）。
  无底无框，hover 时整体提亮，点一下也能开面板。
- **鼠标移上去（或移入面板）就展开**面板，从右侧滑出 288px、`max-height:72vh`；
  移开 220ms 后自动收起。无 hover 能力的设备（触屏笔记本）点一下也能开。
- 面板**没有头部、没有标题、没有关闭按钮**——只有条目列表（参考 Readwise / Notion 的克制做法）。
- 打开时把手淡出，避免和面板叠在一起。

**移动 / iPad（≤1023）—— 点按 + 静置淡出：**

- 右下角圆形图标按钮（40px，无文字），点开底部面板，两侧各留 12px，最大 60vh。
- **面板同样无头部无 ×**，点面板外 / Esc 即收。
- **按钮平时隐藏**：滚动时淡入浮现（opacity 0→1 + `translateY(10px)→0` + `scale(.94)→1`，240ms），
  停止滚动 1.5s 后淡出；进页面先亮 2.6s 提示存在；关闭面板后也会回场 1.5s 再隐去。
- 面板本身带浮起动画（`translateY(14px) scale(.985)` → 原位，220ms），不是硬切。
- **面板打开时按钮让位**（opacity 0 + pointer-events none），避免压在面板底边上；关闭靠点面板外面或按 Esc（面板里没有 ×）。
- 点 × / 点面板外 / Esc 关闭；点条目跳转后自动收起。

**共用细节**：条目按 lvl2/lvl3 缩进分级，当前小节强调色 + 左侧 2px 竖条；
滚动条只在滚动时出现；锚点 `scroll-margin-top:84px` 避开 sticky bar。
浮动按钮堆叠（从下往上）：目录 22px → 回到顶部 74px → 面板 126px；手机档 18 / 80 / 132。

**为什么不做右侧常驻栏**：常驻栏让「正文+目录」整块右偏，正文看着不居中；把正文左移又会让
首页→文章页标题跳位。改成「悬停浮层」后正文独占居中，跨页不跳动。

**坑**：`scrollIntoView({behavior:'smooth'})` 在 WebView 里是空操作 → 用
`window.scrollTo({behavior:'smooth'})` + 400ms 兜底硬跳；后台标签页 rAF 暂停，别用 rAF 做动画。

## 样式组织：文章统一，工具各自为政

- 博客部分（首页 / Lab 索引 / 所有 post）共用 `assets/post.css`、`assets/home.css`、`assets/site.js`，
  改文章排版只改一处。断点固定：`≤720px` 移动、`>720px` 桌面、`>1180px` 右侧目录。
- `/tga/`、`/backlog/`、`/about/` 这类工具页各自独立内联样式。
  Patrick 明确说过：清单是他自己的工具，风格不同很正常，**不要为"统一"去合并**。

## 页面写法

- **博客页共享外链样式**：首页 / Lab 索引 / 所有文章共用 `assets/base.css` + `home.css` / `post.css` + `assets/site.js`，
  页面本身只写结构，不要复制样式进页面。
- **工具页（tga / backlog / about）单文件自包含**：CSS/JS/数据内联在一个 `index.html`，不引 CDN 之外的相对资源。
  静态数据用 `<script type="application/json">` 内嵌，前端 `JSON.parse`。
- 状态存 `localStorage`，key 带版本号（`xxx_v2`），改结构做迁移。
- 必须响应式：手机单列 + PC 两列/三列。
- 配色：低饱和"雾色"比纯色耐看，深底强调色 `#6aa2d8`、浅底 `#2d6496`，对比度 ≥ 4.5:1。

## 中英切换（about 页那套）

`data-i18n` 标记 + 一张 JS 字典，不要复制两份 DOM：

```html
<span data-i18n="hero.1">English</span>
```

```js
var I18N = { "hero.1": {en:"...", zh:"..."} };
function applyLang(l, typed){
  document.documentElement.lang = (l === 'zh' ? 'zh-CN' : 'en');
  document.querySelectorAll('[data-i18n]').forEach(function(el){
    var d = I18N[el.dataset.i18n]; if (!d || !d[l]) return;
    if (el.classList.contains('terminal-type')) el.dataset.typeText = d[l];
    if (typed !== false) el.textContent = d[l];
  });
}
```

- 默认 `en`，选择存 `localStorage.lang`；切换按钮写 **`EN / ZH`**，当前语言用强调色。
- **坑**：`applyLang(lang, lang !== 'en')` 在 en 首次加载时不会写 `textContent`，
  所以非 `terminal-type` 元素的静态 HTML 文案必须直接写成英文最终值，否则切回 EN 会残留旧文案。
- 切换时先 `finish()` 结束打字动画再换文案，否则两种语言交错。

## 打字机动画的两个坑

1. 后台标签页 `setTimeout` 被节流 → 给时间预算：
   `if (Date.now() - started > 4200) return finish();`
2. 兜底定时器与动画循环抢同一节点会重复文本（出现过 `whoamioami`）→
   `finish()` 里加 `done` 标志，每步检查 `if (done) return;`。

## 设计风向参考

做新页面前读（以下 taste skill 仅手机工作站安装，PC 没有；其规则已摘录于本文，PC 按本文执行）：

- `/var/minis/skills/design-taste-frontend/SKILL.md`（taste-skill v2）
- `/var/minis/skills/ui-taste/SKILL.md`（Uizze）

最相关的几条：彩色只上数据（界面彩色占比 ≤3%）；KPI 用排版不用卡片；
表面扁平（1px 线分层，不要阴影卡片墙）；工作型页面标题 ≤24px；
删掉没有 claim 的段落；数据诚实（0 就是 0，缺值给灰破折号）。

## 移动端浮动按钮：别被浏览器工具栏挡住

移动浏览器底部自带工具栏（Chrome / 微信 / 夸克都约 56px 高）。
浮动按钮写成 `position:fixed; bottom:24px` 会正好落在工具栏下面 ——
用户点到的其实是浏览器，表现就是**「按钮点了没反应」**，而 JS 和 CSS
在 DevTools 里查起来一切正常（`el.click()` 手动调用也能工作）。

正确写法：

```css
.toc-fab{
  bottom: calc(24px + env(safe-area-inset-bottom, 0px) + 56px);
}
```

配套的底部面板（`.toc.is-open`）也要抬到 `bottom: calc(84px + … + 56px)`，
否则面板贴底，最后几项看不到。

**排查口径**：用户说「点了没反应」时，先手动 `el.click()`。
- 手动能开 → 是点击区域问题（被遮挡 / z-index / pointer-events），不是逻辑问题
- 手动也不开 → 才去看 JS 绑定（很可能是被绑了多次、toggle 抵消，见 content.md）

## hover 状态在 WebView 里测不出来

`browser_use` 的 `hover` 动作不会触发 CSS `:hover`
（`el.matches(':hover')` 返回 `false`，截图也没变化）。

要验证 hover 效果，直接用 JS 写内联样式模拟：

```js
el.style.background = 'var(--accent)';
el.style.color = '#fff';
```

截图看视觉是否正确，逻辑本身（CSS 规则在不在）用 `document.styleSheets` 遍历确认。

## 目录字体：统一用无衬线，别用等宽

`.toc` 原来继承 `var(--mono)`（JetBrains Mono），中文没有对应字形会 fallback 到系统字体。
结果：**中文文章**的目录是 PingFang，**英文文章**的目录是 JetBrains Mono，
同一站在不同文章里观感完全不一样。

定下来的标准：

```css
.toc{font-family:var(--sans);font-size:.78rem;line-height:1.55}
.toc-list a{
  font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Noto Sans CJK SC",
              "Microsoft YaHei","Helvetica Neue",Arial,sans-serif;
  font-size:.84rem;font-weight:400;line-height:1.5;letter-spacing:0;
}
.toc-head{font-family:var(--sans)}
```

- **字号 0.84rem / 字重 400 / 行高 1.5**，中英文共用一套。
- 等宽字体只留给代码、命令、日期这类"需要对齐"的地方，目录是阅读导航，不该用。
- 目录样式只在 `assets/post.css` 里改；`tools/add_toc.py` 现在只管结构和 JS，不含任何 CSS。

判断标准：打开一篇中文和一篇英文的文章页，目录的字重、行距、字号应该看不出差别。

## 断点：三档，不是两档

```
≤1023px   手机 + 竖屏平板：目录收成右下浮动按钮 → 底部面板
1024–1279 横屏平板：右侧固定目录，正文左移让位
≥1280px   桌面：右侧目录靠右 20px，正文居中
```

**为什么要单独一档**：iPad 横屏是 1024/1180/1366。早先只在 >1180 显示右侧目录，
结果 1024 的 iPad 横屏落到"手机模式"，目录展开是个又宽又矮的底部面板，
20 多个条目挤成一片 —— 用户原话是「横屏 iPad 打开目录展开会很长」。

1024–1279 这一档的写法：

```css
@media (min-width:1024px) and (max-width:1279px){
  .wrap{max-width:680px;margin-left:28px;margin-right:auto}  /* 正文左移让位 */
  .toc{left:auto;right:20px;width:220px}                      /* 目录贴右，不用 50%+偏移 */
}
```

两个坑：
- `.toc{left:calc(50% + 384px)}` 在 1024 宽下会算出 896px 起点 + 238 宽 = 溢出屏幕。
  中等宽度必须改成 `left:auto;right:20px`。
- 只把目录贴右不移正文，会和正文重叠约 90px。正文 `margin-left` 要固定值让位，不能 `margin:0 auto`。

## 目录底部面板的三种宽度

```
≤599px     手机：left:16 right:16，拉满（窄屏没有留白问题）
600–1023   平板竖屏：left:auto right:24 width:420 —— 收成抽屉
1024–1279  横屏平板：右侧固定目录
≥1280      桌面：右侧目录
```

**为什么平板竖屏要单独收窄**：768px 宽的 iPad 竖屏如果用 `left:16 right:16`，
面板宽 736px，但目录文字一行就占满了，右边大片留白，看着像没做完。
收到 420px 靠右，密度才对。

```css
@media (min-width:600px) and (max-width:1023px){
  .toc.is-open{left:auto;right:24px;width:420px;max-width:calc(100vw - 48px);padding:18px 20px}
}
```

**面板里必须保留分级**：`.toc.is-open .toc-list a{padding:9px 0 9px 12px}` 的优先级高于
`.toc-list li.lvl3 a{padding-left:22px}`，会一次性把二级标题拍平到和一级同一行。
所以面板内要单独补：

```css
.toc.is-open .toc-list li.lvl2>a{padding-left:14px;font-size:.92rem}
.toc.is-open .toc-list li.lvl3>a{padding-left:34px;font-size:.84rem;opacity:.82}
```

改完全站验证：412px 和 820px 各开一次面板，2.1 / 2.2 这类三级标题必须缩进且字号更小。

## 首页顶部

**不放「首页」大标题**：它是导航标签、没有 claim，还会把首屏最贵的字号浪费在无信息的内容上
（导航里早已没有「首页」链接，品牌在左上角）。现在是一行 mono 元信息：

```
45 篇 · 最新 10月31日
```

规模 + 新鲜度两个真实信号，和文章页 meta 同一套语言。改文案只动 `tools/gen_index.py` 的 `meta_line`。

## 沉浸阅读（html.readmode）

文章页一个图标按钮（文章头部 `.meta` 行右端，图标-only + aria-label），进入后只剩
**标题 / 正文 / 目录 / 文末版权提示**，其余全部退场。

| 保留 | 退场 |
|---|---|
| H1、正文、目录（PC 横杠 / 手机圆钮）、代码复制、文末版权提示 | 顶栏、日期·作者·字数、来源块、相关阅读、上下篇、返回首页、页脚、回到顶部、阅读位置提示条 |

- 状态存 `localStorage.readmode`，**跨文章、跨刷新保持**；只对文章页生效
- 进入时尝试 `requestFullscreen()`；系统手势退出全屏时同步退出沉浸态（避免“退一半”）
- 退出三个口：右上角图标 / `Esc` / 文末「读完 · 退出沉浸阅读」
- **按钮定位**：`.read-btn` 在两种状态下都是 `position:fixed`（`top:12 right:14`），
  顶栏在沉浸态压成 **0 高**（不是 `display:none`，否则按钮跟着消失）→ 按钮坐标全程不变，也不会留下空带子
- 顶栏压成 0 高会让内容上移，靠 `keepPosition()`（以正文首个标题为锚）补回滚动位置
- 沉浸态隐藏滚动条，PC 目录横杠 `top` 从 88 抬到 32，文章上边距降到 22
- `.bar .nav` 固定留 30px 右内边距，给按钮让位，避免压住主题开关
- 注入在 `add_toc.py` 的 `ensure_readmode()`（幂等），`qa.py` 校验每篇恰好一个 `#readBtn`

**第二层（已做）交互反转**：`html.readmode.no-ui` 下退出按钮 / 目录圆钮 / 目录横杠全隐（`opacity:0` +
`pointer-events:none`）。规则是——

- **一滚动就隐**（跟常规站点相反：滚动表示你在读，不需要控件）
- 轻点空白处（点在 `a/button/input/pre/table` 上不拦截）→ 召回 3 秒
- 桌面端移动鼠标 → 召回 2.6 秒
- 退出沉浸时清掉 `no-ui`，普通态不受影响

未做（刻意）：桌面隐藏光标。体感收益小，误伤大（悬停链接时看不到指针）。
