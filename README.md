# patrick12138.github.io

[English](./README.md) | [简体中文](./README.zh-CN.md)

Small static pages I actually use, hosted on GitHub Pages. No framework, no backend, no build step.

## Pages

| Path | What it is |
| --- | --- |
| `/` | Blog index — original posts and reposts, newest first |
| `/posts/<slug>/` | Individual posts |
| `/tga/` | The Game Awards GOTY nominee checklist, 2014–2025 (68 entries) |
| `/about/` | Terminal-style personal page, English / 中文 toggle |

## Structure

```text
index.html          Blog index
posts/*/index.html  Posts (self-contained)
tga/index.html      TGA checklist (self-contained)
about/index.html    About page (self-contained)
.nojekyll           Serve files as-is, skip Jekyll
```

## Adding a page

1. Create `<slug>/index.html`. Keep CSS, JS and data inline so it works as a single file.
2. Add an entry to the `.list` block in the root `index.html`.
3. Push to `main`. Pages rebuilds in 30–60 seconds.

## Notes

- Every page stores its state in `localStorage`. Nothing is uploaded anywhere.
- `/` and `/tga/` load no external fonts or CDN. `/about/` pulls Figtree and JetBrains Mono from Google Fonts and falls back to system fonts if that fails.

## License

Personal project. Code is free to read and borrow.
