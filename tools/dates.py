#!/usr/bin/env python3
"""日期解析：全站只此一份。

站点上的日期来自四个地方，写法并不统一：
  - vault 的 frontmatter：`published: 2026-10-31`（ISO）
  - sources.json：`"October 30, 2025"`（英文长格式）
  - 页面 meta：`2026年10月31日`（中文，文章页的展示串）
  - 老剪藏：`7月21日`（当年省略年份）

以前 gen_index / gen_feed / rebuild / md2post 各写一份，能力还各不相同
（有的不认「7月21日」、有的只认 ISO），改一处格式另外三处就会静默走兜底。
"""
import re
from datetime import date, datetime

MONTHS = {m: i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"], 1)}

EN_LONG = re.compile(r"([A-Za-z]+)\.?\s+(\d{1,2}),\s*(\d{4})")
CN_FULL = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日")
CN_SHORT = re.compile(r"(?<!\d)(\d{1,2})\s*月\s*(\d{1,2})\s*日")
ISO = re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})")


def to_date(value, today=None):
    """任意写法 → date；认不出来返回 None（由调用方决定兜底）。"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    s = str(value).strip()
    if not s:
        return None

    m = ISO.search(s)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = CN_FULL.search(s)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = EN_LONG.search(s)
    if m and m.group(1)[:3].capitalize() in {k[:3] for k in MONTHS}:
        mon = next(v for k, v in MONTHS.items() if k[:3] == m.group(1)[:3].capitalize())
        return date(int(m.group(3)), mon, int(m.group(2)))
    m = CN_SHORT.search(s)
    if m:
        year = (today or date.today()).year
        return date(year, int(m.group(1)), int(m.group(2)))
    return None


def to_iso(value, today=None):
    """→ `YYYY-MM-DD`；认不出来原样返回（调用方可能就想拿原文）。"""
    d = to_date(value, today)
    return d.isoformat() if d else (str(value).strip() if value else "")


def to_cn(value, today=None):
    """→ `2026年10月31日`（文章页 meta 的写法）。"""
    d = to_date(value, today)
    return "%d年%d月%d日" % (d.year, d.month, d.day) if d else ""


def short_cn(value, today=None):
    """→ `10月31日`；不是当年的补上年份。"""
    d = to_date(value, today)
    if not d:
        return str(value or "")
    base = "%d月%d日" % (d.month, d.day)
    return base if d.year == (today or date.today()).year else "%d年%s" % (d.year, base)
