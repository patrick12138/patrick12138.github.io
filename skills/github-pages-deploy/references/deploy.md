# 部署：凭据、推送、验证、排障

## 凭据

- PAT 在 shell 环境变量 **`$GITHUB_TOKEN`**（classic，带 `repo` scope）。
  **不是 `GITHUB_PAT`** —— 那个在 shell 里不存在，拿去调 GitHub MCP 会报
  `Illegal header value b'Bearer '`。
- 永远不要 echo / print token 值。
- push 必须 URL 内嵌 token（`http.extraheader` 会 invalid credentials），推完立刻还原：

```bash
git remote set-url origin "https://x-access-token:$GITHUB_TOKEN@github.com/<owner>/<repo>.git"
git push -u origin main
git remote set-url origin https://github.com/<owner>/<repo>.git
```

- **token 没有 `delete_repo`**：删仓库会 `403 Must have admin rights`，
  让用户去 `https://github.com/<owner>/<repo>/settings` 底部 Danger Zone 自己删，别反复试。

## 网络：DNS 抽风

症状：`Could not resolve host: github.com`，连 baidu 都 000，但 `curl --resolve` 硬指 IP 能通。
往 `/etc/hosts` 写死（先 `getent hosts github.com` 确认）：

```bash
echo "140.82.113.4 github.com"      >> /etc/hosts
echo "140.82.113.5 api.github.com"  >> /etc/hosts
echo "185.199.108.153 patrick12138.github.io" >> /etc/hosts
```

## 推送与验证

```bash
cd /var/minis/workspace/site
git add -A && git commit -m "…"
git fetch origin main && git rebase origin/main     # 别的会话可能也在推
git remote set-url origin "https://x-access-token:$GITHUB_TOKEN@github.com/patrick12138/patrick12138.github.io.git"
git push origin main
git remote set-url origin https://github.com/patrick12138/patrick12138.github.io.git

sleep 45   # Pages legacy 构建是异步的，30–60s
curl -s -L "https://patrick12138.github.io/<path>/?v=N" -o /tmp/live.html \
  -w "%{http_code} %{size_download}\n" --max-time 25
rg -o '<title>[^<]*</title>' /tmp/live.html
rg -c '<本次新增的字符串>'      # 必须验证新增内容，只看 200 会被缓存骗
```

浏览器看到旧版：加 `?v=N` 或硬刷新（Ctrl/Cmd+Shift+R）。

## 并发冲突（一个会话以上同时改仓库时）

远端被推进过时 rebase 会冲突，常见在 `index.html`（两边都在插文章条目）：

```bash
git checkout --ours index.html     # rebase 中 ours = 远端版本
git add index.html && GIT_EDITOR=true git rebase --continue
```

然后把本地条目用**幂等脚本**（按 slug 去重 + 按日期倒序重排）重新插进去，不要手工对行。

## 首次建站（已完成，仅备查）

```bash
curl -s -X POST -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/user/repos \
  -d '{"name":"patrick12138.github.io","private":false}'

curl -s -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://api.github.com/repos/patrick12138/patrick12138.github.io/pages   # 404 才 POST
# POST body: {"source":{"branch":"main","path":"/"}}
```

## 本地验收

```bash
browser_use navigate minis://workspace/site/<slug>/index.html
browser_use screenshot                      # 手机尺寸
browser_use set_viewport 1180 900           # PC（别用 1440×900，会截出白图）
browser_use screenshot
```

`minis://` 下绝对路径 `/xxx` 解析到 minis 根目录，页面内不要写根路径引用。

## 已知坑

| 现象 | 原因 / 解法 |
|---|---|
| `invalid credentials` | 用了 `http.extraheader`，改用 x-access-token URL |
| `Could not resolve host` | 沙盒 DNS 挂了，往 `/etc/hosts` 写死 IP |
| 线上还是旧内容 | Pages 未构建完（等 30–60s）或浏览器缓存（`?v=N`） |
| 截图全白 | 1440×900 这类大视口会白图，换 1180×760 |
| 子路径 404 | 目录里必须有 `index.html`；`/tga` 301 到 `/tga/` 属正常 |
| 删除仓库 403 | token 无 `delete_repo`，让用户自己删 |
| 高亮错位（导航 `class="on"`） | 从首页复制骨架时把 `on` 一起带过去了，逐页改回 |
