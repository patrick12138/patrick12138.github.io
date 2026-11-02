# patrick12138.github.io

[English](./README.md) | [简体中文](./README.zh-CN.md)

Small static pages I actually use, hosted on GitHub Pages. No framework, no backend, no build step.

## Pages

| Path | What it is |
| --- | --- |
| `/` | Blog index — original posts and reposts, newest first |
| `/posts/<slug>/` | Individual posts |
| `/lab/` | Lab — small things I build for myself |
| `/backlog/` | Games backlog — tick off what I finish, watch the hours drop |
| `/tga/` | The Game Awards GOTY nominee checklist, 2014–2025 (68 entries) |
| `/about/` | Terminal-style personal page, English / 中文 toggle |

## Structure

```text
index.html          Blog index
posts/*/index.html  Posts (self-contained)
lab/index.html      Lab index
tga/index.html      TGA checklist (self-contained)
about/index.html    About page (self-contained)
assets/posts/*/     Images downloaded from original posts
.nojekyll           Serve files as-is, skip Jekyll
```

## Adding a page

1. Create `<slug>/index.html`. Keep CSS, JS and data inline so it works as a single file.
2. Add an entry to the `.list` block in the root `index.html`.
3. Push to `main`. Pages rebuilds in 30–60 seconds.

## Notes

- Every page stores its state in `localStorage`. Nothing is uploaded anywhere.
- `/` and `/tga/` load no external fonts or CDN. `/about/` pulls Figtree and JetBrains Mono from Google Fonts and falls back to system fonts if that fails.

## Development

Everything is generated from `tools/` — no hand-edited HTML.

| Script | Purpose |
| --- | --- |
| `build.py` | One command: rebuild → TOC → index → asset hashes → QA → optional push |
| `md2post.py` | Markdown → one post page (localises images, turns media into links) |
| `rebuild.py` | Rebuild every post from `sources.json` |
| `add_toc.py` | Inject / refresh table of contents (idempotent) |
| `gen_index.py` | Regenerate the home list by scanning `posts/` |
| `qa.py` | Typography check — any P0 blocks deploy |

```bash
python3 tools/build.py --push "feat: new post"
```

Asset versions (`?v=`) are content hashes written by `build.py`; never edit them by hand.

## License

Personal project. Code is free to read and borrow.
