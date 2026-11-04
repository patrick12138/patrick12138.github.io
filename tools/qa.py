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
import postbody
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
    return postbody.body_html(s)


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
    """首页 data-kind 与文章页 meta 的「搬运/个人」必须一致。"""
    idx = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    kinds = dict(re.findall(r'<li data-kind="(\w+)"><a href="posts/([a-z0-9-]+)/"', idx))
    kinds = {slug: kind for kind, slug in kinds.items()}
    bad = []
    for slug, kind in kinds.items():
        p = os.path.join(ROOT, "posts", slug, "index.html")
        if not os.path.exists(p):
            continue
        m = re.search(r'<div class="meta">.*?·\s*(搬运|个人|原创)', open(p, encoding="utf-8").read())
        page_kind = {"搬运": "repost", "个人": "own", "原创": "own"}.get(m.group(1) if m else "", "")
        if page_kind != kind:
            bad.append((slug, kind, page_kind or "?"))
    return bad


def check_dupes():
    """结构性重复注入（目录/浮动按钮/站名下拉）会让元素互相重叠，必须只有一份。"""
    bad = []
    for p in sorted(glob.glob(os.path.join(ROOT, "posts", "*", "index.html"))):
        s = open(p, encoding="utf-8").read()
        for name, pat in (("目录 nav.toc", r'<nav class="toc"'), ("目录按钮", r'class="toc-fab"'),
                          ("站名下拉", r'id="brandSet"'), ("回到顶部", r'id="toTop"'),
                          ("沉浸阅读按钮", r'id="readOpen"'), ("文末出口", r'id="readExit"')):
            n = len(re.findall(pat, s))
            if n > 1:
                bad.append((os.path.basename(os.path.dirname(p)), name, n))
    return bad


def check_css_stamp():
    """页面里所有 assets/*.css?v= 必须等于文件真实内容哈希，否则浏览器会一直吃旧缓存。"""
    import hashlib
    files = {}
    for name in ("base.css", "home.css", "post.css", "site.js", "home.js", "post.js"):
        f = os.path.join(ROOT, "assets", name)
        if os.path.exists(f):
            files[name] = hashlib.sha1(open(f, "rb").read()).hexdigest()[:8]
    bad = []
    pages = (glob.glob(os.path.join(ROOT, "*.html"))
             + glob.glob(os.path.join(ROOT, "posts", "*", "index.html"))
             + glob.glob(os.path.join(ROOT, "*", "index.html")))
    for p in pages:
        s = open(p, encoding="utf-8").read()
        for name, h in files.items():
            m = re.search(r"%s\?v=([0-9a-f]+)" % re.escape(name), s)
            if m and m.group(1) != h:
                bad.append((os.path.basename(os.path.dirname(p)) or "index", name, m.group(1)))
            elif not m and ("assets/%s" % name) in s:
                bad.append((os.path.basename(os.path.dirname(p)) or "index", name, "无版本号"))
    return bad, files


def check_page_shell():
    """每个页面要么自带 <style>，要么必须引 base.css —— 拆分样式后 lab 就是这样丢样式的外壳。"""
    bad = []
    pages = (glob.glob(os.path.join(ROOT, "*.html"))
             + glob.glob(os.path.join(ROOT, "*", "index.html"))
             + glob.glob(os.path.join(ROOT, "posts", "*", "index.html"))
             + glob.glob(os.path.join(ROOT, "*", "index.html")))
    for p in pages:
        s = open(p, encoding="utf-8").read()
        if "<style" in s or "base.css" in s:
            continue
        bad.append(os.path.relpath(p, ROOT))
    return bad


def check_descriptions():
    """首页摘要质量：太短、或是把正文/站点口号当摘要的，都算不合格。"""
    idx = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    items = re.findall(r'<h2>(.*?)</h2><p class="desc">(.*?)</p>', idx, re.S)
    bad = []
    for title, desc in items:
        d = desc.strip()
        if len(d) < 20 or re.search(r"记录时间|^June \d{4}|blog$|^作者：", d):
            bad.append((re.sub(r"<[^>]+>", "", title)[:24], d[:36]))
    return bad


