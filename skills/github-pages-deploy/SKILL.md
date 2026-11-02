---
name: github-pages-deploy
description: Deploy pages to Patrick's single GitHub Pages site (patrick12138.github.io) and hand back a URL. Use whenever the user says 上线, 部署, 推到远程, 想要个链接, 手机上打不开, or asks to publish an HTML tool,写/搬运一篇文章, 排版体检. Covers the one-repo rule, credentials, the one-command build (tools/build.py), the md→post pipeline, design rules for buttons/TOC/theme, and the bilingual README convention.
version: 3.1.0
---

# GitHub Pages 部署（总入口）

站点只有一个仓库：**`patrick12138/patrick12138.github.io`**（`main`，Pages 源 `/`）。
工作副本固定 `/var/minis/workspace/site/`，URL 形态 `https://patrick12138.github.io/<子目录>/`。
**不要为单个页面新建仓库。**

仓库根的 `AGENTS.md` 是给 agent 的入口（对表清单 / 改哪儿 / 坑点表），本 skill 是它的展开版。

```
index.html                首页 = 唯一文章列表（全部 / 搬运 / 个人 三个 tab）
about/  lab/  tga/  backlog/
posts/<slug>/index.html   所有长文与笔记，一篇一个目录
assets/posts/<slug>/      配图（webp，本地化）
tools/                    build.py 一键构建；md2post.py rebuild.py add_toc.py gen_index.py qa.py sources.json
```

## 五条硬规矩

1. **文章一律由 `tools/md2post.py` 从 vault 的 md 生成**，不手写文章 HTML；
   改排版走 `tools/rebuild.py`，它按 `tools/sources.json` 整站重生成。
2. **push 前必须跑 `tools/build.py`（内含 qa），P0 不为 0 不许上线。**
3. **按钮里不放文字，只放图标**（`aria-label` 说明）；要文字就用文字链接。
4. **动手前先对表**：`git remote -v` 确认是 `patrick12138/patrick12138.github.io`、工作副本只有
   `/var/minis/workspace/site` 一处；`git fetch && git rev-list --left-right --count HEAD...origin/main`
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
| 写仓库 README（中英双语） | `references/readme.md` |

**脚本不在这里存副本**（存过一份，跟仓库漂移了）。一律用仓库里的 `/var/minis/workspace/site/tools/`：
`build.py`（一键：注入目录→生成首页→重算 hash→体检）、`gen_index.py`、`md2post.py`、`rebuild.py`、`add_toc.py`、`qa.py`、`sources.json`。

## 最短路径

**一条命令**（推荐）：

```bash
cd /var/minis/workspace/site
python3 tools/build.py --push "feat: 新文章 xxx"
```

`build.py` 固定顺序：可选 rebuild → 生成首页 → 重算资源哈希 → qa → 推送。
P0 不为 0 会**自动中止**，不会推上去。参数：

| 参数 | 作用 |
|---|---|
| （无） | 只重算哈希 + 生成首页 + 体检 |
| `--rebuild` | 额外先从 vault 重建全部文章（1–2 分钟） |
| `--push "msg"` | 构建成功后提交并推送 |

手动分步（调试时用）：

```bash
python3 tools/rebuild.py          # 从 vault 重新生成全部文章 + 重灌目录
python3 tools/gen_index.py        # 扫描 posts/ 重新生成首页
python3 tools/qa.py               # 排版体检，P0 必须为 0
```

- 只 grep 状态码会被 Pages 缓存骗，**必须验证本次新增的字符串**。
- 远端偶尔被别的会话推进：push 前 `git fetch && git rebase origin/main`，
  冲突时 `git checkout --ours <file>` 取远端版，再用幂等脚本把自己的改动加回去。

## 交付话术

给一行可点链接 + 本次改了什么 + 一句状态存哪（localStorage / 无后端）。
部署过程不展开，只有网络或权限问题才单独说明。
