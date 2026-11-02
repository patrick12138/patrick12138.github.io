# 内容流水线：md → 文章页

vault：手机 `/var/minis/mounts/Patrick's_Obsidian/`，PC `C:/Users/Patrick/Documents/Obsidian Vault`
（写进 PC 的 `tools/config.local.json` 的 `vault_root`，缺省值在 `tools/config.py`）。
文章源是 `Sources/`（搬运）和 `Resources/`（他的浓缩笔记）。

## 一篇新文章（极简两步）

```bash
cd <当前环境的工作副本>     # 手机 /var/minis/workspace/site，PC F:\patrick12138.github.io

# 1) 转换（自动处理 frontmatter / 图片本地化 / 排版，并自动同步登记到 tools/sources.json）
python3 tools/md2post.py "/var/minis/mounts/Patrick's_Obsidian/Sources/Inbox/xxx.md" <slug> \
        [--author "作者"] [--date 2026-01-01] [--title "覆盖标题"] [--kind repost|own]
# PC 上 vault 路径换 "C:/Users/Patrick/Documents/Obsidian Vault/Sources/Inbox/xxx.md"，python3 换 python，flag 写法相同

# 2) 一键构建与上线（自动注入目录、统计字数、生成首页、打资源戳、排版体检、推送）
python3 tools/build.py --push "feat: 新文章 xxx"
```

注：首页**不需要且不要手动改** `index.html`，`build.py` 会自动调用 `tools/gen_index.py` 重新全自动生成。

`build.py --push` 这一条里已经包含：目录注入 → **搬运页版权信号**（`gen_legal`）→ 字数 → 首页 →
上下篇 → **相关阅读** → **两份搜索索引**（`search.js` + `search-deep.js`）→ RSS/sitemap →
回归测试 → 资源版本戳 → skill 一致性 → 排版体检（含脱敏）→ 推送。顺序以 `tools/build.py` 的 docstring 为准。

**发布后 30 秒自查**（三次里有一次会撞上 Pages 缓存）：

```bash
sleep 45
curl -s -o /dev/null -w '%{http_code}\n' https://patrick12138.github.io/posts/<slug>/
curl -s https://patrick12138.github.io/ | grep -c '<slug>/'          # 首页要有
curl -s https://patrick12138.github.io/search.js | grep -c '<slug>'  # 搜索索引要有
```

md 必须来自 vault（`Sources/Inbox` / `Sources/Clippings`），**不要用 `/tmp` 里的临时文件**——
`sources.json` 里记的是 md 路径，绝对路径换台机器就失效。

`--kind own` 进「个人」tab，`repost` 进「搬运」tab。**笔记和文章放同一个目录、同一个列表**——
2026-11-02 开过独立的 `/notes/` 板块，用户明确否掉：只要一个列表，不要两个入口。

## 常用命令

