# 内容流水线：md → 文章页

vault 在 `/var/minis/mounts/Patrick's_Obsidian/`，文章源是 `Sources/`（搬运）和 `Resources/`（他的浓缩笔记）。

## 一篇新文章（三步）

```bash
cd /var/minis/workspace/site

# 1) 转换（自动处理 frontmatter / 图片 / 排版）
python3 tools/md2post.py "/var/minis/mounts/Patrick's_Obsidian/Sources/Inbox/xxx.md" <slug> \
        [--author "作者"] [--date 2026-01-01] [--title "覆盖标题"] [--kind repost|own]

# 2) 把这条记进 tools/sources.json（slug / md 相对路径 / author / date / kind / title）
#    这样 rebuild.py 才能整站重生成

# 3) 首页 index.html 的 <ul class="posts"> 按日期倒序插一条
#    <li data-kind="repost|own"><a href="posts/<slug>/"><h2>标题</h2><p class="desc">描述</p><time>Month D, YYYY · 作者 · 搬运</time></a></li>
```

`--kind own` 进「个人」tab，`repost` 进「搬运」tab。**笔记和文章放同一个目录、同一个列表**——
2026-11-02 开过独立的 `/notes/` 板块，用户明确否掉：只要一个列表，不要两个入口。

## 常用命令

```bash
python3 tools/rebuild.py              # 全部重建（按 sources.json，图片有 webp 就复用）
python3 tools/rebuild.py slug1 slug2  # 只重建指定文章
python3 tools/add_toc.py              # 只重灌目录
python3 tools/qa.py                   # 排版体检
python3 tools/qa.py posts/xxx/index.html
```

依赖：`apk add py3-yaml py3-markdown py3-pillow`。

## 排版质检（硬性）与已知历史坑

P0 必须为 0，P1 尽量清完，P2 多为原文 OCR 带进来的空格，可以放过：

| 级别 | 查什么 |
|---|---|
| P0 | 残留 `## 标题`、`**粗体**`、`[[wikilink]]`、`[文字](相对链接)`、`\-` `\`` 转义 |
| P1 | `<br> - 列表` 假列表、空段落、零宽字符、重复转义实体 |
| P2 | 段落内硬换行、中文标点前多余空格、中文之间多余空格 |

这些坑 `md2post.normalize_md()` + 收尾正则已经处理，**别绕过它手写 HTML**：

- 标题/列表前补空行；`…setup)### 标题` 这种剪藏粘连会被切开
- `\``、`\*`、`\[` 反转义回正常字符
- 正文 `[[双链]]` 一律转纯文字（来源块里的列表也一样）
- 中文句中 `<br>` 合并成空格；英文列表项里的 `<br>` 保留
- 空段落、中文标点前空格、源码多余空行清掉
- 图片下载后压成 webp（宽≤1400、q82），已存在则复用不重复下载

`tools/qa.py` 检查时会自动跳过 `<pre>` / `<code>` 和标签属性值，避免把代码当排版问题。

## 文章页后处理（tools/add_toc.py）

一个脚本管四件事：右侧目录、文末「↑ 回到顶部」、站名下拉、`post.css?v=` 内容哈希。

**三条铁规（都是踩过坑的）**

1. **幂等**：改 HTML 一律「先全量剥离、再注入一次」。剥离按签名扫（`brandSet` / `backTop` / `var toc=`），
   用 `re.sub` 清掉**所有**副本而不是只删第一份。早期只删一份 → 每跑一次多堆一个脚本 →
   同一事件绑 3 次 → 单击被 toggle 两次抵消，表现是「点了没反应」。
2. **注入后自检**：连跑两遍，`rg -c "getElementById('brandSet')"` 必须等于 **1**，
   `rg -c '<script></script>'` 必须等于 **0**。数字不对就是剥离漏了。
3. **样式外置 + 内容哈希**：文章页 CSS 在共享 `assets/post.css`，页面里只有 `<link ...?v=hash>`。
   哈希只有**一个写入者**：`tools/build.py` 的 `stamp_assets()`（覆盖 home.css / post.css / site.js）。
   改完 CSS **必须跑 `build.py`**（`add_toc.py` 不再负责打戳，跑它不会更新版本号）。
   hash 不跟着文件变 = URL 不变 = 浏览器一直吃旧缓存，症状是「有的页面刷新后才生效」。
   `qa.py` 已加检查：任何页面 `?v=` 不等于真实文件 hash 就报 P0。
   **内联 `<style>` 的路子已经废了**（页面里没有 `<style>`），往 `<style>` 里 replace 是静默失效。

**重建而非跳过**：`if 已存在: return` 这种写法会让样式改了刷不进旧页面。
正确做法是剥回朴素结构（如普通 `<a class="brand">`），再按当前内容重新生成。

站名下拉的样式与交互见 `design.md`「站名下拉」。

## 从网页 / 剪藏转文章：三个必查项

这三条都是「页面能打开、但看起来不对劲」的隐性问题，`qa.py` 目前查不出来，得人眼过：

**1. 装饰性空 SVG**

原文（尤其是带花体标题的博客）常有这种：

```html
<svg height="200"><path id="x"></path><textPath href="#x">君子生非異也…</textPath></svg>
```

`<path>` 没有 `d` 属性，文字渲染不出来，但 SVG 仍然占 **200px 高**。
转换后表现为文章开头或段落之间凭空一大块空白。

清理方式：删掉同时满足「含空 `<path id>`」和「含 `<textPath>`」的整个 `<svg>`，
删完再 `re.sub(r'<p[^>]*>\s*</p>', '')` 清一遍空段落。

**2. 列表摘要必须截断**

首页每条的 `.desc` 要 `-webkit-line-clamp:3`。不截断的话，150 字的描述会折成 6 行，
把这条撑到别的条目的 1.5 倍高，看起来像「下面空了一大截」（实际是别人矮）。
排查方法：`[...document.querySelectorAll('#posts li')].map(li=>li.getBoundingClientRect().height)`，
高度方差过大就是它。

**3. 来源要给完整 URL + 作者**

只写域名（`tw93.fun`）读者没法核对原文。用 `<aside class="source">` 放完整链接，
meta 行给作者名，格式 `October 23, 2026 · Tw93 · 搬运`。

## 重复注入：这次是元素叠了 10 个

同源的坑，比脚本重复更隐蔽：

`add_toc.py` 的 `strip_toc()` 里剥离正则写的是
`aria-label="Contents"`（英文），但生成的时候写的是 `aria-label="目录"`（中文）。
**剥不掉 → 每跑一次多一个按钮 → 攒到 10 个叠在同一位置。**

症状极像「按钮坏了」：`el.click()` 手动调用能开，手指点就是没反应。
因为 `getElementById` 拿到的是第一个（有事件），而点击命中的是最上层那个（没事件）。

排查一条命令：

```js
document.querySelectorAll('.toc-fab').length   // >1 就是重复
document.elementFromPoint(x, y) === document.getElementById('tocFab')  // false 就说明点歪了
```

修法两条都要做：

1. **剥离正则不要绑定生成时的文案**，用 `<button class="toc-fab"[^>]*>.*?</button>`，
   不要写 `aria-label="Contents"` 这种实现细节。
2. **跑完复核计数**：`python3 tools/add_toc.py` 连跑两遍，第二遍后
   `rg -c 'class="toc-fab"' posts/*/index.html` 每个文件必须是 1。

顺带一条：浮动按钮里的 `<svg>` 加 `pointer-events:none`，
让命中目标永远是 `<button>`，少一层不确定性。
