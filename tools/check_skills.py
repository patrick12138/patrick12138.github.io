#!/usr/bin/env python3
"""skill / 文档 与代码 的一致性检查。

每次 build 都会跑。检查项：
  1. 索引完整：tools/ 下每个脚本都要在 skill 文档或 AGENTS.md 里出现过
  2. 引用有效：文档里提到的 references/*.md、tools/*.py 必须真实存在
  3. 参数属实：文档里写的 `tools/X.py --flag` 必须真的被 X.py 支持
  4. skill 不臃肿：SKILL.md <= 100 行（细节进 references/）
  5. 已安装副本同步：~/.minis skills 与仓库 skills/ 完全一致
失败以非 0 退出，交给 build.py 拦下。
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
import config  # noqa: E402

INSTALLED = config.load()["skills_dst"]
MAX_SKILL_LINES = 100

problems = []
notes = []


def read(p):
    try:
        return open(p, encoding="utf-8").read()
    except OSError:
        return ""


def doc_files():
    """所有 skill 文档 + AGENTS.md：[(path, text)]"""
    out = []
    for base, _, files in os.walk(SKILLS):
        for f in files:
            if f.endswith(".md"):
                p = os.path.join(base, f)
                out.append((p, read(p)))
    ag = os.path.join(ROOT, "AGENTS.md")
    if os.path.exists(ag):
        out.append((ag, read(ag)))
    return out


def check_tools_documented(docs):
    blob = "\n".join(t for _, t in docs)
    for f in sorted(os.listdir(os.path.join(ROOT, "tools"))):
        if not f.endswith(".py") or f == "check_skills.py":
            continue
        name = f[:-3]
        if name not in blob:
            problems.append("tools/%s 没有任何文档提到它（skill 或 AGENTS.md）" % f)


def check_references_exist(docs):
    for path, text in docs:
        for m in re.finditer(r"references/([A-Za-z0-9._-]+\.md)", text):
            target = os.path.join(SKILLS, "github-pages-deploy", "references", m.group(1))
            if not os.path.exists(target):
                problems.append("%s 引用了不存在的 references/%s" % (os.path.relpath(path, ROOT), m.group(1)))


def check_flags(docs):
    """文档里的 `tools/x.py --flag` / `x.py --flag` 必须在源码里存在。"""
    seen = set()
    for _, text in docs:
        for m in re.finditer(r"([a-z0-9_]+)\.py((?:\s+--?[A-Za-z0-9_-]+(?:[ =][^\s`'\"）)]*)?)+)", text):
            script, args = m.group(1), m.group(2)
            src_path = os.path.join(ROOT, "tools", script + ".py")
            if not os.path.exists(src_path):
                continue
            src = read(src_path)
            for flag in re.findall(r"--[A-Za-z0-9_-]+", args):
                if flag in seen:
                    continue
                seen.add(flag)
                if flag not in src:
                    problems.append("%s 不支持文档里写的 %s" % ("tools/%s.py" % script, flag))


def check_skill_size(docs):
    sk = os.path.join(SKILLS, "github-pages-deploy", "SKILL.md")
    n = len(read(sk).splitlines())
    if n > MAX_SKILL_LINES:
        problems.append("SKILL.md 已 %d 行（上限 %d），细节该拆进 references/" % (n, MAX_SKILL_LINES))
    else:
        notes.append("SKILL.md %d 行" % n)


def check_installed_sync():
    if not os.path.isdir(INSTALLED):      # CI 上没有这个目录，跳过而不是判失败
        notes.append("跳过副本比对：%s 不存在" % INSTALLED)
        return
    for name in sorted(os.listdir(SKILLS)):
        src = os.path.join(SKILLS, name)
        dst = os.path.join(INSTALLED, name)
        if not os.path.isdir(src):
            continue
        if not os.path.isdir(dst):
            problems.append("skill %s 没安装到 %s（build.py 的 sync_skills 没跑？）" % (name, INSTALLED))
            continue
        for base, _, files in os.walk(src):
            for f in files:
                a = os.path.join(base, f)
                b = os.path.join(dst, os.path.relpath(a, src))
                if not os.path.exists(b):
                    problems.append("%s 缺文件：%s" % (name, os.path.relpath(a, src)))
                elif read(a) != read(b):
                    problems.append("%s 内容不同步：%s" % (name, os.path.relpath(a, src)))


def main():
    docs = doc_files()
    if not docs:
        problems.append("找不到任何 skill 文档")
    check_tools_documented(docs)
    check_references_exist(docs)
    check_flags(docs)
    check_skill_size(docs)
    check_installed_sync()

    for n in notes:
        print("  · " + n)
    if problems:
        print("\nskill 检查：%d 个问题" % len(problems))
        for p in problems[:20]:
            print("  [x] " + p)
        return 1
    print("✓ skill 与代码一致")
    return 0


if __name__ == "__main__":
    sys.exit(main())
