# AGENTS.md

给接手这个仓库的 agent（和未来的自己）的入口。细节在 `skills/github-pages-deploy/`，别往这里堆。

## 0. 开工前

```bash
python3 tools/preflight.py      # 要看到 clean
```

工作副本两处：手机 `/var/minis/workspace/site`、PC `F:\patrick12138.github.io`，别建第三份。
这个仓库经常被另一个会话并发提交，落后就先 `git rebase origin/main`。
回复用户时明确说「本地 = 远端 @ `<commit>`」。

## 1. 这是什么

纯静态站（GitHub Pages，`main` 分支，源 `/`）。没有服务端、没有构建服务器：所有 HTML 都是本地生成后提交的产物，Pages 只是把文件原样发出去。

## 2. 目录

```
index.html / posts/<slug>/   生成物，别手改
assets/                      base|home|post.css + site|home|post.js
tools/                       生成器与质检脚本（清单见 SKILL.md）
skills/                      skill 单一源，build 时同步到 /var/minis/skills
about/ lab/ tga/ backlog/    单页
```

## 3. 一条命令

```bash
python3 tools/build.py                     # 构建 + 测试 + qa，green 才算过
python3 tools/build.py --rebuild           # 先从 vault 的 md 重建正文（会改正文，慎用）
python3 tools/build.py --push "feat: xxx"  # green 后自动 commit + push
```

PC（Windows）首次：`python -m pip install pyyaml markdown pillow`；之后用 `python tools/build.py`（内部子进程已用 `sys.executable`）。

## 4. 要改什么，先查这张表

| 想改的东西 | 改这里 |
|---|---|
| 加文章 | vault 里的 md → `tools/sources.json` → `build.py` |
| **新增/改名脚本** | 放进 `tools/` 并在 skill 或本文档里提一句，否则 `check_skills.py` 会让构建失败 |
| **改 skill 文档** | 改仓库 `skills/` 里的，`build.py` 自动同步到 `/var/minis/skills/`（PC/CI 无该目录时自动跳过）；`SKILL.md` 不超过 100 行 |
| **脱敏** | vault 里的 md 改词（公司名换代号）→ `md2post` 重生成 → `qa.py` 复查 |
| **下线文章** | `tools/unpublish.py <slug>`（git rm + 移出 sources.json + 重生成列表/feed） |
| 文章正文排版 | `assets/post.css` |
| 首页列表/分类/搜索 | `tools/gen_index.py`（**不是** `index.html`） |
| 导航条（Lab / About） | `tools/gen_index.py` + `tools/post_template.html` + `lab/index.html`（三处） |
| 右侧目录 / 站名下拉 | `tools/add_toc.py` + `assets/post.css` |
| **搬运页版权**（canonical / noindex / 文末提示） | `tools/gen_legal.py`（联系方式在文件头 `CONTACT`）+ `assets/base.css` 的 `.legal-note` |
| 主题切换、回到顶部 | `assets/site.js` + 对应 CSS |
| 部署、凭据、DNS 排障 | `skills/github-pages-deploy/references/deploy.md` |

## 5. 硬规矩（其余见 SKILL.md）

1. **生成物不手改**：`index.html`、`posts/**` 改了也会被下次 build 覆盖。
2. **push 前必须 green**；P0 不为 0 不上线。
3. **上线前必过脱敏**：前公司/客户名、证件、手机号、内网地址、密钥 → P0（`qa.check_privacy()` 自动拦）；求职痕迹、薪资 → P1。改 vault 里的 md，不要只改 HTML。
4. **后处理脚本必须幂等**：跑两遍字节一致、注入标记各只有 1 份。

## 6. 三个高频坑

| 现象 | 原因 / 解法 |
|---|---|
| 改了 CSS 但线上没变 | `post.css?v=` 是内容哈希，必须跑 `build.py` 重写（qa 会拦） |
| 按钮/目录文字叠在一起 | 后处理重复注入；剥离要按签名全量清，跑两遍 `rg -c` 必须 = 1 |
| 在 minis:// 里测 `replaceState` 报 SecurityError | 本地预览的限制，线上 https 才生效 |

其余 10 条（含"看着像出错其实正常"的）见 `references/pitfalls.md`，撞到怪事先查它。

## 7. 算不算做完

green → push → 等 30–60s → `curl` 线上并 **grep 本次新增的字符串**（只看 200 会被缓存骗）。

> 觉得上下文变臃肿、或模型升级后想重新瘦身 → 读 `docs/context-diet.md`。
