#!/usr/bin/env python3
"""一键构建：从 vault 重建 → 目录 → 字数 → 首页 → 上下篇 → 相关阅读 → 搜索索引 → RSS → 回归测试
→ 资源版本号 → skill 同步与一致性 → 排版体检 →（可选）推送。

顺序（改这里就是改全站流程，文档一律指向本文件，不要再各写一份）：
  ① rebuild.py        可选，--rebuild 时从 vault 的 md 重生成全部文章（会改正文，慎用）
  ② add_toc.py        注入目录/站名下拉/回到顶部，剥旧标记（幂等）
  ③ stats.py          字数与阅读时间
  ④ gen_index.py      生成首页
  ④.2 gen_prevnext.py 上一篇 / 下一篇
  ④.25 gen_related.py 相关阅读（tf-idf 共词）
  ④.3 gen_search.py   生成 search.js（首页搜索只在点开时才加载）
  ④.5 gen_feed.py     feed.xml / sitemap.xml / robots.txt
  ⑤ test_pipeline.py  回归测试（幂等 + 注入唯一），失败即中止
  ⑥ stamp_assets.py   资源 ?v= 哈希
  ⑥.5 sync_skills()   仓库 skills/ → /var/minis/skills
  ⑥.8 check_skills.py skill 与代码一致性（脚本登记 / 引用 / 参数 / 副本）
  ⑦ qa.py             排版与内容体检，P0 不为 0 就中止（不会 push）
"""
import hashlib
import os
import re
import subprocess
import sys
import glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
ASSETS = ("assets/base.css", "assets/home.css", "assets/post.css", "assets/site.js")


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


SKILLS_SRC = os.path.join(ROOT, "skills")
import config  # noqa: E402

SKILLS_DST = config.load()["skills_dst"]


def sync_skills():
    """仓库 skills/ 是唯一源，单向同步到 /var/minis/skills/（本机没那个目录就跳过）。"""
    if not os.path.isdir(SKILLS_SRC) or not os.path.isdir(SKILLS_DST):
        return "跳过（无 skills 目录）"
    import shutil
    changed = 0
    for name in os.listdir(SKILLS_SRC):
        src = os.path.join(SKILLS_SRC, name)
        if not os.path.isdir(src):
            continue
        dst = os.path.join(SKILLS_DST, name)
        if os.path.isdir(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        changed += 1
    return "同步 %d 个 skill" % changed


def main():
    args = sys.argv[1:]
    do_rebuild = "--rebuild" in args
    do_push = "--push" in args

    if do_rebuild:
        print("① 从 vault 重建文章 …")
        print(sh("python3 tools/rebuild.py").strip().splitlines()[-1])

    print("② 注入目录 …")
    print(sh("python3 tools/add_toc.py").strip().splitlines()[-1])

    print("③ 字数与阅读时间 …")
    print(sh("python3 tools/stats.py").strip().splitlines()[-1])

    print("④ 生成首页 …")
    print(sh("python3 tools/gen_index.py").strip().splitlines()[0])

    print("④.2 上一篇 / 下一篇 …")
    print("   " + sh("python3 tools/gen_prevnext.py").strip())

    print("④.25 相关阅读 …")
    print("   " + sh("python3 tools/gen_related.py").strip())

    print("④.3 搜索索引 …")
    print("   " + sh("python3 tools/gen_search.py").strip())

    print("④.5 生成 RSS / sitemap …")
    print("   " + sh("python3 tools/gen_feed.py").strip())

    print("⑤ 回归测试 …")
    t = subprocess.run("python3 tools/test_pipeline.py", shell=True, cwd=ROOT,
                       capture_output=True, text=True)
    print("\n".join(t.stdout.strip().splitlines()[-3:]))
    if t.returncode != 0:
        print("\n✗ 回归测试未通过，已中止，不会 push。")
        raise SystemExit(1)

    print("⑥ 重算资源版本号 …")
    vs, n = stamp_assets()
    for k, v in vs.items():
        print("   %-18s %s" % (k, v))
    print("   更新了 %d 个页面" % n)

    print("⑥.5 同步 skills（仓库 → /var/minis）…")
    print("   " + sync_skills())

    print("⑥.8 skill 一致性 …")
    k = subprocess.run("python3 tools/check_skills.py", shell=True, cwd=ROOT,
                       capture_output=True, text=True)
    print("\n".join("   " + l for l in k.stdout.strip().splitlines()))
    if k.returncode != 0:
        print("\n✗ skill 与代码不一致，已中止，不会 push。")
        raise SystemExit(1)

    print("⑦ 排版体检 …")
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
        print("⑨ 推送 …")
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
