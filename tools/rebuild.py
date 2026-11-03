#!/usr/bin/env python3
"""按 tools/sources.json 重新生成所有文章页，然后统一注入目录。

用法：
  python3 tools/rebuild.py            # 全部重建
  python3 tools/rebuild.py slug1 slug2 # 只重建指定 slug
"""
import json
import os
import re
import dates
import sys
from datetime import datetime

def iso(d):
    """英文长日期 → ISO；认不出来原样返回。解析逻辑在 tools/dates.py。"""
    return dates.to_iso(d)


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import add_toc  # noqa: E402
import config  # noqa: E402
import md2post  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VAULT = config.load()["vault_root"]


def main():
    only = set(sys.argv[1:])
    rows = json.load(open(os.path.join(ROOT, "tools", "sources.json"), encoding="utf-8"))
    done, skipped = 0, []
    for r in rows:
        if only and r["slug"] not in only:
            continue
        md = os.path.join(VAULT, r["md"]) if r.get("md") else ""
        if not md or not os.path.exists(md):
            skipped.append(r["slug"])
            continue
        print("· %s" % r["slug"])
        md2post.build(md, r["slug"], date_arg=iso(r.get("date")), author_arg=r.get("author"),
                      kind=r.get("kind", "repost"), images=True,
                      desc_arg=r.get("desc"),
                      title_arg=r.get("title") or None)
        done += 1
    print("重建 %d 篇，跳过 %d 篇 %s" % (done, len(skipped), skipped or ""))
    saved, sys.argv = sys.argv, sys.argv[:1]   # add_toc 会读 argv，别把 slug 当成文件路径
    try:
        add_toc.main()
    finally:
        sys.argv = saved


if __name__ == "__main__":
    main()
