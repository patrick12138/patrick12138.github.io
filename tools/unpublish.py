#!/usr/bin/env python3
"""下线 / 恢复一篇文章。

下线：
  python3 tools/unpublish.py <slug>            # 摘掉页面 + 从 sources.json 移除 + 重生成列表
  python3 tools/unpublish.py <slug> --dry      # 只报告会发生什么，不动文件

恢复：
  python3 tools/unpublish.py <slug> --restore  # 从 git 历史里取回页面并重新登记

设计取舍：
- **页面用 git rm 删掉**，不是移到某个目录——历史里留着，随时能 checkout 回来，
  也不会在站点上留下可被猜到的 URL。
- 只删「列表、feed、上下篇」里的入口，其余文章里指向它的正文链接会被列出来，人工决定改不改。
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = os.path.join(ROOT, "tools", "sources.json")


def sh(cmd, check=False):
    p = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True)
    if check and p.returncode != 0:
        print(p.stdout, p.stderr)
        raise SystemExit("命令失败：" + cmd)
    return (p.stdout + p.stderr).strip()


def inbound_links(slug, skip_self=True):
    hits = []
    for p in __import__("glob").glob(os.path.join(ROOT, "posts", "*", "index.html")):
        other = os.path.basename(os.path.dirname(p))
        if skip_self and other == slug:
            continue
        s = open(p, encoding="utf-8").read()
        if "posts/%s/" % slug in s or "../%s/" % slug in s:
            hits.append(other)
    return hits


def unpublish(slug, dry=False):
    page = os.path.join(ROOT, "posts", slug)
    if not os.path.isdir(page):
        raise SystemExit("找不到文章：posts/%s/" % slug)

    rows = json.load(open(SOURCES, encoding="utf-8"))
    entry = next((r for r in rows if r["slug"] == slug), None)

    print("· 下线 %s" % slug)
    print("  · 页面目录：posts/%s/（git rm，历史可恢复）" % slug)
    print("  · sources.json：%s" % ("有这一条，将移除" if entry else "没有这一条"))
    refs = inbound_links(slug)
    print("  · 其他文章里的引用：%s" % (", ".join(refs) if refs else "无"))
    if dry:
        print("  (dry run，未改动任何文件)")
        return

    sh("git rm -r -q posts/%s" % slug)
    if entry:
        rows = [r for r in rows if r["slug"] != slug]
        json.dump(rows, open(SOURCES, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    sh("python3 tools/gen_index.py >/dev/null")
    sh("python3 tools/gen_prevnext.py >/dev/null")
    sh("python3 tools/gen_feed.py >/dev/null")
    print("✓ 已下线。接下来：python3 tools/build.py 体检 → commit → push")
    print("  恢复：python3 tools/unpublish.py %s --restore" % slug)


def restore(slug, dry=False):
    rows = json.load(open(SOURCES, encoding="utf-8"))
    if any(r["slug"] == slug for r in rows):
        raise SystemExit("sources.json 里已经有 %s，无需恢复" % slug)
    # 找最近一次包含它的提交
    commit = sh("git log --diff-filter=D --format=%%H -- posts/%s/index.html | head -1" % slug)
    if not commit:
        commit = sh("git log --format=%%H -- posts/%s/index.html | head -1" % slug)
    if not commit:
        raise SystemExit("git 历史里找不到 posts/%s/" % slug)
    print("· 从 %s 恢复 posts/%s/" % (commit[:8], slug))
    if dry:
        return
    sh("git checkout %s -- posts/%s" % (commit, slug))
    print("✓ 页面已恢复。sources.json 需要手动补回这一条（作者/日期/kind），然后 build.py")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        print(__doc__)
        raise SystemExit(1)
    slug = args[0]
    if "--restore" in sys.argv:
        restore(slug, "--dry" in sys.argv)
    else:
        unpublish(slug, "--dry" in sys.argv)


if __name__ == "__main__":
    main()
