# 下线 / 恢复一篇文章

## 一条命令

```bash
cd <当前工作副本>        # 手机 /var/minis/workspace/site，PC F:\patrick12138.github.io（见 AGENTS.md §0）
python3 tools/unpublish.py <slug> --dry     # 先看会发生什么：删什么、有多少别的文章引用它
python3 tools/unpublish.py <slug>           # 真下线
python3 tools/build.py                      # 体检（qa P0 必须 0）
git add -A && git commit -m "chore: 下线 <slug>" && git push
```

恢复：

```bash
python3 tools/unpublish.py <slug> --restore   # 从 git 历史取回页面目录 + 自动补回 sources.json 条目
python3 tools/build.py                        # 确认回到首页 / 相关阅读 / 搜索索引
```

取的是**删除那次提交的父版本**（删除提交里路径已经不存在，直接 checkout 会静默什么都不做）。
sources.json 的条目也从同一个父版本里读回来；找不回时会明确提示需要手补哪几个字段。

## 它会做什么

| 步骤 | 说明 |
|---|---|
| `git rm -r posts/<slug>/` | 页面从工作树移除，但**历史里还在**，随时可 checkout 回来 |
| 从 `sources.json` 移除条目 | 以后 `rebuild.py` 不会再把它生成回来 |
| 重生成 index / prevnext / **related** / **search** / feed | 列表、上下篇、相关阅读、两份搜索索引、RSS、sitemap 同步消失 |
| **列出站内入链** | 只有**正文里手工写的**链接会打印；上下篇 / 相关阅读是自动生成的，每轮 build 重算，不参与统计 |

## 为什么不用「移动到 offline 目录」

GitHub Pages 有 `.nojekyll`，仓库里任何目录都会被原样发布。放到 `_offline/` 之类的目录里
页面依然能被猜到 URL 访问到 —— 等于没下线。用 git 历史保存才干净。

## 要注意的

- **正文入链不会自动改**：脚本只报告。如果被下线的是常被引用的文章（比如某篇写得很全的指南），
  建议把那些链接换成同主题的替代文章，或直接删掉那句引用。
- **收藏夹 / 搜索引擎里的旧 URL 会 404**：这是预期的。仓库根已有 `404.html`（站点风格，带 `GET /?q=` 搜索框），
  下线文章的旧链接会落到那里。
- **下线不是草稿**：想先写不发，别建页面再删，直接在 vault 里躺着，等要发时再走 `md2post`。
- 下线后再想发，走正常发布流程（md → `md2post` → `sources.json`），不要用 restore 的页面当模板，
  那样会把旧的时间戳和元信息带回来。

## 手动跑一遍全链路

改过 `md2post` / `unpublish` / 生成器之后，跑这个（约 20 秒，只在临时目录里动，不碰仓库）：

```bash
python3 tools/test_flow.py            # 通过才继续
python3 tools/test_flow.py --keep     # 失败时保留 /tmp/flow-test-* 便于排查
```

它断言的事：md2post 生成页面并登记 → unpublish 删页面 + 清 sources + 首页/搜索/sitemap/feed 无残留
→ restore 取回页面并自动补回 sources → 重建后回到列表与搜索索引。

**不放进 build.py**：每次构建都跑太重；改完这几个脚本后手动跑一次即可。
