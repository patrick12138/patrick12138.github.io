#!/usr/bin/env python3
"""给文章页补「字数 + 预估阅读时间」，幂等。

中文按 400 字/分钟，英文按 230 词/分钟。
显示格式：`2,340 字 · 约 6 分钟`
"""
import re
import postbody
import glob
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CN_RE = re.compile(r"[\u4e00-\u9fff]")
EN_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")


def body_html(html):
    return postbody.body_html(html)


def text_of(html):
    s = body_html(html)
    s = re.sub(r"<script.*?</script>", "", s, flags=re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    return s


def stats(html):
    t = text_of(html)
    cn = len(CN_RE.findall(t))
    en = len(EN_RE.findall(t))
    minutes = max(1, round(cn / 400 + en / 230))
    return cn + en, minutes


def label(html):
    chars, minutes = stats(html)
    return "%s 字 · 约 %d 分钟" % (format(chars, ","), minutes)


def inject(path):
    """把统计写进 <div class="meta">…</div>，已有的先删掉。"""
    s = open(path, encoding="utf-8").read()
    if '<div class="meta">' not in s:
        return False
    lab = label(s)
    # 先剥掉旧的统计片段
    s = re.sub(r'\s*<span class="stats">[^<]*</span>', "", s)
    def repl(m):
        base = m.group(2).rstrip(' ·　')
        return m.group(1) + base + ' · <span class="stats">' + lab + '</span>' + m.group(3)
    s = re.sub(r'(<div class="meta">)(.*?)(</div>)', repl, s, count=1, flags=re.S)
    open(path, "w", encoding="utf-8").write(s)
    return True


def main():
    n = 0
    for path in sorted(glob.glob(os.path.join(ROOT, "posts", "*", "index.html"))):
        if inject(path):
            n += 1
    print("字数统计：%d 篇" % n)


if __name__ == "__main__":
    main()
