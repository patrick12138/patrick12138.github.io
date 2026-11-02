#!/usr/bin/env python3
"""生成首页搜索索引 search.js。

为什么要有它：首页列表只有标题和摘要，很多关键词只出现在正文里（比如 worktree、缓存命中率），
用户记得自己写过却搜不到。索引在构建期压出来，前端只在点开搜索时才 fetch，不拖慢首屏。

用法：python3 tools/gen_search.py
"""
import glob
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "search.js")
BODY_CHARS = 1500      # 每篇正文收录的字数上限，够覆盖关键词，又不至于把索引撑大
MAX_HEADINGS = 30


def clean(s):
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def one(doc, pat, flags=re.S):
    m = re.search(pat, doc, flags)
    return m.group(1) if m else ""


def build_post(path):
    doc = open(path, encoding="utf-8").read()
    slug = os.path.basename(os.path.dirname(path))
    title = clean(one(doc, r"<h1[^>]*>(.*?)</h1>")) or slug
    desc = clean(html.unescape(one(doc, r'<meta name="description" content="([^"]*)"')))
    # 正文边界：从 .body 起点到 related / pager / back 三者里最先出现的那个。
    # 不能用「到第一个 </div>」或「到 pager」——正文里现在有 .tablewrap，
    # 而 related 又插在 pager 之前，两种写法都会把正文截成空。
    i = doc.find('<div class="body"')
    if i > 0:
        i = doc.find(">", i) + 1
        ends = [doc.find(x, i) for x in ('<nav class="related"', '<nav class="pager"',
                                         '<aside class="legal-note"', '<a class="back"')]
        ends = [e for e in ends if e > i]
        inner = doc[i:min(ends) if ends else len(doc)]
    else:
        inner = ""
    heads = [clean(h) for h in re.findall(r"<h[234][^>]*>(.*?)</h[234]>", inner, re.S)]
    heads = [h for h in heads if h and len(h) <= 60][:MAX_HEADINGS]
    body = clean(inner)[:BODY_CHARS]
    # 日期用于“新近加权”，从 time 标签或列表里取不到，用 stats 里的字数不参与排序
    return {"s": slug, "t": title, "d": desc, "h": heads, "b": body}


def main():
    posts = []
    for p in sorted(glob.glob(os.path.join(ROOT, "posts", "*", "index.html"))):
        try:
            posts.append(build_post(p))
        except Exception as e:          # 单篇坏了不要拖垮整站
            print("  跳过 %s：%s" % (p, e))
    raw = json.dumps(posts, ensure_ascii=False, separators=(",", ":"))
    # 用 .js 而不是 .json：fetch() 在 file:// 和 minis:// 预览下会被拦，
    # 动态 <script> 到处都能加载，https 下也一样。
    open(OUT, "w", encoding="utf-8").write("window.__SEARCH=" + raw + ";\n")
    print("search.js：%d 篇，%.0f KB" % (len(posts), len(raw.encode()) / 1024))


if __name__ == "__main__":
    main()
