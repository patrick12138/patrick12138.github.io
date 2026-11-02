#!/usr/bin/env python3
"""生成首页搜索索引：search.js（浅）+ search-deep.js（深，后台补齐）。

为什么要有它：首页列表只有标题和摘要，很多关键词只出现在正文里（比如 worktree、submodule），
用户记得自己写过却搜不到。

为什么要分两个文件：全文索引 744KB（gzip 328KB），首发就加载会让第一次搜索等一两秒。
拆成「浅索引 1500 字」（约 150KB，点开搜索立即到）+「深索引 1500 字之后的剩余正文」
（后台静默加载，到了自动重跑当前查询）。用户无感，但第一次搜索就能立即出结果。

用法：python3 tools/gen_search.py
"""
import glob
import html
import json
import os
import re
import postbody

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "search.js")
OUT_DEEP = os.path.join(ROOT, "search-deep.js")
BODY_CHARS = 1500      # 浅索引每篇收录的字数
MAX_HEADINGS = 30
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
    inner = postbody.body_html(doc)
    heads = [clean(h) for h in re.findall(r"<h[234][^>]*>(.*?)</h[234]>", inner, re.S)]
    heads = [h for h in heads if h and len(h) <= 60][:MAX_HEADINGS]
    text = clean(inner)
    body = text[:BODY_CHARS]
    body2 = text[BODY_CHARS:]
    # 日期用于“新近加权”，从 time 标签或列表里取不到，用 stats 里的字数不参与排序
    return {"s": slug, "t": title, "d": desc, "h": heads, "b": body, "b2": body2}


def main():
    posts = []
    for p in sorted(glob.glob(os.path.join(ROOT, "posts", "*", "index.html"))):
        try:
            posts.append(build_post(p))
        except Exception as e:          # 单篇坏了不要拖垮整站
            print("  跳过 %s：%s" % (p, e))

    shallow = [{"s": p["s"], "t": p["t"], "d": p["d"], "h": p["h"], "b": p["b"]} for p in posts]
    raw = json.dumps(shallow, ensure_ascii=False, separators=(",", ":"))
    open(OUT, "w", encoding="utf-8").write("window.__SEARCH=" + raw + ";\n")

    deep = [{"s": p["s"], "b": p["b2"]} for p in posts if p["b2"]]
    raw2 = json.dumps(deep, ensure_ascii=False, separators=(",", ":"))
    open(OUT_DEEP, "w", encoding="utf-8").write("window.__SEARCH_DEEP=" + raw2 + ";\n")

    print("search.js：%d 篇 %.0f KB ｜ search-deep.js：%d 篇 %.0f KB"
          % (len(shallow), len(raw.encode()) / 1024, len(deep), len(raw2.encode()) / 1024))


if __name__ == "__main__":
    main()
