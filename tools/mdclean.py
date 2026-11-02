"""剪藏 md 的清洗管线：front matter 解析、双链剥离、排版修补。

纯文本变换，无 IO 副作用；md2post.build() 按序调用。
"""
import re

import yaml

WIKI = re.compile(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]")


# ─── md 解析 ───────────────────────────────────────────────
def split_front(text):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return {}, text
    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        meta = {}
    return meta, text[m.end():]


def unwiki(s):
    return WIKI.sub(lambda m: (m.group(2) or m.group(1)).split("/")[-1], str(s))


def clean_author(v):
    if not v:
        return ""
    if isinstance(v, (list, tuple)):
        return "、".join([p for p in (clean_author(x) for x in v) if p])
    return unwiki(v).strip()


def norm(s):
    return re.sub(r"\s+", "", unwiki(s))


def strip_title_heading(body, title):
    lines = body.split("\n")
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i < len(lines):
        m = re.match(r"^#{1,3}\s+(.+)$", lines[i].strip())
        if m and norm(m.group(1)) == norm(title):
            lines = lines[:i] + lines[i + 1:]
    return "\n".join(lines)


def pull_source_block(body):
    """把开头的“来源：”段落（可能是紧跟的列表）抽出来，返回 (来源文本, 去掉它的正文)。"""
    lines = body.split("\n")
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i >= len(lines) or not re.match(r"^(来源|Source)[:：]", lines[i].strip(), re.I):
        return "", body
    j = i + 1
    chunk = [lines[i]]
    while j < len(lines):
        s = lines[j].strip()
        if not s:
            j += 1
            continue
        if re.match(r"^[-*+]\s+", s) or s.startswith("[["):
            chunk.append(s)
            j += 1
            continue
        break
    items = []
    for ln in chunk:
        s = re.sub(r"^\s*[-*+]\s+", "", ln.strip())
        s = re.sub(r"^(来源|Source)[:：]\s*", "", s, flags=re.I)
        if s:
            items.append(s)
    text = " · ".join(items)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)   # 链接只留文字
    text = unwiki(text).replace("[[", "").replace("]]", "")
    text = re.sub(r"\s*·\s*·\s*", " · ", text)
    return re.sub(r"\s{2,}", " ", text).strip(), "\n".join(lines[:i] + lines[j:])


def strip_empty_svg(body):
    """删掉「空 path + textPath」的装饰 SVG：渲染不出内容，却白占 200px 高度。"""
    import re as _re

    def repl(m):
        svg = m.group(0)
        if _re.search(r'<path[^>]*id="[^"]*"[^>]*>\s*</path>', svg) and '<textPath' in svg:
            return ""
        return svg

    body = _re.sub(r"<svg\b[^>]*>.*?</svg>", repl, body, flags=_re.S)
    body = _re.sub(r"<p[^>]*>\s*</p>", "", body)
    return body


def video_to_link(body):
    """内嵌 <video> 改成外链文字，不做播放器。"""
    import re as _re

    def repl(m):
        m2 = _re.search(r'src="([^"]+)"', m.group(0))
        if not m2:
            return ""
        return '\n\n[观看视频 →](%s)\n\n' % m2.group(1)

    body = _re.sub(r"<video[^>]*>.*?</video>|<video[^>]*/?>", repl, body, flags=_re.S)
    body = _re.sub(r"<iframe[^>]*src=\"([^\"]+)\"[^>]*>.*?</iframe>", r"\n\n[打开嵌入内容 →](\1)\n\n", body, flags=_re.S)
    return body


def normalize_md(body):
    body = strip_empty_svg(body)
    body = video_to_link(body)
    """剪藏 md 的排版修补：反转义、给标题/列表补空行（跳过代码块）。"""
    body = body.replace("\r\n", "\n")
    body = re.sub(r"\\([`*_\[\]#()!+])", r"\1", body)
    out, fence = [], False
    for ln in body.split("\n"):
        st = ln.strip()
        if st.startswith("```") or st.startswith("~~~"):
            fence = not fence
            out.append(ln)
            continue
        if fence:
            out.append(ln)
            continue
        glued = re.search(r"(?<=[^\s|])(#{2,6}\s+\S)", ln)
        if glued and not st.startswith("#"):
            out.append("")
            ln = ln[:glued.start(1)] + "\n\n" + ln[glued.start(1):]
            st = ln.strip()
        is_head = re.match(r"^#{1,6}\s+\S", st)
        is_item = re.match(r"^([-*+]|\d+\.)\s+\S", st)
        if (is_head or is_item) and out:
            prev = out[-1]
            ps = prev.strip()
            if (ps and not re.match(r"^([-*+]|\d+\.)\s+", ps)
                    and not re.match(r"^#{1,6}\s", ps) and not ps.startswith("|")
                    and not prev.startswith("    ") and not ps.endswith("|")):
                out.append("")
        out.append(ln)
    return "\n".join(out)


def strip_clip_junk(body):
    out = []
    for line in body.split("\n"):
        s = line.strip()
        if re.match(r"^\[See all posts\]\(.*\)$", s):
            continue
        if re.match(r"^\[回到顶部\]", s):
            continue
        if s in ("本文由作者授权发布", "原文链接"):
            continue
        out.append(line)
    body = "\n".join(out)
    body = re.sub(r"(?m)^#{1,4}\s*(目录|目錄|Table of Contents)\s*\n(?=\s*(#{1,4}\s|\Z))", "", body)
    return body


def first_paragraph(body, limit=120):
    for block in re.split(r"\n\s*\n", body):
        b = block.strip()
        if not b or b.startswith("#") or b.startswith("|") or b.startswith("!["):
            continue
        b = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", b)
        b = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", b)
        b = re.sub(r"^[->*\s]+", "", b)
        b = unwiki(b).replace("**", "").replace("`", "")
        b = re.sub(r"\s+", "", b) if re.search(r"[\u4e00-\u9fff]", b) else re.sub(r"\s+", " ", b)
        if len(b) < 8:
            continue
        return b if len(b) <= limit else b[:limit].rstrip("，、, ") + "…"
    return ""
