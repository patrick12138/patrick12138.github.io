#!/usr/bin/env python3
"""构建期生成「相关阅读」：按标题 / 小标题 / 摘要的共词相似度，每篇挑 2–3 篇。

不做标签体系——45 篇的规模，自动共词比人工归类省事，也不会因为漏打标签而失效。
幂等：每次先剥掉旧的 <nav class="related"> 再重新插到 pager 之前。

用法：python3 tools/gen_related.py
"""
import glob
import html
import math
import os
import re
import postbody
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_RELATED = 3
MIN_SCORE = 0.06
DF_CAP = 0.45          # 出现在超过 45% 文章里的词当作停用词过滤掉

CJK = re.compile(r"[\u4e00-\u9fff]+")
LAT = re.compile(r"[A-Za-z][A-Za-z0-9.+#_-]*")


def strip_tags(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(s))).strip()


def tokens(text):
    out = []
    for seg in CJK.findall(text):
        out += [seg[i:i + 2] for i in range(len(seg) - 1)]
        if len(seg) == 1:
            out.append(seg)
    out += [w.lower() for w in LAT.findall(text)]
    return [t for t in out if len(t) > 1 or t.isalnum()]


def collect(path):
    doc = open(path, encoding="utf-8").read()
    slug = os.path.basename(os.path.dirname(path))
    title = strip_tags((re.search(r"<h1[^>]*>(.*?)</h1>", doc, re.S) or [None, ""])[1]) if re.search(
        r"<h1[^>]*>(.*?)</h1>", doc, re.S) else slug
    desc = html.unescape((re.search(r'<meta name="description" content="([^"]*)"', doc) or [None, ""])[1])
    heads = " ".join(strip_tags(h) for h in re.findall(r"<h[234][^>]*>(.*?)</h[234]>", doc, re.S))
    body = postbody.text_of(doc)[:1200]
    c = Counter()
    c.update({t: 3 for t in tokens(title)})
    c.update({t: 2 for t in tokens(heads)})
    c.update({t: 1 for t in tokens(desc)})
    c.update({t: 1 for t in tokens(body)})
    return {"slug": slug, "path": path, "title": title, "vec": c}


def build_vecs(posts):
    df = Counter()
    for p in posts:
        for t in p["vec"]:
            df[t] += 1
    n = len(posts)
    drop = {t for t, d in df.items() if d > n * DF_CAP}
    for p in posts:
        # tf-idf：越少见的词权重越高，否则「Codex」这种高频词会把所有文章都连成一坨
        v = {}
        for t, w in p["vec"].items():
            if t in drop:
                continue
            v[t] = w * (math.log((n + 1) / (df[t] + 1)) + 1)
        norm = math.sqrt(sum(w * w for w in v.values())) or 1.0
        p["vec"] = v
        p["norm"] = norm
    return posts


def similarity(a, b):
    small, big = (a["vec"], b["vec"]) if len(a["vec"]) < len(b["vec"]) else (b["vec"], a["vec"])
    dot = sum(w * big.get(t, 0) for t, w in small.items())
    return dot / (a["norm"] * b["norm"])


RELATED_RE = re.compile(r'\s*<nav class="related".*?</nav>', re.S)


def inject(path, picks):
    doc = open(path, encoding="utf-8").read()
    doc = RELATED_RE.sub("", doc)
    if not picks:
        open(path, "w", encoding="utf-8").write(doc)
        return 0
    items = "".join('<li><a href="../%s/">%s</a></li>' % (s, html.escape(t)) for s, t in picks)
    block = ('<nav class="related" aria-label="相关阅读"><span class="related-k">相关阅读</span>'
             '<ul>%s</ul></nav>\n' % items)
    if '<nav class="pager"' in doc:
        doc = doc.replace('<nav class="pager"', block + '<nav class="pager"', 1)
    else:
        doc = doc.replace('<a class="back"', block + '<a class="back"', 1)
    open(path, "w", encoding="utf-8").write(doc)
    return len(picks)


def main():
    posts = [collect(p) for p in sorted(glob.glob(os.path.join(ROOT, "posts", "*", "index.html")))]
    build_vecs(posts)
    total = 0
    for p in posts:
        scored = []
        for q in posts:
            if q["slug"] == p["slug"]:
                continue
            s = similarity(p, q)
            if s >= MIN_SCORE:
                scored.append((s, q["slug"], q["title"]))
        scored.sort(reverse=True)
        picks = [(slug, title) for _, slug, title in scored[:MAX_RELATED]]
        total += inject(p["path"], picks)
    print("相关阅读：%d 篇，共插入 %d 条" % (len(posts), total))


if __name__ == "__main__":
    main()
