---
name: github-pages-deploy
description: Deploy a self-contained HTML/JS page to Patrick's GitHub Pages site and hand back a URL. Use whenever the user says 上线, 部署, 推到远程, 想要个链接, 手机上打不开/pc 也能打开, or asks to publish a generated HTML tool or page. Also covers the bilingual (English-first) README convention for every repo, the single-site-repo layout, credential quirks, and post-deploy verification.
version: 2.0.0
---

# GitHub Pages 部署

把本地做好的静态页面推上线，返回可访问 URL。也管仓库 README 的双语规范。

## 铁律：只有一个站点仓库

**站点根仓库：`patrick12138/patrick12138.github.io`**（分支 `main`，Pages 源 `/`）

```
patrick12138.github.io/
├── index.html          # 入口页，列出所有工具
├── about/index.html    # 终端风个人页（复刻 stevibe.ai）
├── tga/index.html      # TGA 待玩清单
├── .nojekyll
├── README.md           # 英文（仓库首页显示）
└── README.zh-CN.md     # 中文
```

- URL 形态：`https://patrick12138.github.io/<子目录>/`
- **不要为单个页面新建仓库。** 以前误建过 `tga-checklist`，已迁走留了跳转页。
- 新增工具 = 加一个子目录 + 在根 `index.html` 的 `.list` 加一条 + push。

## 凭据

- PAT 在 shell 环境变量 **`$GITHUB_TOKEN`**（classic，带 `repo` scope）。
  **不是 `GITHUB_PAT`** —— 那个在 shell 里不存在，拿去调 GitHub MCP 会报
  `Illegal header value b'Bearer '`。
- 永远不要 echo / print token 值。
- push 认证：`http.extraheader` 会失败（invalid credentials），必须用 URL 内嵌：

```bash
git remote set-url origin "https://x-access-token:$GITHUB_TOKEN@github.com/<owner>/<repo>.git"
git push -u origin main
git remote set-url origin https://github.com/<owner>/<repo>.git   # 推完立刻还原
```

- **这个 token 没有 `delete_repo`**。删仓库会返回
  `403 Must have admin rights`，直接告诉用户去
  `https://github.com/<owner>/<repo>/settings` 底部 Danger Zone 自己删，别反复试。

## 网络不通时（DNS 抽风）

沙盒偶尔整个 DNS 挂掉：`Could not resolve host: github.com`，连 baidu 都 000，
但 `curl --resolve` 硬指 IP 能通。这时往 `/etc/hosts` 写死：

```bash
echo "140.82.113.4 github.com"      >> /etc/hosts
echo "140.82.113.5 api.github.com"  >> /etc/hosts
echo "185.199.108.153 patrick12138.github.io" >> /etc/hosts
```

先 `getent hosts github.com` 确认解析，再继续。恢复后这些行留着无害。

## 文章页与笔记页：用 scripts/md2post.py 从 vault md 生成

搬运/原创都不手写 HTML，走转换器。skill 里存了正本
`/var/minis/skills/github-pages-deploy/scripts/md2post.py`，仓库里也放了一份 `tools/md2post.py`：

```bash
cd /var/minis/workspace/site
# 搬运文章（md 有 frontmatter：title/source/author/published/description）
python3 tools/md2post.py "/var/minis/mounts/Patrick's_Obsidian/Sources/Inbox/xxx.md" <slug> \
        [--author "作者"] [--date 2026-01-01]
# 自己的浓缩笔记（Resources/*.md，无 frontmatter，标题取第一个 H1，“来源：”那段自动抽出来）
python3 tools/md2post.py "/var/minis/mounts/Patrick's_Obsidian/Resources/xxx.md" <slug> \
        --kind own --date 2026-06-24
```

- **笔记和文章同一个目录**：都生成到 `posts/<slug>/`，首页一个列表按日期倒序，
  `--kind own` 的进「个人」tab，`repost` 进「搬运」tab。**不要再开 /notes/ 这种独立板块**
  （2026-11-02 开过又拆了：用户要的是一个列表，不是两个入口）。

- 模板从 `posts/git-worktree/index.html` 现切，样式永远和旧文章一致。
- 图片自动下载到 `assets/posts/<slug>/` 并压成 webp（最大宽 1400、q82），9MB → 1.4MB 量级。
- 自动去掉重复标题、`[See all posts]`、空的「目录」、`来源：` 列表里的 wiki 括号。
- 生成完记得在首页 `index.html` 的 `<ul class="posts">` 里按日期倒序插一条
  `<li data-kind="repost|own">`，`data-kind` 决定「搬运 / 个人」筛选 tab。
- 依赖：`apk add py3-yaml py3-markdown py3-pillow`。

### 站点目录（2026-11 现状）

