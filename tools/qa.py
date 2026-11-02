#!/usr/bin/env python3
"""上线前的排版体检：扫 posts/*/index.html 的正文，报告残留的 markdown 标记、
异常换行、怪字符、空段落、未闭合标签等。有 P0 问题就退出码 1。

用法：
  python3 tools/qa.py            # 检查全部
  python3 tools/qa.py posts/xxx/index.html
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CHECKS = [
    # (级别, 说明, 正则)
    ("P0", "残留 markdown 标题 ##", r"(?<![\w#])#{2,}\s+\S"),
    ("P0", "残留粗体 **", r"(?<!\*)\*\*[^*\n]{1,80}\*\*"),
    ("P0", "残留 wikilink", r"\[\[[^\]]{1,80}\]\]"),
    ("P0", "残留 md 链接语法", r"(?<![\"'=>])\[[^\]\n]{0,40}\]\((?!http)[^)\n]{0,80}\)"),
    ("P0", "em dash 被转义 \\-", r"\\-"),
    ("P0", "反引号残留 \\`", r"\\`"),
    ("P1", "行内出现裸 - 列表符号", r"<br ?/?>\s*[-*+]\s+\S"),
    ("P1", "空段落", r"<p>\s*(&nbsp;)?\s*</p>"),
    ("P2", "源码里连续空行", r"\n\s*\n\s*\n\s*\n"),
    ("P1", "零宽/异常字符", r"[\u200b-\u200f\ufeff\ufffd]"),
    ("P1", "html 实体重复转义", r"&amp;(?:amp|lt|gt|quot|#\d+);"),
    ("P2", "段落内硬换行 (br)", r"<p>[^<]{5,}<br ?/?>"),
    ("P2", "空格后紧跟中文标点", r"[ \t]+[，。；：！？、]"),
    ("P2", "中文之间多余空格", r"[\u4e00-\u9fff]\s+[\u4e00-\u9fff]"),
]


def body_of(s):
    i = s.find('<div class="body"')
    j = s.find('<a class="back"')
    return s[i:j] if i >= 0 and j > i else ""


def check(path):
    s = open(path, encoding="utf-8").read()
    body = body_of(s)
    # 代码块里的内容不算排版问题
    body = re.sub(r"<pre[^>]*>.*?</pre>", "x", body, flags=re.S)
    body = re.sub(r"<code[^>]*>.*?</code>", "x", body, flags=re.S)
    body = re.sub(r'="[^"]*"', '=""', body)   # 属性值（alt/title）不算正文
    hits = []
    for level, desc, pat in CHECKS:
        for m in re.finditer(pat, body):
            seg = body[max(0, m.start() - 40):m.end() + 40].replace("\n", " ")
            hits.append((level, desc, seg.strip()[:110]))
    return hits


def check_kinds():
    """首页 data-kind 与文章页 meta 的「搬运/原创」必须一致。"""
    idx = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    kinds = dict(re.findall(r'<li data-kind="(\w+)"><a href="posts/([a-z0-9-]+)/"', idx))
    kinds = {slug: kind for kind, slug in kinds.items()}
    bad = []
    for slug, kind in kinds.items():
        p = os.path.join(ROOT, "posts", slug, "index.html")
        if not os.path.exists(p):
            continue
        m = re.search(r'<div class="meta">.*?·\s*(搬运|原创)', open(p, encoding="utf-8").read())
        page_kind = {"搬运": "repost", "原创": "own"}.get(m.group(1) if m else "", "")
        if page_kind != kind:
            bad.append((slug, kind, page_kind or "?"))
    return bad


def check_dupes():
    """结构性重复注入（目录/浮动按钮/站名下拉）会让元素互相重叠，必须只有一份。"""
    bad = []
    for p in sorted(glob.glob(os.path.join(ROOT, "posts", "*", "index.html"))):
        s = open(p, encoding="utf-8").read()
        for name, pat in (("目录 nav.toc", r'<nav class="toc"'), ("目录按钮", r'class="toc-fab"'),
                          ("站名下拉", r'id="brandSet"'), ("回到顶部", r'id="backTop"')):
            n = len(re.findall(pat, s))
            if n > 1:
                bad.append((os.path.basename(os.path.dirname(p)), name, n))
    return bad


def check_css_stamp():
    """页面里 post.css?v= 必须等于文件真实内容哈希，否则浏览器会一直吃旧缓存。"""
    import hashlib
    css = os.path.join(ROOT, "assets", "post.css")
    if not os.path.exists(css):
        return []
    h = hashlib.sha1(open(css, "rb").read()).hexdigest()[:8]
    bad = []
    for p in sorted(glob.glob(os.path.join(ROOT, "posts", "*", "index.html"))):
        m = re.search(r"post\.css\?v=([0-9a-f]+)", open(p, encoding="utf-8").read())
        if not m or m.group(1) != h:
            bad.append((os.path.basename(os.path.dirname(p)), m.group(1) if m else "-"))
    return bad, h


def main():
    paths = sys.argv[1:] or sorted(glob.glob(os.path.join(ROOT, "posts", "*", "index.html")))
    total = {k: 0 for k in ("P0", "P1", "P2")}
    for p in paths:
        hits = check(p)
        if not hits:
            continue
        rel = os.path.relpath(p, ROOT)
        print("\n%s" % rel)
        for level, desc, seg in hits[:8]:
            total[level] += 1
            print("  [%s] %s\n       %s" % (level, desc, seg))
        if len(hits) > 8:
            print("  … 还有 %d 处" % (len(hits) - 8))
    stamp_bad, css_hash = check_css_stamp()
    if stamp_bad:
        print("\nCSS 版本戳过期（应为 %s，跑一次 add_toc.py）" % css_hash)
        for slug, v in stamp_bad[:5]:
            print("  [P0] %s：%s" % (slug, v))
        total["P0"] += len(stamp_bad)

    dupe_bad = check_dupes()
    if dupe_bad:
        print("\n重复注入（会互相重叠）")
        for slug, name, n in dupe_bad:
            print("  [P0] %s：%s 出现 %d 次" % (slug, name, n))
        total["P0"] += len(dupe_bad)

    kind_bad = check_kinds()
    if kind_bad:
        print("\n分类不一致（首页 data-kind ≠ 文章页 meta）")
        for slug, a, b in kind_bad:
            print("  [P1] %s：首页 %s / 页面 %s" % (slug, a, b))
        total["P1"] += len(kind_bad)

    print("\n汇总：P0=%d  P1=%d  P2=%d（共 %d 篇）"
          % (total["P0"], total["P1"], total["P2"], len(paths)))
    if total["P0"]:
        print("✗ 有 P0 问题，先修再上线")
        sys.exit(1)
    print("✓ 可以上线")


if __name__ == "__main__":
    main()
