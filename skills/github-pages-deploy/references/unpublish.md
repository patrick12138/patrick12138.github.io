# 下线 / 恢复一篇文章

## 一条命令

```bash
cd /var/minis/workspace/site
python3 tools/unpublish.py <slug> --dry     # 先看会发生什么：删什么、有多少别的文章引用它
python3 tools/unpublish.py <slug>           # 真下线
python3 tools/build.py                      # 体检（qa P0 必须 0）
git add -A && git commit -m "chore: 下线 <slug>" && git push
```

恢复：

```bash
python3 tools/unpublish.py <slug> --restore   # 从 git 历史取回页面目录
# 然后手动把这一条补回 tools/sources.json（slug / md / author / date / kind）
python3 tools/build.py
```

## 它会做什么

| 步骤 | 说明 |
|---|---|
| `git rm -r posts/<slug>/` | 页面从工作树移除，但**历史里还在**，随时可 checkout 回来 |
| 从 `sources.json` 移除条目 | 以后 `rebuild.py` 不会再把它生成回来 |
| 重生成 index / prevnext / feed | 列表、上一篇下一篇、RSS、sitemap 同步消失 |
| **列出站内入链** | 其他文章正文里指向它的链接会打印出来，人工决定改不改（脚本不动正文） |

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
