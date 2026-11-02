# patrick12138.github.io

[English](./README.md) | 简体中文

一些自己真在用的小页面，托管在 GitHub Pages。没有框架、没有后端；文章和索引由仓库里的 `tools/` 在本地生成后推送，Pages 只负责静态托管。

## 页面

| 路径 | 是什么 |
| --- | --- |
| `/` | 博客首页 —— 原创与搬运，按时间倒序 |
| `/posts/<slug>/` | 单篇文章 |
| `/lab/` | Lab —— 自己做来玩的小东西 |
| `/backlog/` | 待玩清单 —— 划掉一款，剩余时长实时减少 |
| `/tga/` | TGA 年度游戏提名清单，2014–2025（68 席） |
| `/about/` | 终端风格的个人页，中英文可切 |

## 目录结构

```text
index.html          博客首页（tools/gen_index.py 生成）
posts/*/index.html  文章（tools/md2post.py 生成，共用 assets/base.css + post.css）
lab/index.html      Lab 索引
tga/index.html      TGA 清单（工具页，样式内联自包含）
about/index.html    关于页（工具页，样式内联自包含）
assets/*.css|site.js 博客外壳与正文样式、主题/回到顶部脚本
assets/posts/*/     从原文下载的图片
tools/              构建脚本（文章转换、首页生成、目录、字数、体检）
.nojekyll           原样输出，跳过 Jekyll
```

## 新增一个页面

- **文章**：不要手写 HTML。见下面「开发」——`md2post.py` 转好、`build.py` 一条命令生成首页并推送。
- **工具页**：建 `<slug>/index.html`，CSS、JS 和数据都内联，保证单文件能跑；首页列表由脚本生成，不用手动改。

## 说明

- 每个页面的状态都存在 `localStorage` 里，不上传到任何地方。
- `/` 和 `/tga/` 不加载外部字体和 CDN；`/about/` 从 Google Fonts 取 Figtree 和 JetBrains Mono，取不到就走系统字体兜底。

## 开发

一切都由 `tools/` 生成，不手写文章 HTML。

| 脚本 | 用途 |
| --- | --- |
| `build.py` | 一条命令：重建 → 目录 → 首页 → 资源哈希 → 体检 → 可选推送 |
| `md2post.py` | 单篇 markdown 转文章页（图片本地化、媒体转外链） |
| `rebuild.py` | 按 `sources.json` 全量重建 |
| `add_toc.py` | 注入 / 刷新目录（幂等） |
| `gen_index.py` | 扫描 `posts/` 重新生成首页列表（含字数） |
| `stats.py` | 给文章页补「字数 · 预估阅读时间」 |
| `qa.py` | 排版体检，P0 不为 0 不许上线 |
| `test_pipeline.py` | 回归测试：md2post / add_toc / gen_index 幂等 |

`post_template.html` 是文章外壳模板，`sources.json` 是 slug → vault 源文件的登记表（`md2post.py` 会自动写入）。

```bash
python3 tools/build.py --push "feat: 新文章"
```

页面里的 `?v=` 是 `build.py` 写入的内容哈希，不要手改。

## 许可

个人项目，代码随便看、随便抄。
