#!/usr/bin/env python3
"""回归测试：三条黄金用例，挡住「改了看不见」的坑。

  1. md2post 幂等    同一篇 md 连转两次，输出字节一致
  2. add_toc 幂等    同一页连处理两次，输出一致且注入标记各只有 1 份
  3. gen_index 稳定  连生成两次首页，字节一致

用法：python3 tools/test_pipeline.py
"""
import hashlib
import glob
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import config  # noqa: E402

VAULT = config.load()["vault_root"]
FAILED = []


def md5(path):
    return hashlib.md5(open(path, "rb").read()).hexdigest()


def check(name, ok, detail=""):
    print(("  ✓ " if ok else "  ✗ ") + name + ("" if ok else "  " + detail))
    if not ok:
        FAILED.append(name)


def md2post_idempotent():
    src = os.path.join(VAULT, "Resources", "AI 疲劳与可持续使用.md")
    if not os.path.exists(src):
        print("  · 跳过 md2post（vault 不在本机）")
        return
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import md2post
    out = os.path.join(ROOT, "posts", "ai-fatigue", "index.html")
    if not os.path.exists(out):
        print("  · 跳过 md2post（样本页不存在）")
        return
    old_content = open(out, "rb").read()
    reg = os.path.join(ROOT, "tools", "sources.json")
    old_reg = open(reg, "rb").read() if os.path.exists(reg) else None
    import contextlib, io
    with contextlib.redirect_stdout(io.StringIO()):
        md2post.build(src, "ai-fatigue", kind="own")
        a = md5(out)
        md2post.build(src, "ai-fatigue", kind="own")
        b = md5(out)
    open(out, "wb").write(old_content)  # 还原现场，避免冲掉 TOC 与 stats
    if old_reg is not None:              # 登记表也是副产物，必须还原
        open(reg, "wb").write(old_reg)
    check("md2post 幂等（同一篇连转两次字节一致）", a == b, "%s != %s" % (a, b))


def add_toc_idempotent():
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import add_toc
    sample = os.path.join(ROOT, "posts", "git-worktree", "index.html")
    if not os.path.exists(sample):
        print("  · 跳过 add_toc（样本页不存在）")
        return
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(open(sample, encoding="utf-8").read())
        tmp = f.name
    add_toc.process(tmp)
    a = md5(tmp)
    add_toc.process(tmp)
    b = md5(tmp)
    s = open(tmp, encoding="utf-8").read()
    os.unlink(tmp)
    check("add_toc 幂等（连处理两次字节一致）", a == b)
    for name, pat in (("nav.toc", '<nav class="toc"'), ("toc-fab", 'class="toc-fab"'),
                      ("brandSet", 'id="brandSet"'), ("backTop", 'id="toTop"')):
        check("注入标记唯一：%s" % name, s.count(pat) <= 1, "出现 %d 次" % s.count(pat))


def gen_index_stable():
    idx = os.path.join(ROOT, "index.html")
    subprocess.run([sys.executable, "tools/gen_index.py"], cwd=ROOT,
                   capture_output=True, check=False)
    a = md5(idx)
    subprocess.run([sys.executable, "tools/gen_index.py"], cwd=ROOT,
                   capture_output=True, check=False)
    b = md5(idx)
    check("gen_index 输出稳定（连生成两次一致）", a == b)


def gen_legal_idempotent():
    """搬运页版权信号：注入有意义（能找到 src-url）、注入两次字节一致、标记各 1 份。"""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    import gen_legal
    import shutil
    import tempfile
    samples = sorted(glob.glob(os.path.join(ROOT, "posts", "*", "index.html")))
    repost = None
    for p in samples:
        s = open(p, encoding="utf-8").read()
        m = re.search(r'<div class="meta">(.*?)</div>', s, re.S)
        if m and "搬运" in m.group(1) and '<a class="src-url"' in s:
            repost = p
            break
    if not repost:
        print("  · 跳过 gen_legal（没有带来源链接的搬运页）")
        return
    tmp = tempfile.mkdtemp()
    try:
        copy = os.path.join(tmp, "index.html")
        shutil.copyfile(repost, copy)
        gen_legal.apply_one(copy)
        a = md5(copy)
        gen_legal.apply_one(copy)
        b = md5(copy)
        s = open(copy, encoding="utf-8").read()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    check("gen_legal 幂等（连注入两次字节一致）", a == b, "%s != %s" % (a, b))
    for name, pat in (("canonical", 'rel="canonical"'), ("robots", 'name="robots"'),
                      ("legal-note", 'class="legal-note"')):
        check("版权标记唯一：%s" % name, s.count(pat) == 1, "出现 %d 次" % s.count(pat))
    check("canonical 指回原文", 'rel="canonical" href="http' in s)


def main():
    print("回归测试")
    md2post_idempotent()
    add_toc_idempotent()
    gen_legal_idempotent()
    gen_index_stable()
    print()
    if FAILED:
        print("✗ 失败 %d 项：%s" % (len(FAILED), "、".join(FAILED)))
        raise SystemExit(1)
    print("✓ 全部通过")


if __name__ == "__main__":
    main()
