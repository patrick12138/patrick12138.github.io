# patrick12138.github.io

[English](./README.md) | 简体中文

一些自己真在用的小页面，托管在 GitHub Pages。没有框架、没有后端、没有构建步骤。

## 页面

| 路径 | 是什么 |
| --- | --- |
| `/` | 入口页 —— Notion 风格的页面列表 |
| `/tga/` | TGA 年度游戏提名清单，2014–2025（68 席） |
| `/about/` | 终端风格的个人页，中英文可切 |

## 目录结构

```text
index.html          入口页
tga/index.html      TGA 清单（单文件自包含）
about/index.html    关于页（单文件自包含）
.nojekyll           原样输出，跳过 Jekyll
```

## 新增一个页面

1. 建 `<slug>/index.html`，CSS、JS 和数据都内联，保证单文件能跑。
2. 在根 `index.html` 的 `.list` 里加一条。
3. push 到 `main`，Pages 会在 30–60 秒内重新构建。

## 说明

- 每个页面的状态都存在 `localStorage` 里，不上传到任何地方。
- `/` 和 `/tga/` 不加载外部字体和 CDN；`/about/` 从 Google Fonts 取 Figtree 和 JetBrains Mono，取不到就走系统字体兜底。

## 许可

个人项目，代码随便看、随便抄。
