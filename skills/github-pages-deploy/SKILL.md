---
name: github-pages-deploy
description: Deploy to Patrick's single GitHub Pages site (patrick12138.github.io) and hand back a URL. Use when the user says 上线 / 部署 / 推远程 / 要链接 / 手机上打不开, or asks to 写/搬运文章、排版体检。不用于其他仓库或托管平台。
version: 3.1.0
---

# GitHub Pages 部署（总入口）

站点只有一个仓库：**`patrick12138/patrick12138.github.io`**（`main`，Pages 源 `/`）。
工作副本两处：手机 `/var/minis/workspace/site/`、PC `F:\patrick12138.github.io`（同一远端，URL 形态 `https://patrick12138.github.io/<子目录>/`）。
**不要为单个页面新建仓库。**

仓库根的 `AGENTS.md` 是给 agent 的入口（对表清单 / 改哪儿 / 坑点表），本 skill 是它的展开版。

```
index.html                首页 = 唯一文章列表（全部 / 搬运 / 个人 三个 tab）
about/  lab/  tga/  backlog/
posts/<slug>/index.html   所有长文与笔记，一篇一个目录
assets/posts/<slug>/      配图（webp，本地化）
```

## 硬规矩（6 条）

1. **文章一律由 `tools/md2post.py` 从 vault 的 md 生成**，不手写文章 HTML；
   改样式**只改 `assets/*.css` 然后跑 `build.py`**（它会重灌目录、重算哈希）。
   `tools/rebuild.py` 是从 vault 的 md 重新生成正文，正文没变就别用——它会改动已有页面。
2. **push 前必须跑 `tools/build.py`（内含 qa），P0 不为 0 不许上线。**
3. **按钮里不放文字，只放图标**（`aria-label` 说明）；要文字就用文字链接。
4. **动手前先对表**：`git remote -v` 确认是 `patrick12138/patrick12138.github.io`、当前工作副本只有
   手机 `/var/minis/workspace/site` / PC `F:\patrick12138.github.io` 两处之一；
   `git fetch && git rev-list --left-right --count HEAD...origin/main`
   必须是 `0 0`（这个仓库经常被别的会话并发推），并向用户明确报「本地 = 远端 @ <commit>」。
5. **上线前必过脱敏**：前公司/客户名、证件、手机号、内网地址、密钥一旦出现在页面上就是 P0
   （`qa.py` 的 `check_privacy()` 会自动拦），改的是 vault 里的 md 而不是 HTML。
6. **后处理脚本必须幂等**：跑两遍 diff 为空、注入标记计数为 1，才算做完（详见 `references/content.md`）。

## 按需读的参考文件

| 要做的事 | 读这个 |
|---|---|
| 加一篇文章 / 笔记，整站重排，排版质检 | `references/content.md` |
| 推代码、凭据、DNS 抽风、验证线上、已知坑 | `references/deploy.md` |
| 新页面设计（按钮、目录、深浅色、组件规范） | `references/design.md` |
| 下线 / 恢复一篇文章 | `references/unpublish.md` |
| **上线前脱敏**（公司名、证件、联系方式、求职痕迹） | `references/privacy.md` |
| **做图标 / favicon** | `references/icons.md`（32 网格、笔画≥4u、16px 灰边验收） |
| 写仓库 README（中英双语） | `references/readme.md` |

## 脚本一览（从左 AGENTS.md §2 搬来）

| 脚本 | 干什么 |
|---|---|
| `build.py` | 一键构建（顺序以它 docstring 为准），P0 不为 0 中止 |
| `preflight.py` | 开工对表：remote、是否落后、工作区是否干净 |
| `md2post.py` / `mdclean.py` | 剪藏 md 清洗 + 转文章 |
| `add_toc.py` | 目录、页脚、表格包裹、相关阅读注入 |
| `gen_index.py` / `gen_feed.py` / `gen_legal.py` | 首页 / RSS+sitemap / 搬运页版权信号 |
| `gen_prevnext.py` / `gen_search.py` | 上下篇 / 搜索索引 |
| `qa.py` / `check_skills.py` | 体检（P0 中止）/ 文档与代码一致性 |
| `post_snippets.py` | 只剩 `BRAND_JS`（站名下拉的一小段内联脚本） |
| `rebuild.py` / `unpublish.py` / `optimize_assets.py` | 全量重建 / 下线恢复 / 图片压缩 |
| `test_pipeline.py` / `test_flow.py` | 回归 / 上线-下线-恢复链路 |
| `postbody.py` / `dates.py` / `partials.py` / `config.py` / `stats.py` | 公共模块：正文边界、日期、顶栏、配置、字数 |

**脚本不在这里存副本**（存过一份，跟仓库漂移了）。一律用**当前工作副本**仓库内的 `tools/`（两处路径见 AGENTS.md §0）：
`build.py`（一键：目录→字数→首页→上下篇→相关阅读→搜索索引→RSS→测试→hash→skill 一致性→体检，顺序以它自己的 docstring 为准）、`gen_index.py`、`md2post.py`、`rebuild.py`、`add_toc.py`、`qa.py`、`sources.json`。

## 最短路径

**一条命令**（推荐）：

```bash
cd <当前环境的工作副本>          # 手机 /var/minis/workspace/site，PC F:\patrick12138.github.io
python3 tools/build.py --push "feat: 新文章 xxx"    # PC 用 python tools/build.py
```

`build.py` 固定顺序：可选 rebuild → 生成首页 → 重算资源哈希 → qa → 推送。
P0 不为 0 会**自动中止**，不会推上去。参数：

| 参数 | 作用 |
|---|---|
| （无） | 只重算哈希 + 生成首页 + 体检 |
| `--rebuild` | 额外先从 vault 重建全部文章（1–2 分钟） |
| `--push "msg"` | 构建成功后提交并推送 |

- 只 grep 状态码会被 Pages 缓存骗，**必须验证本次新增的字符串**。
- 远端偶尔被别的会话推进：push 前 `git fetch && git rebase origin/main`；冲突处理见 `references/deploy.md`。

## 交付话术（别写报告腔）

**NO**：我已经成功完成了本次修改！主要做了以下几点优化：1) 优化了间距 2) 调整了按钮位置。希望这些改动对您有帮助，如有问题随时告诉我。

**OK**：改了三处（h2 间距 12→16、沉浸按钮只在 >1024px 显示、`post.css` 版本戳重算），线上已验证 `v=7d83bae`。

一行可点链接 + 改了什么 + 状态存哪（localStorage / 无后端）。部署过程不展开，只有网络或权限问题才单独说明。
