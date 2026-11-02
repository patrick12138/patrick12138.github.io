#!/usr/bin/env python3
"""正文边界：一个文档里「正文」到哪儿结束。

`.body` 之后挂着一串尾巴容器，它们都不算正文：
  <nav class="related">   相关阅读
  <nav class="pager">     上一篇 / 下一篇
  <aside class="legal-note">  搬运页版权提示
  <a class="back">        返回首页

这些块是**后插**的（②.5 / ④.2 / ④.25 各插一个），所以任何「截到第一个 </div>」
或「截到 <a class=back>」的写法都会随注入顺序变来变去。历史上因此出过三次事故：
字数虚高（把版权条算进正文）、搜索能搜到「版权/相关阅读」、版权提示每次 build 前后跳。

所有需要正文的脚本都从这里取，不要再各写一份截断标记。
"""
import html
import re

BODY_OPEN = '<div class="body"'
TAIL_MARKERS = ('<nav class="related"', '<nav class="pager"', '<aside class="legal-note"', '<a class="back"')


def body_span(doc):
    """返回 (start, end)：.body 开标签之后到最早出现的尾巴容器之前。找不到返回 (0, 0)。"""
    i = doc.find(BODY_OPEN)
    if i < 0:
        return (0, 0)
    start = doc.find(">", i) + 1
    if start <= 0:
        return (0, 0)
    ends = [doc.find(m, start) for m in TAIL_MARKERS]
    ends = [e for e in ends if e > start]
    return (start, min(ends) if ends else len(doc))


def body_html(doc):
    """正文的 HTML 片段（不含尾巴容器）。"""
    start, end = body_span(doc)
    return doc[start:end] if end > start else ""


def tail_start(doc):
    """尾巴区起点（版权提示、相关阅读、上下篇都插在它前面）。找不到返回 -1。"""
    start, end = body_span(doc)
    return end if end > start else -1


def text_of(doc):
    """正文纯文本：去标签、去 HTML 实体、压空白。"""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", body_html(doc)))).strip()


ROW_RE = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
CELL_RE = re.compile(r"<t[hd][^>]*>(.*?)</t[hd]>", re.S)


def table_rows(table_html):
    """表格 → [[单元格原始 HTML, ...], ...]（跳过空行）。wrap 与 qa 共用一份解析。"""
    rows = []
    for r in ROW_RE.findall(table_html):
        cells = CELL_RE.findall(r)
        if cells:
            rows.append(cells)
    return rows
