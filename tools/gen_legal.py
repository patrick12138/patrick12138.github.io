#!/usr/bin/env python3
"""给「搬运」文章补版权信号：canonical 指向原文、noindex、文末版权提示。

为什么：全文搬运 + 署名 + 链接 **不等于** 授权。署名只解决署名权，复制权/信息网络
传播权那一项仍在。canonical 在技术上讲「正本在原文那边」，noindex 让搬运页不与原文
抢搜索位，两者一起把「替代原作、损害市场」这个论点削掉；文末提示给出真实的删除通道。

只处理 kind=repost 的页面；原创页会被剥干净（把一篇从 repost 改成 own 后自动收敛）。

可重复执行：先按 `data-legal` 签名剥旧标记，再重算，跑两遍字节一致。

用法：python3 tools/gen_legal.py            # 注入
      python3 tools/gen_legal.py --check    # 只体检，不写（有问题非 0 退出）
"""
import glob
import os
import re
import postbody
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 与 about 页的联系方式保持一致（https://patrick12138.github.io/about/）。
# 这里只放一个超链接，不再写 Telegram 全称：技术上看，读者只需要知道「点这里能找到我」。
CONTACT = "https://t.me/patrick12138"

# 搬运页要不要退出搜索引擎收录。改 False 就只留 canonical，保留搜索流量。
NOINDEX = True

META = re.compile(r'<div class="meta">(.*?)</div>', re.S)
SRC_URL = re.compile(r'<a class="src-url" href="([^"]+)"')
ANCHOR_HEAD = re.compile(r'(<meta property="og:url"[^>]*>)')
# 插入点：正文结束处（第一个尾巴容器之前）。统一由 tools/postbody.py 判定，
# 不再自己写一份截断标记——相关阅读/上下篇都在本脚本之后才插。

NOTE = (
    '<aside class="legal-note" data-legal="1">'
    '<span class="legal-text">本文版权归原作者与译者所有，全文搬运仅供检索与离线阅读。</span>'
    '<a class="legal-link" href="%s" rel="noopener">不希望被转载？联系我删除</a>'
    "</aside>\n" % CONTACT
)


def strip_legal(doc):
    """剥掉上一次注入的三样东西（只认自己的 data-legal 签名）。"""
    doc = re.sub(r'\s*<(?:link|meta) [^>]*data-legal="1"[^>]*>', "", doc)
    doc = re.sub(r'<aside class="legal-note" data-legal="1">.*?</aside>\s*', "", doc, flags=re.S)
    return doc


def apply_one(path, dry=False):
    doc = open(path, encoding="utf-8").read()
    original = doc
    doc = strip_legal(doc)

    meta = META.search(doc)
    is_repost = bool(meta) and "搬运" in meta.group(1)
    src = SRC_URL.search(doc)
    url = src.group(1) if src else ""

    if is_repost and url:
        head = ""
        if not re.search(r'<link rel="canonical"', doc):
            head += '<link rel="canonical" href="%s" data-legal="1">' % url
        if NOINDEX and not re.search(r'<meta name="robots"', doc):
            head += '<meta name="robots" content="noindex,follow" data-legal="1">'
        if head:
            doc = ANCHOR_HEAD.sub(lambda m: m.group(1) + head, doc, count=1)
        pos = postbody.tail_start(doc)
        if pos > 0:
            doc = doc[:pos] + NOTE + doc[pos:]
        else:
            print("  ! 找不到正文尾巴锚点，跳过版权提示：%s" % os.path.relpath(path, ROOT))

    if doc == original:
        return False
    if not dry:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(doc)
    return True


def check():
    """体检：搬运页三样齐、原创页一样都不许有。"""
    problems = []
    reposts = 0
    for path in sorted(glob.glob(os.path.join(ROOT, "posts", "*", "index.html"))):
        slug = os.path.basename(os.path.dirname(path))
        doc = open(path, encoding="utf-8").read()
        meta = META.search(doc)
        is_repost = bool(meta) and "搬运" in meta.group(1)
        has_note = '<aside class="legal-note"' in doc
        has_canon = '<link rel="canonical"' in doc
        has_src = bool(SRC_URL.search(doc))
        if is_repost:
            reposts += 1
            if not has_src:
                problems.append("[P1] %s 标了搬运但没有 src-url，无法指回原文" % slug)
            elif not has_canon:
                problems.append("[P1] %s 搬运页缺 canonical" % slug)
            elif not has_note:
                problems.append("[P1] %s 搬运页缺版权提示" % slug)
        elif has_note or has_canon:
            problems.append("[P2] %s 不是搬运页，却带着版权标记" % slug)
        if has_note and '<nav class="related"' in doc:
            if doc.index('class="legal-note"') > doc.index('class="related"'):
                problems.append("[P1] %s 版权提示跑到相关阅读后面了（位置不幂等）" % slug)
    print("  搬运页 %d 篇 · 问题 %d 条" % (reposts, len(problems)))
    for p in problems:
        print("   " + p)
    return problems


def main():
    dry = "--dry" in sys.argv
    if "--check" in sys.argv:
        return 1 if check() else 0
    changed = 0
    for path in sorted(glob.glob(os.path.join(ROOT, "posts", "*", "index.html"))):
        if apply_one(path, dry=dry):
            changed += 1
    print("  版权信号：更新 %d 篇" % changed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
