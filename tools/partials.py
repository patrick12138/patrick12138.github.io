#!/usr/bin/env python3
"""站点外壳的唯一来源：顶栏导航（Lab / About / 主题按钮）。

之前这套标记散在四个地方（首页模板、文章页模板、lab、404），改一个链接要改四处，
加一个入口要记得改全部——这就是「新增功能太麻烦」的根。

现在：
- `nav(prefix, current)` 生成 `<nav class="nav">…</nav>`
- `sync()` 在构建时把全站页面的这一段整体替换成生成结果（按页面所在层级算 prefix）

品牌那一段（首页的 `<a class="brand">` vs 文章页的站名下拉）刻意不纳入：
两者是不同的东西，不是复制。

用法：
  python3 tools/partials.py           # 同步全站顶栏
  python3 tools/partials.py --check   # 只检查不写
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

THEME_BTN = (
    '<button class="theme-toggle" id="themeToggle" aria-label="Toggle theme">'
    '<svg class="icon-sun" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="5"/>'
    '<line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>'
    '<line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>'
    '<line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>'
    '<line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>'
    '<svg class="icon-moon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2" stroke-linecap="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>'
    '</button>'
)

# 顶栏右侧的入口表：以后加入口只改这里
LINKS = (
    ("lab/", "Lab", "lab"),
    ("about/", "About", "about"),
)


def nav(prefix="", current=None):
    """prefix：相对当前页面的路径前缀（""/="../"/"../../"/"/"）。"""
    parts = []
    for href, label, key in LINKS:
        cls = ' class="on"' if key == current else (' class="nav-lab"' if key == "lab" else "")
        parts.append('<a href="%s%s"%s>%s</a>' % (prefix, href, cls, label))
    return '<nav class="nav">%s%s</nav>' % ("".join(parts), THEME_BTN)


NAV_RE = re.compile(r'<nav class="nav">.*?</nav>', re.S)


def sync(dry=False):
    pages = []
    for path in glob.glob(os.path.join(ROOT, "*.html")):
        # 404.html 会在任意路径下被返回，只能用绝对路径
        pages.append((path, "/" if os.path.basename(path) == "404.html" else ""))
    for path in glob.glob(os.path.join(ROOT, "*", "index.html")):
        pages.append((path, "../"))
    for path in glob.glob(os.path.join(ROOT, "posts", "*", "index.html")):
        pages.append((path, "../../"))

    changed = 0
    for path, prefix in pages:
        s = open(path, encoding="utf-8").read()
        if '<nav class="nav">' not in s:      # about 是独立外壳，不参与
            continue
        rel = os.path.relpath(path, ROOT).replace("\\", "/")
        current = "lab" if rel == "lab/index.html" else ("home" if rel == "index.html" else None)
        html = nav(prefix, current)
        new = NAV_RE.sub(lambda m: html, s, count=1)
        if new != s:
            if not dry:
                open(path, "w", encoding="utf-8").write(new)
            changed += 1
    return changed


def main():
    dry = "--check" in sys.argv
    n = sync(dry)
    if n:
        print(("需要更新" if dry else "已同步") + " %d 个页面的顶栏" % n)
        if dry:
            return 1
    else:
        print("顶栏已是最新")
    return 0


if __name__ == "__main__":
    sys.exit(main())