```
index.html                 首页 = 唯一列表（全部 / 搬运 / 个人 三个 tab）
about/  lab/  tga/         个人页 / 玩具 / TGA 清单
posts/<slug>/index.html    所有长文与笔记，一篇一个目录
assets/posts/<slug>/       配图（webp）
```

## 目录（右侧跳转栏）

文章页的目录由 `tools/add_toc.py`（skill 正本 `scripts/add_toc.py`）注入，**可重复执行**（先剥旧的再重算）：

```bash
python3 tools/add_toc.py                      # 处理全部 posts/*/index.html
python3 tools/add_toc.py posts/xxx/index.html # 只处理一页
```

- 给正文 h2/h3 自动加 id，生成 `<nav class="toc">` + CSS + JS，标题少于 3 个的页面自动跳过。
- **PC（>1180px）**：固定在正文右侧 `left:calc(50% + 392px)`，宽 196px，跟随滚动高亮当前节；
  点「目录 ⌄」折叠 → 只剩右边缘的竖排「目录」小标签，状态存 `localStorage.tocCollapsed`。
- **手机（≤1180px）**：右下浮动「目录」按钮，点开是底部面板（模糊底 + 最大 60vh + × 关闭），
  点条目跳转后自动收起。
- **坑**：`scrollIntoView({behavior:'smooth'})` 在部分 WebView（含 Minis 内置浏览器）里是空操作，
  必须用 `window.scrollTo({behavior:'smooth'})` + 400ms 后位置没动就硬跳一次兜底；
  后台标签页的 `requestAnimationFrame` 会被暂停，所以**不要**用 rAF 做滚动动画。
- 滚到锚点时用 `scroll-margin-top:84px` 避开顶部 52px 的 sticky bar。

## 标准流程（新增一个页面）
```bash
# 1. 本地源在工作区，例如 /var/minis/workspace/tga/index.html
#    站点仓库工作副本固定在 /var/minis/workspace/site/
mkdir -p /var/minis/workspace/site/<slug>
cp <源>/index.html /var/minis/workspace/site/<slug>/index.html

# 2. 在 /var/minis/workspace/site/index.html 的 .list 里加一条

# 3. 提交推送
cd /var/minis/workspace/site
git add -A && git commit -m "feat: <slug>"
git remote set-url origin "https://x-access-token:$GITHUB_TOKEN@github.com/patrick12138/patrick12138.github.io.git"
git push origin main
git remote set-url origin https://github.com/patrick12138/patrick12138.github.io.git
```

**等 30–60 秒**（Pages legacy 构建是异步的）再验证：

```bash
curl -s -L "https://patrick12138.github.io/<slug>/?v=2" -o /tmp/live.html \
  -w "%{http_code} %{size_download}\n" --max-time 25
rg -o '<title>[^<]*</title>' /tmp/live.html
rg -c '<本次新增的某个字符串>'   # 确认新代码真的生效
```

- 200 + 标题对 = 上线。
- 刚 push 完立刻 curl 大概率拿旧内容。**必须 grep 本次新增的字符串**，
  只看 200 会被缓存骗。
- 已经上线但浏览器还是旧的：加 `?v=N` 强制刷新。

## 首次建站（已完成，仅备查）

```bash
curl -s -X POST -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/user/repos \
  -d '{"name":"patrick12138.github.io","private":false}'

# *.github.io 仓库通常自动开 Pages，先 GET 看 status，404 才 POST
curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/repos/patrick12138/patrick12138.github.io/pages
# POST body: {"source":{"branch":"main","path":"/"}}
```

## README：中英双语，英文优先

Patrick 所有仓库都这样，照抄：

```markdown
# Project Name

[English](./README.md) | [简体中文](./README.zh-CN.md)

One sentence on what it is and who it's for.

## Features        ← 或 Pages / How it behaves
- bullet，一句话一条

## Tech Stack      ← 可选
## Requirements    ← 运行环境 / SDK 版本
## Build / Run     ← 命令块
## Project Structure
## Known limitations
## License
```

- **文件名固定**：`README.md`（英文，仓库首页显示的就是它）+ `README.zh-CN.md`（中文）。
- 标题下第一行必须是语言切换：英文文件写
  `[English](./README.md) | [简体中文](./README.zh-CN.md)`；
  中文文件写 `[English](./README.md) | 简体中文`。
- **英文在前、为主**。中文版不逐字硬译，语气自然些，技术细节一条都不能少
  （表格、参数、命令、路径、issue 链接全保留）。
- 章节标题用英文（`## Features`、`## Build`）；命令、路径、字段名、代码不翻译。
- 中英两版的结构必须对称，方便对照维护。
- 改已有仓库的 README 时：`git show HEAD:README.md` 拿原版 → 存成 `README.zh-CN.md` →
  再写英文版覆盖 `README.md`。**顺序别反**，否则会把英文写进中文文件。
