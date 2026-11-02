#!/usr/bin/env python3
"""把已入库的大图压成 webp 并就地改写引用（存量清理用，幂等）。

webp 分支是就地重编码（quality 逐代下降），**非幂等**，属一次性手动清理。
用法：python3 tools/optimize_assets.py [--max-kb 400] [--dry]
"""
import glob
import config
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_KB = 400
MAX_W = config.IMG["max_w"]
QUALITY = config.IMG["quality"]
METHOD = config.IMG["method"]


def convert(path, max_kb, dry):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".webp":
        # 一次性手动清理：超限的存量 webp 就地重编码（每跑一次质量降一代，别反复跑）
        if os.path.getsize(path) < max_kb * 1024:
            return None
        try:
            from PIL import Image
        except ImportError:
            return None
        try:
            im = Image.open(path)
            im.load()
        except Exception:
            print("  ! 不是图片，跳过：%s" % os.path.relpath(path, ROOT))
            return None
        if im.width > MAX_W:
            im = im.resize((MAX_W, round(im.height * MAX_W / im.width)), Image.LANCZOS)
        im = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB")
        before = os.path.getsize(path)
        if dry:
            return (path, path, before, None)
        import io
        buf = io.BytesIO()
        im.save(buf, "WEBP", quality=QUALITY, method=METHOD)
        if buf.tell() >= before:
            return None    # 没省就放弃，保留原件
        with open(path, "wb") as f:
            f.write(buf.getvalue())
        return (path, path, before, buf.tell())
    if ext in (".svg", ".gif"):
        return None
    if os.path.getsize(path) < max_kb * 1024:
        return None
    try:
        from PIL import Image
    except ImportError:
        return None
    try:
        im = Image.open(path)
        im.load()
    except Exception:
        print("  ! 不是图片，跳过：%s" % os.path.relpath(path, ROOT))
        return None
    if im.width > MAX_W:
        im = im.resize((MAX_W, round(im.height * MAX_W / im.width)), Image.LANCZOS)
    im = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB")
    out = os.path.splitext(path)[0] + ".webp"
    before = os.path.getsize(path)
    if dry:
        return (path, out, before, None)
    im.save(out, "WEBP", quality=QUALITY, method=METHOD)
    os.remove(path)
    return (path, out, before, os.path.getsize(out))


def main():
    dry = "--dry" in sys.argv
    max_kb = MAX_KB
    for i, a in enumerate(sys.argv):
        if a == "--max-kb":
            max_kb = int(sys.argv[i + 1])
    saved = 0
    for p in sorted(glob.glob(os.path.join(ROOT, "assets", "posts", "*", "*"))):
        r = convert(p, max_kb, dry)
        if not r:
            continue
        old, new, before, after = r
        # Windows relpath 给反斜杠，HTML 里是正斜杠，必须归一
        rel_old = os.path.relpath(old, os.path.join(ROOT, "assets")).replace(os.sep, "/")
        rel_new = os.path.relpath(new, os.path.join(ROOT, "assets")).replace(os.sep, "/")
        # 改写所有页面里的引用
        if not dry:
            for page in glob.glob(os.path.join(ROOT, "posts", "*", "index.html")):
                s = open(page, encoding="utf-8").read()
                if rel_old in s:
                    open(page, "w", encoding="utf-8").write(s.replace(rel_old, rel_new))
        saved += before - (after or before)
        print("  %-46s %6.1fMB → %s" % (rel_old, before / 1048576,
                                        "%.2fMB" % (after / 1048576) if after else "(dry)"))
    print("共省 %.1f MB" % (saved / 1048576))


if __name__ == "__main__":
    main()
