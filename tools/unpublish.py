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
PY = sys.executable   # Windows 没有 python3 命令，子进程统一用当前解释器
DEVNULL = ">%s" % os.devnull


def sh(cmd, check=False):
    p = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True)
    if check and p.returncode != 0:
        print(p.stdout, p.stderr)
        raise SystemExit("命令失败：" + cmd)
    return (p.stdout + p.stderr).strip()


def sh_out(cmd):
    """只要 stdout（解析 JSON / 提交号时用；sh() 会把 stderr 也拼进来）。"""
    p = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True)
    return p.stdout.strip()


def inbound_links(slug, skip_self=True):
    hits = []
    for p in __import__("glob").glob(os.path.join(ROOT, "posts", "*", "index.html")):
        other = os.path.basename(os.path.dirname(p))
        if skip_self and other == slug:
            continue
        s = open(p, encoding="utf-8").read()
        # 自动生成的上下篇/相关阅读每次 build 都会重算，不算“正文里的手工链接”
        s = re.sub(r'<nav class="pager".*?</nav>', '', s, flags=re.S)
        s = re.sub(r'<nav class="related".*?</nav>', '', s, flags=re.S)
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
    sh('"%s" tools/gen_index.py %s' % (PY, DEVNULL))
    sh('"%s" tools/gen_prevnext.py %s' % (PY, DEVNULL))
    sh('"%s" tools/gen_related.py && "%s" tools/gen_search.py && "%s" tools/gen_feed.py %s'
       % (PY, PY, PY, DEVNULL))
    print("✓ 已下线。接下来：tools/build.py 体检 → commit → push")
    print("  恢复：tools/unpublish.py %s --restore" % slug)


def restore(slug, dry=False):
    rows = json.load(open(SOURCES, encoding="utf-8"))
    if any(r["slug"] == slug for r in rows):
        raise SystemExit("sources.json 里已经有 %s，无需恢复" % slug)
    # 找最近一次包含它的提交（Windows cmd 无 head，取首行用纯 Python）
    commit = sh("git log --diff-filter=D --format=%%H -- posts/%s/index.html" % slug).strip().splitlines()[:1]
    if not commit:
        commit = sh("git log --format=%%H -- posts/%s/index.html" % slug).strip().splitlines()[:1]
    if not commit:
        raise SystemExit("git 历史里找不到 posts/%s/" % slug)
    commit = commit[0].strip()
    print("· 从 %s 恢复 posts/%s/" % (commit[:8] + "^", slug))
    if dry:
        return
    # commit 是「删除它的那次提交」，那一版里路径已不存在，必须从父提交取，
    # 否则 checkout 静默什么都不做（曾以为恢复了，其实没恢复）
    parent = commit + "^"
    sh("git checkout %s -- posts/%s" % (parent, slug))
    if not os.path.isdir(os.path.join(ROOT, "posts", slug)):
        raise SystemExit("恢复失败：%s 里没有 posts/%s/" % (parent[:8], slug))
    print("✓ 页面已恢复")

    # 顺手把 sources.json 的条目找回来：从「删除它的那次提交」的父版本里读
    try:
        raw = sh_out("git show %s:tools/sources.json" % parent)
        entry = next((r for r in json.loads(raw) if r.get("slug") == slug), None)
    except Exception:
        entry = None
    if entry:
        rows = json.load(open(SOURCES, encoding="utf-8"))
        if not any(r.get("slug") == slug for r in rows):
            rows.append(entry)
            rows.sort(key=lambda r: r.get("date", ""), reverse=True)
            with open(SOURCES, "w", encoding="utf-8") as f:
                json.dump(rows, f, ensure_ascii=False, indent=1)
                f.write("\n")
        print("  · sources.json 条目已自动补回：%s" % entry.get("md", "?"))
    else:
        print("  · sources.json 里没找到它的旧条目，需手动补：slug / md / author / date / kind")
    print("  下一步：python3 tools/build.py")


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