- 已按此规范改过：`patrick12138.github.io`、`telegram-toggle`。

## 设计：先读这两个 skill

做新页面之前读：

- `/var/minis/skills/design-taste-frontend/SKILL.md`（taste-skill v2，配 `references/`）
- `/var/minis/skills/ui-taste/SKILL.md`（Uizze，配 `reference/`）

最相关的几条（都在实测里踩过）：

- **颜色只上数据，不上装饰**：界面彩色像素占比 3%，超过 5% 就花。
- **KPI 用排版，不用卡片**：不要彩色圆图标 + 火花线。
- **表面扁平**：1px 线或一个色阶分层，不要阴影和悬浮卡片墙。
- **不要 hero 大标题**：工作型页面标题最多 24px。
- **删掉没有 claim 的段落**：每段都要给信息，不要“这是我自己用的小工具”这种自我说明。
- 数据诚实：0 就是 0，缺值给灰破折号。
- 选色算对比度：深底上强调色 ≥ 4.5:1，浅底同理。低饱和的“雾色”比纯色耐看
  （蓝：深色 `#6aa2d8` / 浅色 `#2d6496`）。

## 页面写法要求

- **单文件自包含**：CSS、JS、数据全内联在一个 `index.html`。不引 CDN，不用相对路径拉本地资源。
- 数据用 `<script type="application/json">` 内嵌，前端 `JSON.parse`。
- 状态存 `localStorage`，key 带版本号（`xxx_v2`），改结构时做迁移。
- 必须响应式：手机单列 + PC 两列/三列。

### 中英切换（about 页那套）

用 `data-i18n` 标记 + 一张 JS 字典，不要复制两份 DOM：

```html
<span data-i18n="hero.1" data-type-text="...">English</span>
<p data-i18n="about">English</p>
```

```js
var I18N = { "hero.1": {en:"...", zh:"..."}, ... };
function applyLang(l, typed){
  document.documentElement.lang = (l === 'zh' ? 'zh-CN' : 'en');
  document.querySelectorAll('[data-i18n]').forEach(function(el){
    var d = I18N[el.dataset.i18n]; if (!d || !d[l]) return;
    if (el.classList.contains('terminal-type')) el.dataset.typeText = d[l];
    if (typed !== false) el.textContent = d[l];
  });
}
```

- 默认 `en`，选择存 `localStorage.lang`。
- 切换按钮写 **`EN / ZH`**（英文页里不出现汉字），当前语言用强调色，另一个灰。
- 切换时先结束打字动画再换文案，否则两种语言会交错。
- 命令本身（`whoami`、`cat x.txt`）不翻译。

### 打字机动画的两个坑

1. **后台标签页的 `setTimeout` 会被节流**，动画可能几分钟走不完。
   必须给时间预算：`if (Date.now() - started > 4200) return finish();`
2. **兜底定时器会和动画循环抢同一个节点**，导致文本重复（出现过 `whoamioami`）。
   `finish()` 里加 `done` 标志，动画每步检查 `if (done) return;`。

## 本地先验收，再上线

```bash
browser_use navigate minis://workspace/site/<slug>/index.html
browser_use screenshot                      # 手机尺寸
browser_use set_viewport 1180x760           # PC 尺寸（不要用 1440×900）
browser_use screenshot
```

`minis://` 下绝对路径 `/xxx` 会解析到 minis 根目录，所以页面内不要写根路径引用。

## 已知坑

| 现象 | 原因 / 解法 |
|---|---|
| `invalid credentials` | 用了 `http.extraheader`，改用 x-access-token URL |
| `Could not resolve host` | 沙盒 DNS 挂了，往 `/etc/hosts` 写死 IP（见上） |
| 线上还是旧内容 | Pages 未构建完（等 30–60s）或浏览器缓存（加 `?v=N`） |
| 截图全白 | 1440×900 这类大视口会返回白图，换 1180×760 |
| 文字重复 `whoamioami` | 兜底 finish 与动画循环竞争，加 `done` 标志 |
| 动画在后台不动 | setTimeout 被节流，加时间预算直接铺完整文本 |
| 手机端英文名被截断 | 状态按钮太占宽；窄屏只留第一个平台徽章 |
| 子路径 404 | 目录里必须有 `index.html`；`/tga` 会 301 到 `/tga/`，属正常 |
| 删除仓库 403 | token 无 `delete_repo`，让用户自己在 Settings 底部 Danger Zone 删 |

## 交付话术

上线后给一行可点的链接 + 本次改了什么 + 一句数据存在哪（localStorage / 无后端）。
不要把部署过程展开讲；网络或权限问题才需要单独说明。
