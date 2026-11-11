#!/usr/bin/env python3
"""开工对表：remote 是否正确、是否落后远端、工作区是否干净。

用法：python3 tools/preflight.py
输出最后一行是 clean 或 dirty（dirty 时非 0 退出）。
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WANT = "patrick12138/patrick12138.github.io"


def sh(cmd):
    p = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True)
    return p.returncode, (p.stdout + p.stderr).strip()


def main():
    problems = []

    rc, remote = sh("git remote -v")
    urls = [w for w in remote.replace("\n", " ").split() if "/" in w and w.startswith("http") or w.startswith("git@")]
    if WANT not in remote:
        problems.append("remote 不是 %s" % WANT)

    sh("git fetch origin")
    rc, counts = sh("git rev-list --left-right --count HEAD...origin/main")
    ahead, behind = (counts.split() + ["?", "?"])[:2] if counts else ("?", "?")
    if behind not in ("0", "?"):
        problems.append("落后远端 %s 个提交：git rebase origin/main" % behind)

    rc, st = sh("git status --porcelain")
    if st:
        n = len([l for l in st.split("\n") if l.strip()])
        problems.append("工作区有 %d 处未提交改动" % n)

    rc, head = sh("git log -1 --format=%h")
    print("HEAD %s  (ahead %s / behind %s)" % (head, ahead, behind))
    if problems:
        for p in problems:
            print("  ! " + p)
        print("dirty")
        return 1
    print("clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
