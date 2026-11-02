#!/usr/bin/env python3
"""给每篇文章注入「上一篇 / 下一篇」（全局按发布时间，不受首页 tab 影响）。

顺序取自 index.html（已按日期倒序生成）。可重复执行：先剥旧的再插。
用法：python3 tools/gen_prevnext.py
"""
import glob
import html
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGER_RE = re.compile(r'<nav class="pager".*?</nav>\s*', re.S)


def order():
    idx = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    return re.findall(r'href="posts/([a-z0-9-]+)/"', idx)


def title_of(slug):
    p = os.path.join(ROOT, "posts", slug, "index.html")
    if not os.path.exists(p):
        return slug
    s = open(p, encoding="utf-8").read()
    m = re.search(r"<h1>(.*?)</h1>", s, re.S)
    return html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else slug


def main():
    slugs = order()
    titles = {s: title_of(s) for s in slugs}
    n = 0
    for i, slug in enumerate(slugs):
        path = os.path.join(ROOT, "posts", slug, "index.html")
        if not os.path.exists(path):
            continue
        s = open(path, encoding="utf-8").read()
        s = PAGER_RE.sub("", s)

        newer = slugs[i - 1] if i > 0 else None      # 列表更靠上 = 更新
        older = slugs[i + 1] if i + 1 < len(slugs) else None
        parts = []
        if older:
            parts.append('<a class="pager-prev" href="../%s/"><span class="pager-k">← 上一篇</span>'
                         '<span class="pager-t" title="%s">%s</span></a>' % (older, html.escape(titles[older]), html.escape(titles[older])))
        else:
            parts.append('<span class="pager-empty"></span>')
        if newer:
            parts.append('<a class="pager-next" href="../%s/"><span class="pager-k">下一篇 →</span>'
                         '<span class="pager-t" title="%s">%s</span></a>' % (newer, html.escape(titles[newer]), html.escape(titles[newer])))
        nav = '<nav class="pager" aria-label="文章导航">%s</nav>\n' % "".join(parts)

        if '<a class="back"' in s:
            s = s.replace('<a class="back"', nav + '<a class="back"', 1)
        else:
            continue
        open(path, "w", encoding="utf-8").write(s)
        n += 1
    print("prev/next 注入 %d 篇" % n)


if __name__ == "__main__":
    main()