# 上线前必须过一遍的脱敏清单：前公司名、证件、联系方式、内网地址、密钥
PRIVACY_HARD = [
    ("前公司/客户名", r"合地|保信|华钦|CLPS|富卫|FWD"),
    ("证件/银行卡", r"身份证|银行卡|社保号"),
    ("手机号", r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    ("内网地址", r"\b(?:192\.168|10\.|172\.(?:1[6-9]|2\d|3[01]))\.\d+\.\d+"),
    ("疑似密钥", r"sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}"),
]
PRIVACY_SOFT = [
    ("邮箱（搬运原文里的公开联系方式，确认无隐私即可）", r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    ("求职痕迹", r"求职|面试话术|内推"),
    ("薪资数字", r"月薪\s*\d|年薪\s*\d|工资\s*\d"),
]


def check_tables():
    """表格的可读性：列太多、单元格太长、没有表头，都属于该改内容而不是改样式。"""
    bad = []
    for p in sorted(glob.glob(os.path.join(ROOT, "posts", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        doc = open(p, encoding="utf-8").read()
        for ti, tbl in enumerate(re.findall(r"<table.*?</table>", doc, flags=re.S), 1):
            cells = postbody.table_rows(tbl)
            if not cells:
                continue
            ncol = max(len(c) for c in cells)
            if ncol > 6:
                bad.append((slug, "表格%d 有 %d 列，手机横滑会很累" % (ti, ncol), "P1"))
            if "<th" not in tbl:
                bad.append((slug, "表格%d 没有表头" % ti, "P2"))
            for c in cells:
                for cell in c:
                    txt = re.sub(r"<[^>]+>", "", cell).strip()
                    if len(txt) > 90:
                        bad.append((slug, "表格%d 有 %d 字的单元格" % (ti, len(txt)), "P1"))
                        break
    return bad


def check_placeholders():
    """生成物里不得残留 {{XXX}}：模板加了新占位符但 md2post 忘了替换时，会原样上线。"""
    bad = []
    for p in sorted(glob.glob(os.path.join(ROOT, "posts", "*", "index.html"))):
        s = open(p, encoding="utf-8").read()
        left = set(re.findall(r"\{\{[A-Z_]+\}\}", s))
        if left:
            bad.append((os.path.basename(os.path.dirname(p)), " ".join(sorted(left))))
    return bad


def check_md_leak():
    """markdown 链接残渣：](http / 独立成段的 [ / ]( —— 微信或爬虫抓正文常留这些。"""
    bad = []
    pats = [(r"\]\(https?:", "markdown 链接残渣 ](http"),
            (r"(?m)^\s*\[\s*$", "孤立的一行 ["),
            (r"(?m)^\s*\]\([^)]*\)?\s*$", "孤立的一行 ](...)")]
    for p in sorted(glob.glob(os.path.join(ROOT, "posts", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        text = re.sub(r"<[^>]+>", " ", body_of(open(p, encoding="utf-8").read()))
        for pat, name in pats:
            if re.search(pat, text):
                bad.append((slug, name))
    return bad


def check_privacy():
    """P0：前公司名/证件/联系方式/内网/密钥；P1：求职痕迹、薪资。"""
    hard, soft = [], []
    for p in sorted(glob.glob(os.path.join(ROOT, "posts", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(p))
        s = open(p, encoding="utf-8").read()
        body = body_of(s)
        text = re.sub(r"<[^>]+>", " ", body)
        for name, pat in PRIVACY_HARD:
            for m in re.finditer(pat, text):
                hard.append((slug, name, text[max(0, m.start() - 20):m.start() + 24].strip()))
        for name, pat in PRIVACY_SOFT:
            for m in re.finditer(pat, text):
                soft.append((slug, name, text[max(0, m.start() - 16):m.start() + 20].strip()))
    return hard, soft


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
    tbad = check_tables()
    if tbad:
        print("\n表格可读性")
        for slug, msg, lvl in tbad[:6]:
            print("  [%s] %s · %s" % (lvl, slug, msg))
            total[lvl] += 1

    ph = check_placeholders()
    if ph:
        print("\n生成物里的模板占位符（P0）")
        for slug, left in ph[:8]:
            print("  [P0] %s · %s" % (slug, left))
        total["P0"] += len(ph)

    leak = check_md_leak()
    if leak:
        print("\n正文里的 markdown 残渣（P0）")
        for slug, name in leak[:8]:
            print("  [P0] %s · %s" % (slug, name))
        total["P0"] += len(leak)

    hard, soft = check_privacy()
    if hard:
        print("\n脱敏：必须处理的内容（P0）")
        for slug, name, ctx in hard[:8]:
            print("  [P0] %s · %s → %s" % (slug, name, ctx))
        total["P0"] += len(hard)
    if soft:
        print("\n脱敏：建议处理（P1）")
        for slug, name, ctx in soft[:5]:
            print("  [P1] %s · %s → %s" % (slug, name, ctx))
        total["P1"] += len(soft)

    desc_bad = check_descriptions()
    if desc_bad:
        print("\n首页摘要不合格（太短 / 把正文或口号当摘要）")
        for t, d in desc_bad:
            print("  [P1] %s → %s" % (t, d))
        total["P1"] += len(desc_bad)

    shell_bad = check_page_shell()
    if shell_bad:
        print("\n这些页面既没有内联 <style> 也没引 base.css（会丢外壳样式）")
        for p in shell_bad:
            print("  [P0] %s" % p)
        total["P0"] += len(shell_bad)

    stamp_bad, css_hash = check_css_stamp()
    if stamp_bad:
        print("\nCSS 版本戳过期（应为 %s，跑一次 build.py）" % " / ".join("%s=%s" % kv for kv in css_hash.items()))
        for slug, name, v in stamp_bad[:5]:
            print("  [P0] %s：%s?v=%s" % (slug, name, v))
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
