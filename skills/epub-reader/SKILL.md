---
name: epub-reader
description: 把一本 EPUB 挂到 patrick12138.github.io/read/ 供自己在手机/电脑上读。当用户说「传本书到线上」「放到书架」「想在线看这本书」时用这条。和文章上线（skill `github-pages-deploy`）是两条独立的路，别混。
version: 1.0.0
---

# 电子书上线（/read/）

书和文章是**两条互不相干的路**：

| | 文章 | 书 |
|---|---|---|
| skill | `github-pages-deploy` | 这一条 |
| 产物 | `posts/<slug>/index.html` | `read/<slug>/` |
| 触发构建 | 必须 `build.py` | 不需要（不进首页/搜索/feed/sitemap） |
| 内容进 agent 上下文 | 要（写正文） | **一个字的正文都不该进** |

## 一条命令

```bash
cd /var/minis/workspace/site            # PC 是 F:\patrick12138.github.io
python3 tools/newbook.py --file ~/书.epub [--title "书名"] [--slug 六位hex]
```

- 不给 `--slug` 就随机 6 位 hex（书架靠不可猜的路径防乱翻）
- 不给 `--title` 就取 EPUB 的 `dc:title`（常带一堆出版社营销词，往往要手动覆盖）
- 重跑同一 slug 会**整本重建**（章节、图片、book.json 全换）

## 为什么省 token

正文由 Python 解包后写进 HTML，agent 只写脚本、不读内容：

1. 只读 `container.xml → OPF` 拿书名/作者/封面路径
2. 章节正文解出来直接塞进 `index.html` 的 `<template id="chN">`
3. 一本 10 万字的书，成本 ≈ 几次脚本调用，而不是几十万 token 的阅读

**不要**为了「确认排版好不好」去读正文，用 browser_use 截图看。

## 产物

```
read/<slug>/index.html   阅读器 + 全部正文（内嵌 template，零网络请求）
read/<slug>/book.json    章节标题/字数索引（书架、进度用）
read/<slug>/ch/*.html    章节片段备份（不在渲染路径上）
read/<slug>/a/**         图片字体，保持包内相对结构
read/index.html          书架（每次生成重扫 read/*/book.json）
```

## 拆章规则（脚本里定的，改之前想清楚）

- 按 `toc.ncx` 目录项切；一个目录项 = 一章（`标题页 + 正文页`两个 spine 文件会合并）
- 标题命中 `版权页|目录|扉页|封面|出版信息|Contents|Cover|Copyright|Colophon` → 整章不生成
- 章节里出现 ≥2 种出版信息（`图书在版编目|CIP数据|责任编辑|装帧设计|ISBN 978`）且 <3000 字 → 丢掉，防止没标题的版权章漏网
- 字数 <20 的纯图页跳过
- 书内自带的那页目录**一律删掉**，目录只留阅读器侧边抽屉

## 阅读器（tools/read_template.html）

改样式/交互只改这一个文件，然后重跑 `newbook.py` 生成。

- **纯 DOM 滚动阅读，不用 iframe**。epub.js 在这套 WebView 里会让渲染队列永久卡死（srcdoc iframe 不派发 load 事件），别再回头试
- 顶栏：触屏上滑唤出/下滑收起；PC 指针进入顶部 80px 才出现，离开 600ms 收起
- 进度：只存本地 `localStorage['rd:<slug>:pos'] = {ch, r, n}`；触屏往回翻时闪 1.2 秒，PC 悬停右下角
- 章节数（`n`）变了旧进度自动作废 —— 重新拆书不会让人跳到乱位置
- 三套底色（深色/浅色/羊皮纸），首次进入跟随系统；书架跟随系统并复用主页配色变量

## 验证

```bash
# 本地
browser_use navigate minis://workspace/site/read/<slug>/index.html
# 看：首屏是不是正文（不是版权页）、目录条目数、往回翻时百分比闪不闪

# 线上（Pages 是异步构建，等 50s）
curl -s -o /dev/null -w '%{http_code}\n' https://patrick12138.github.io/read/<slug>/
curl -s https://patrick12138.github.io/read/<slug>/ | rg -o 'data-t="[^"]*"' | head
```

推送流程与凭据同 `github-pages-deploy/references/deploy.md`（PAT 在 `$GITHUB_TOKEN`，push 时 URL 内嵌，推完还原）。

## 已知限制

- **没有全文搜索**（正文是 DOM 不是索引）。要搜索得另建一层
- **仓库公开**：`/read/` 只靠 `noindex` + `robots.txt` 的 `Disallow: /read/` 挡搜索引擎，挡不住拿到链接的人
- 书的体积会进 git 历史，删书要 `git rm` + 改历史才干净
- 大书（>2MB 正文）的 `index.html` 会很大，首屏解析变慢；先试试，不行再改成分章 fetch