```bash
python3 tools/rebuild.py              # 全部重建（按 sources.json，图片有 webp 就复用）
python3 tools/rebuild.py slug1 slug2  # 只重建指定文章
python3 tools/add_toc.py              # 只重灌目录
python3 tools/qa.py                   # 排版体检（含脱敏检查）
python3 tools/check_skills.py         # skill 文档与代码是否还对得上
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

一个脚本管三件事：右侧目录（含锚点 id）、站名下拉、右上角导航对齐（Lab / About）。
**它不再管**：CSS（在 `assets/post.css`）、`?v=` 哈希（`build.py` 的 `stamp_assets()`）、
文末「↑ 回到顶部」（已取消，只保留右下浮动按钮，脚本在 `assets/site.js`）。

**三条铁规（都是踩过坑的）**

1. **幂等**：改 HTML 一律「先全量剥离、再注入一次」。剥离按签名扫（`brandSet` / `toTop` / `var toc=`），
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

首页每条的 `.desc` 要 `-webkit-line-clamp:2`。不截断的话，150 字的描述会折成 6 行，
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

## 字数与阅读时间（自动）

`tools/stats.py` 会扫描每篇文章，把 `N 字 · 约 M 分钟` 写进 `<div class="meta">`：

- 中文按 400 字/分钟，英文按 230 词/分钟，取整到分钟
- 幂等：先剥掉旧的 `<span class="stats">`，再写入，跑多少遍都不会重复
- 首页列表的时间行由 `gen_index.py` 从文章页抓同一段文字，两处永远一致
- `build.py` 第 ③ 步执行，不用手动跑


## 正文边界（tools/postbody.py）

`.body` 之后挂着四个尾巴容器，都**不算正文**：`nav.related`（相关阅读）、`nav.pager`（上下篇）、
`aside.legal-note`（版权提示）、`a.back`（返回首页）。

它们由不同步骤**后插**（②.5 / ④.2 / ④.25），所以任何「截到第一个 `</div>`」或「截到 `<a class=back>`」
的写法都会随注入顺序漂移。历史上因此出过三次事故：字数虚高、搜索能搜到「版权/相关阅读」、
版权提示每次 build 前后跳。

现在只有一处实现，谁要正文都从这里取：

```python
import postbody
postbody.body_html(doc)    # 正文 HTML 片段
postbody.body_text(doc)    # 正文纯文本（去标签、压空白）
postbody.body_span(doc)    # (start, end)，需要原地替换时用
postbody.tail_start(doc)   # 尾巴区起点，往这之前插新块
postbody.table_rows(tbl)   # 表格 → 行×单元格，wrap 与 qa 共用
```

**加一个新的文末区块时**：把它加进 `postbody.TAIL_MARKERS`，别在各自的脚本里再写截断标记。

## 搬运页版权信号（tools/gen_legal.py）

全文搬运 + 署名 + 原文链接 **不等于** 授权：署名只解决署名权，复制权/信息网络传播权那一项还在。
`gen_legal.py` 干三件事，只针对 `meta` 里带「搬运」的页面：

1. `<link rel="canonical" href="原文">` —— 技术上声明正本在原文那边；
2. `<meta name="robots" content="noindex,follow">` —— 搬运页不和原文抢搜索位
   （`sitemap.xml` 里同时剔除，否则自相矛盾；`feed.xml` 保留，那是给订阅者的）；
3. 文末 `.legal-note` —— 版权归属 + 删除通道（联系方式是脚本头的 `CONTACT`，与 about 页一致）。

原创页会被**剥干净**：把一篇从 `repost` 改成 `own` 后跑一遍 build 就自动收敛。
同样幂等（按 `data-legal` 签名先剥再注），`test_pipeline.py` 有对应用例。
真要彻底降风险，仍然只有两条路：**拿许可**，或**不复制全文**。

## 构建顺序（tools/build.py）

```
① (可选) rebuild.py   从 vault 重建全部文章（会改正文，慎用）
② add_toc.py          目录 / 站名下拉 / 回到顶部 / 去重
②.5 gen_legal.py      搬运页版权信号（canonical / noindex / 文末提示）
③ stats.py            字数与阅读时间
④ gen_index.py        生成首页（唯一文章列表）
④.2 gen_prevnext.py   文末「上一篇 / 下一篇」（全局按发布时间）
④.25 gen_related.py   文末「相关阅读」（tf-idf 共词，自动挑 3 篇）
④.3 gen_search.py     search.js（首页搜索索引，点开才加载）
④.5 gen_feed.py       feed.xml + sitemap.xml + robots.txt
⑤ test_pipeline.py    幂等回归测试
⑥ stamp_assets()      base/home/post.css + site.js 内容哈希
⑥.5 sync_skills()     仓库 skills/ → /var/minis/skills/（PC/CI 无该目录时自动跳过）
⑥.8 check_skills.py   skill 与代码一致性（脚本登记 / 引用 / 参数）
⑦ qa.py               排版 / 分类 / 重复注入 / hash / 外壳 / 摘要质量
```

**上一篇/下一篇不跟首页分类走**：tab 只是筛选视图，不是栏目；跟分类就得在链接上带 `?from=`。

## 文档与代码的一致性（check_skills.py）

`build.py` 第 ⑥.8 步会自动跑，四个结论都是硬失败：

| 检查 | 失败含义 |
|---|---|
| 脚本都登记过 | 新加了 `tools/xxx.py` 但 SKILL / AGENTS 里一次都没提 |
| 引用都存在 | 文档写了 `references/<slug>.md`，但文件不存在 |
| 参数都属实 | 文档写了 `md2post.py --<flag>`，源码里没这个参数 |
| 副本同步 | `/var/minis/skills/` 与仓库 `skills/` 内容不同（sync_skills 没跑或手改了副本；本机无该目录则跳过） |

另外 SKILL.md 硬上限 **100 行**，超了必须把细节挪进 `references/`。
改完 skill 不要手改 `/var/minis/skills/` —— 那是构建产物的下游，`build.py` 会单向覆盖（本机没有该目录时整步跳过）。

## 表格怎么转（2026-11 定）

md 表格 → `<div class="tablewrap"><table>` 两层，**不要手写 HTML 表格**，构建会统一包。

**为什么要有外层容器**：`table` 自己当滚动容器（`display:block;overflow-x`）时，宽度会被内容撑开，
它就不再溢出自己，手机上怎么拖都拖不动。挪动表格那行 CSS 之前先想清楚这点。

渲染规则（`assets/base.css`，一般不用碰）：

| 项 | 行为 |
|---|---|
| 列宽 | 桌面 `table-layout:fixed` 均分；手机按内容宽度 + 横滑 |
| 数字列 | 构建时自动识别（≥60% 单元格是数字/货币/百分比），加 `n2`/`n3` 类右对齐 + `tabular-nums` |
| 表头 | mono、0.76em、淡色、下压一条更实的线 |
| 边界 | 首列去左内边距、末列去右内边距，表格左右与正文严丝合缝 |
| 分隔线 | 只留极淡的横线，最后一行不画 |

**写表格时的四条硬约束**（`qa.py` 的 `check_tables()` 会拦）：

1. **列数 ≤ 6**，超过就拆两张表或改成列表（手机横滑超过 6 列基本没法读）
2. **单元格 ≤ 90 字**，长句放正文，表里只放短语
3. **必须有表头**（md 表格第一行），否则 P2
4. 单元格里不要塞 `<br>` 或用空行凑排版

**别做的事**：不要给单元格加 `text-align`（构建时按数字自动判）、不要在 md 里写 `<table>`。

## 首页搜索（gen_search.py）

首页列表只有标题和摘要，很多词只出现在正文里（`worktree`、`缓存命中率`）。所以构建期压一份索引：

```bash
python3 tools/gen_search.py     # 生成 search.js（45 篇约 154KB，gzip 后 ~50KB）
```

- **两份索引**：`search.js`（标题/摘要/小标题/正文前 1500 字，约 175KB，点开搜索立即到）+
  `search-deep.js`（每篇 1500 字之后的剩余正文，约 600KB，后台静默加载，到了自动重跑当前查询）
  这样做是因为全文索引 gzip 后仍有 330KB：首发就加载会让第一次搜索等一两秒
- 前端**只在点开搜索时才 fetch**，不拖慢首屏
- 打分：标题命中 5、标题开头额外 +3、小标题 3、摘要 2、正文 1
- 命中正文时显示片段 + 高亮，搜索词同步到 `?q=`（可分享、可刷新）
- `/` 直接开搜，`Esc` 退出

改索引字段时注意：`tools/gen_index.py` 里的 `score()` 和 `mark()` 依赖 `s/t/d/h/b` 这几个键名。

## 相关阅读（gen_related.py）

不做标签体系——45 篇的量，自动共词比人工归类省事，也不会因为漏打标签失效。

```bash
python3 tools/gen_related.py      # 插到 <nav class="pager"> 之前，幂等
```

- 词源：标题（权重 3）、小标题（2）、摘要（1）、正文前 1200 字（1）
- 中文按 2 字滑窗切，英文按单词；出现率 >45% 的词当停用词丢掉
- 相似度用 **tf-idf 余弦**：不 IDF 加权的话「Codex」这种高频词会把所有文章连成一坨
- 每篇最多 3 条，分数低于 0.06 就不显示（宁缺毋滥）
- 调参在这几个常量：`MAX_RELATED`、`MIN_SCORE`、`DF_CAP`

## 日期解析（tools/dates.py）

站点上的日期有四种写法（ISO / `October 30, 2025` / `2026年10月31日` / `7月21日`），以前
`gen_index`、`gen_feed`、`rebuild`、`md2post` 各写一份，能力还不一样（有的不认「7月21日」）。

现在只此一份：

```python
import dates
dates.to_date("7月21日")        # date，当年
dates.to_iso("October 30, 2025")  # "2025-10-30"，认不出来原样返回
dates.to_cn(d)                 # "2026年10月31日"
dates.short_cn(d)              # "10月31日"，非当年补年份
```

加新格式只改 `dates.py` 的正则表。
