# 仓库 README：中英双语，英文优先

Patrick 所有仓库都这样，照抄结构：

```markdown
# Project Name

[English](./README.md) | [简体中文](./README.zh-CN.md)

One sentence on what it is and who it's for.

## Features        ← 或 Pages / How it behaves
- bullet，一句话一条

## Tech Stack      ← 可选
## Requirements   ← 运行环境 / SDK 版本
## Build / Run    ← 命令块
## Project Structure
## Known limitations
## License
```

- **文件名固定**：`README.md`（英文，仓库首页显示的就是它）+ `README.zh-CN.md`（中文）。
- 标题下第一行必须是语言切换：英文文件写
  `[English](./README.md) | [简体中文](./README.zh-CN.md)`；中文文件写
  `[English](./README.md) | 简体中文`。
- **英文在前、为主**。中文版不逐字硬译，语气自然，技术细节一条都不能少
  （表格、参数、命令、路径、issue 链接全保留）。
- 章节标题用英文；命令、路径、字段名、代码不翻译。两版结构对称，方便对照维护。
- 改已有仓库的 README 时：`git show HEAD:README.md` 拿原版 → 存成 `README.zh-CN.md` →
  再写英文版覆盖 `README.md`。**顺序别反**，否则会把英文写进中文文件。
- 已按此规范改过：`patrick12138.github.io`、`telegram-toggle`。
