#!/usr/bin/env python3
"""手动跑一遍「上线 → 下线 → 恢复」链路，断言每一步的产物都对。

为什么不放进 build.py：它要复制仓库、起临时 git、跑五次生成脚本，约 20 秒；
每次构建都跑太重。手动触发或者在 CI 里单独跑。

用法：
  python3 tools/test_flow.py           # 跑完删除临时目录
  python3 tools/test_flow.py --keep    # 保留 /tmp/flow-test-* 便于排查
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SLUG = "flow-test"
SKIP = {".git", "assets", "node_modules", "__pycache__"}
GIT = ["git", "-c", "user.email=test@local", "-c", "user.name=flow-test"]

fails = []


def ok(msg):
    print("  ✓ " + msg)


def bad(msg):
    print("  ✗ " + msg)
    fails.append(msg)


def run(args, cwd):
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if p.returncode != 0:
        print(p.stdout[-800:], p.stderr[-800:])
        raise SystemExit("命令失败：%s" % " ".join(args))
    return p.stdout + p.stderr


def copy_tree(dst):
    for name in os.listdir(ROOT):
        if name in SKIP:
            continue
        src = os.path.join(ROOT, name)
        tgt = os.path.join(dst, name)
        if os.path.isdir(src):
            shutil.copytree(src, tgt, ignore=shutil.ignore_patterns(*SKIP))
        else:
            shutil.copy2(src, tgt)


def has(path, needle):
    try:
        return needle in open(path, encoding="utf-8").read()
    except OSError:
        return False


def main():
    keep = "--keep" in sys.argv
    tmp = tempfile.mkdtemp(prefix="flow-test-")
    print("· 临时副本 %s" % tmp)
    try:
        copy_tree(tmp)
        run(["git", "init", "-q"], tmp)
        run(GIT + ["add", "-A"], tmp)
        run(GIT + ["commit", "-qm", "base"], tmp)

        md = os.path.join(tmp, "_flow_test.md")
        open(md, "w", encoding="utf-8").write(
            "---\ntitle: 流程测试（自动生成）\npublished: 2026-01-01\nkind: own\n---\n\n"
            "## 一句话结论\n\n这是一篇由 test_flow.py 生成的临时文章。\n\n"
            "## 第二节\n\n用于验证上线下线链路。\n")

        # ① 上线
        print("① md2post 上线一篇")
        run([sys.executable, "tools/md2post.py", md, SLUG, "--kind", "own", "--date", "2026-01-01"], tmp)
        ok("页面生成") if os.path.isdir(os.path.join(tmp, "posts", SLUG)) else bad("页面没生成")
        rows = json.load(open(os.path.join(tmp, "tools", "sources.json"), encoding="utf-8"))
        ok("sources.json 自动登记") if any(r["slug"] == SLUG for r in rows) else bad("sources.json 没登记")

        run(GIT + ["add", "-A"], tmp)
        run(GIT + ["commit", "-qm", "add"], tmp)

        # ② 下线
        print("② unpublish 下线")
        run([sys.executable, "tools/unpublish.py", SLUG], tmp)
        ok("页面目录已删除") if not os.path.isdir(os.path.join(tmp, "posts", SLUG)) else bad("页面目录还在")
        rows = json.load(open(os.path.join(tmp, "tools", "sources.json"), encoding="utf-8"))
        ok("sources.json 已移除") if not any(r["slug"] == SLUG for r in rows) else bad("sources.json 还有")
        for f in ("index.html", "search.js", "search-deep.js", "sitemap.xml", "feed.xml"):
            p = os.path.join(tmp, f)
            if os.path.exists(p) and has(p, SLUG):
                bad("%s 里还留着 %s" % (f, SLUG))
        ok("首页 / 搜索 / sitemap / feed 无残留")

        run(GIT + ["add", "-A"], tmp)
        run(GIT + ["commit", "-qm", "remove"], tmp)

        # ③ 恢复
        print("③ unpublish --restore 恢复")
        out = run([sys.executable, "tools/unpublish.py", SLUG, "--restore"], tmp)
        page_ok = os.path.isdir(os.path.join(tmp, "posts", SLUG))
        ok("页面目录已恢复") if page_ok else bad("页面目录没恢复 —— " + out.strip().splitlines()[-1])
        rows = json.load(open(os.path.join(tmp, "tools", "sources.json"), encoding="utf-8"))
        ok("sources.json 条目自动补回") if any(r["slug"] == SLUG for r in rows) else bad("sources.json 没补回")

        # ④ 恢复后重建，确认重新出现在列表与索引
        print("④ 重建并确认回到各处")
        run([sys.executable, "tools/gen_index.py"], tmp)
        run([sys.executable, "tools/gen_search.py"], tmp)
        for f in ("index.html", "search.js"):
            ok("%s 已包含 %s" % (f, SLUG)) if has(os.path.join(tmp, f), SLUG) else bad("%s 没包含 %s" % (f, SLUG))
    finally:
        if keep:
            print("· 保留临时目录：%s" % tmp)
        else:
            shutil.rmtree(tmp, ignore_errors=True)

    print()
    if fails:
        print("✗ 流程测试失败 %d 项" % len(fails))
        return 1
    print("✓ 上线 / 下线 / 恢复 全链路通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
