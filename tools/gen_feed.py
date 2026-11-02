#!/usr/bin/env python3
"""生成 feed.xml（RSS 2.0）+ sitemap.xml + robots.txt。

数据直接从已生成的 posts/*/index.html 里读，所以永远和站点一致。
用法：python3 tools/gen_feed.py
"""
import glob
import html
import os
import re
from datetime import datetime, timezone
from email.utils import format_datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://patrick12138.github.io"
TITLE = "patrick"
DESC = "写点东西，也搬运点好东西。"
NOW = datetime.now(timezone.utc)

CN = re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日")
EN = re.compile(r"([A-Z][a-z]+)\s+(\d{1,2}),\s*(\d{4})")
SHORT = re.compile(r"^(\d{1,2})月(\d{1,2})日")
MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June",
     "July", "August", "September", "October", "November", "December"], 1)}


def parse_date(text):
    """三套格式都要认：2026年7月21日 / July 21, 2026 / 7月21日（当年省略年份）。"""
    m = CN.search(text)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=timezone.utc)
    m = EN.search(text)
    if m:
        return datetime(int(m.group(3)), MONTHS.get(m.group(1), 1), int(m.group(2)), tzinfo=timezone.utc)
    m = SHORT.search(text)
    if m:
        return datetime(NOW.year, int(m.group(1)), int(m.group(2)), tzinfo=timezone.utc)
    return NOW


def collect():
    items = []
    for p in glob.glob(os.path.join(ROOT, "posts", "*", "index.html")):
        slug = os.path.basename(os.path.dirname(p))
        s = open(p, encoding="utf-8").read()
        h1 = re.search(r"<h1>(.*?)</h1>", s, re.S)
        meta = re.search(r'<div class="meta">(.*?)</div>', s, re.S)
        desc = re.search(r'<meta name="description" content="([^"]*)"', s)
        if not h1:
            continue
        items.append({
            "slug": slug,
            "title": html.unescape(re.sub(r"<[^>]+>", "", h1.group(1))).strip(),
            "desc": html.unescape(desc.group(1)) if desc else "",
            "date": parse_date(meta.group(1) if meta else ""),
            "link": "%s/posts/%s/" % (BASE, slug),
        })
    items.sort(key=lambda x: x["date"], reverse=True)
    return items


def write_feed(items):
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
           "<channel>",
           "<title>%s</title>" % html.escape(TITLE),
           "<link>%s/</link>" % BASE,
           "<description>%s</description>" % html.escape(DESC),
           "<language>zh-CN</language>",
           "<lastBuildDate>%s</lastBuildDate>" % format_datetime(items[0]["date"] if items else NOW),
           '<atom:link href="%s/feed.xml" rel="self" type="application/rss+xml" />' % BASE]
    for it in items:
        out += ["<item>",
                "<title>%s</title>" % html.escape(it["title"]),
                "<link>%s</link>" % it["link"],
                '<guid isPermaLink="true">%s</guid>' % it["link"],
                "<pubDate>%s</pubDate>" % format_datetime(it["date"]),
                "<description>%s</description>" % html.escape(it["desc"]),
                "</item>"]
    out += ["</channel>", "</rss>", ""]
    open(os.path.join(ROOT, "feed.xml"), "w", encoding="utf-8").write("\n".join(out))


def write_sitemap(items):
    urls = ["%s/" % BASE, "%s/about/" % BASE] + [it["link"] for it in items]
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        out.append("<url><loc>%s</loc></url>" % u)
    out += ["</urlset>", ""]
    open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8").write("\n".join(out))

    robots = "User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n" % BASE
    open(os.path.join(ROOT, "robots.txt"), "w", encoding="utf-8").write(robots)


def main():
    items = collect()
    write_feed(items)
    write_sitemap(items)
    print("feed %d 条 · sitemap %d 条" % (len(items), len(items) + 2))


if __name__ == "__main__":
    main()
