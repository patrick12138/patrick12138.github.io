# AGENTS.md

给接手这个仓库的 agent（和未来的自己）的入口。**这里只放三件事：怎么开工、改哪儿、踩过什么坑。**
细节在 `skills/github-pages-deploy/`，不要往这个文件里堆。

## 0. 每次动手前先对表

```bash
# 手机：/var/minis/workspace/site    PC：F:\patrick12138.github.io（cd 到当前那份，以下相对它跑）
git remote -v                                   # 必须是 patrick12138/patrick12138.github.io
git fetch origin && git rev-list --left-right --count HEAD...origin/main   # 必须是 0 0
git status --porcelain                          # 干净才开工
```

- 工作副本就两处（手机、PC），别建第三份；两边都推 main，动手前必须 fetch 对表。
- 这个仓库经常被另一个会话并发提交，落后就先 `git rebase origin/main`。
- 回复用户时明确说「本地 = 远端 @ `<commit>`」。

## 1. 这是什么

纯静态站（GitHub Pages，`main` 分支，源 `/`）。**没有服务端、没有构建服务器**：
所有 HTML 都是本地生成后提交的产物，Pages 只是把文件原样发出去。

## 2. 目录

```
index.html            首页（生成物，别手改）
posts/<slug>/         文章（生成物，别手改）
assets/base.css       外壳：变量、reset、顶栏、正文排版、回到顶部
assets/home.css       首页特有
assets/post.css       文章页特有（目录、来源块、站名下拉）
assets/site.js        主题切换 / 回到顶部 / Lab 暗门
tools/                生成器与质检脚本（手写）
                      build.py 一键构建 / md2post 转文章 / mdclean 剪藏 md 清洗管线（md2post 调用） / add_toc 目录与页脚 / gen_index 首页
                      gen_prevnext 上一篇下一篇 / gen_feed RSS+sitemap / stats 字数 / qa 体检
                      gen_legal 搬运页版权信号（canonical 指回原文 + noindex + 文末提示）
                      home_snippets 首页内嵌 JS/图标常量（gen_index 调用）
                      post_snippets 文章页注入的 JS 片段（add_toc 调用）
                      optimize_assets 存量图片压缩 / test_pipeline 回归测试 / rebuild 全量重建
                      unpublish 下线与恢复
                      config.py 环境配置（vault/skills 目录；PC 用 config.local.json 覆盖，已 gitignore）
skills/               skill 文档（单一源，build 时同步到 /var/minis/skills；PC/CI 无此目录自动跳过）
```

## 3. 一条命令构建

```bash
python3 tools/build.py            # 目录 → 字数 → 首页 → 上下篇 → RSS/sitemap → 测试 → hash → 同步 skill → qa
python3 tools/build.py --rebuild  # 另外先从 vault 的 md 重建全部文章（慢，且会改正文，慎用）
python3 tools/build.py --push "feat: xxx"   # 构建通过后自动 commit + push
```

PC（Windows）首次：`python -m pip install pyyaml markdown pillow`；之后用 `python tools/build.py`（内部子进程已用 sys.executable，不依赖 python3 命令）。

`qa.py` 的 P0 不为 0 会中止，不会推送。

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

## 5. 硬规矩（权威版在 SKILL.md，这里六条速览）

1. **只有一个站点仓库**，不要为单个页面新建 repo。
2. **生成物不手改**：`index.html`、`posts/**` 改了也会被下次 build 覆盖。
3. **push 前必须跑 `build.py`**，qa 的 P0 必须为 0。
4. **按钮里不放文字**，只放图标 + `aria-label`；要文字就用文字链接。
5. **上线前脱敏**：前公司名（合地/保信/华钦…）、证件、手机号、内网地址、密钥一律 P0 拦截；
   求职痕迹、薪资算 P1。细节见 `references/privacy.md`，改 vault 里的 md 不要只改 HTML。
6. **后处理脚本必须幂等**：跑两遍字节一致、注入标记各只有 1 份。

## 6. 踩过的坑（别再踩）

| 现象 | 原因 / 解法 |
|---|---|
| 正文出现 `##`、`**减号-列表**` | 剪藏 md 标题/列表缺空行；`md2post.normalize_md()` 已处理，别绕过它手写 HTML |
| 页面里出现 `[[双链]]` | 站点不认 Obsidian 双链，`unwiki()` 统一转纯文字 |
| 改了 CSS 但线上没变 | `post.css?v=` 是内容哈希，必须跑 `build.py` 重写（qa 会拦） |
| 按钮/目录文字叠在一起 | 后处理重复注入；剥离要按签名全量清，跑两遍 `rg -c` 必须 = 1 |
| 吸顶顶栏不吸了 | `overflow-x:hidden` 让 body 变滚动容器；用 `clip` |
| 右下浮动按钮被推出屏幕 | 宽表格撑出横向滚动；移动端表格改内部滚动 |
| 在 minis:// 里测 `replaceState` 报 SecurityError | 本地预览的限制，线上 https 才生效 |
| `rebuild.py` 跑完 diff 巨大 | 它会从 md 重生成正文，**可能改变已有正文**；只是改样式就别用 `--rebuild` |
| Lab 入口不见了 | 故意的：长按主题图标 1.5s 解锁，或访问 `/?u=lab` |
| 手机端按钮挡住内容 | 目录/回顶按钮静置 1.5s 自动淡出，滚动才浮现 |

## 7. 文档索引（要细节看这里）

- `skills/github-pages-deploy/SKILL.md` — 部署总入口 + 硬规矩权威版（本文件不复述）
- `references/content.md` — md→文章流水线、排版体检、后处理幂等
- `references/deploy.md` — 凭据、DNS 抽风、并发冲突、已知坑
- `references/design.md` — 按钮/目录/暗门等交互规范
- `references/readme.md` — 仓库 README 中英双语规范

## 8. 算不算做完了

`build.py` 全绿（测试 + qa P0=0）→ push → 等 30–60s →
`curl` 线上并 **grep 本次新增的字符串**（只看 200 会被缓存骗）。
