#!/usr/bin/env python3
"""一条命令构建整站。

用法：
  python3 tools/build.py              # 重算资源版本 → 生成首页 → 排版体检
  python3 tools/build.py --rebuild    # 另外先从 vault 重建全部文章（慢，约 1-2 分钟）
  python3 tools/build.py --push       # 构建完顺便 commit + push

顺序固定，不要改：
  1. (可选) rebuild.py     从 vault 的 md 重新生成所有文章
  2. gen_index.py          扫描 posts/ 生成首页
  3. stamp_assets()        给 home.css / post.css / site.js 写内容哈希
  4. qa.py                 排版体检，P0 不为 0 就中止（不会 push）
"""
import hashlib
import os
import re
import subprocess
import sys
import glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
ASSETS = ("assets/home.css", "assets/post.css", "assets/site.js")


def sh(cmd, check=True):
    p = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True)
    if p.returncode != 0 and check:
        print(p.stdout[-2000:])
        print(p.stderr[-2000:])
        raise SystemExit("命令失败：" + cmd)
    return p.stdout


def stamp_assets():
    """按内容哈希重写所有页面里的 ?v=，内容不变时不动文件。"""
    vs = {}
    for rel in ASSETS:
        path = os.path.join(ROOT, rel)
        vs[rel] = hashlib.sha1(open(path, "rb").read()).hexdigest()[:8]

    files = (glob.glob(os.path.join(ROOT, "*.html"))
             + glob.glob(os.path.join(ROOT, "*", "index.html"))
             + glob.glob(os.path.join(ROOT, "posts", "*", "index.html")))
    changed = 0
    for path in files:
        s = open(path, encoding="utf-8").read()
        o = s
        for rel, v in vs.items():
            base = os.path.basename(rel)
            s = re.sub(r'(href="[^"]*%s)(\?v=[^"]*)?"' % re.escape(base),
                       r'\1?v=%s"' % v, s)
            s = re.sub(r'(src="[^"]*%s)(\?v=[^"]*)?"' % re.escape(base),
                       r'\1?v=%s"' % v, s)
        if s != o:
            open(path, "w", encoding="utf-8").write(s)
            changed += 1
    return vs, changed


def main():
    args = sys.argv[1:]
    do_rebuild = "--rebuild" in args
    do_push = "--push" in args

    if do_rebuild:
        print("① 从 vault 重建文章 …")
        print(sh("python3 tools/rebuild.py").strip().splitlines()[-1])

    print("② 生成首页 …")
    print(sh("python3 tools/gen_index.py").strip().splitlines()[0])

    print("③ 重算资源版本号 …")
    vs, n = stamp_assets()
    for k, v in vs.items():
        print("   %-18s %s" % (k, v))
    print("   更新了 %d 个页面" % n)

    print("④ 排版体检 …")
    p = subprocess.run("python3 tools/qa.py", shell=True, cwd=ROOT,
                       capture_output=True, text=True)
    tail = "\n".join(p.stdout.strip().splitlines()[-6:])
    print(tail)
    if p.returncode != 0:
        print("\n✗ qa 未通过（P0 不为 0），已中止，不会 push。")
        raise SystemExit(1)

    print("\n✓ 构建完成")

    if do_push:
        msg = args[args.index("--push") + 1] if len(args) > args.index("--push") + 1 else "chore: rebuild site"
        print("⑤ 推送 …")
        sh('git add -A && git commit -m "%s" || true' % msg, check=False)
        sh('git remote set-url origin "https://x-access-token:$GITHUB_TOKEN@github.com/patrick12138/patrick12138.github.io.git"')
        r = subprocess.run("git pull --rebase origin main && git push origin main",
                           shell=True, cwd=ROOT, capture_output=True, text=True)
        sh('git remote set-url origin https://github.com/patrick12138/patrick12138.github.io.git')
        print((r.stdout + r.stderr).strip().splitlines()[-2:])
        if r.returncode != 0:
            print("✗ push 失败（可能有冲突），remote 已还原")
            raise SystemExit(1)
        print("✓ 已推送，Pages 约 30–60 秒后生效")


if __name__ == "__main__":
    main()
