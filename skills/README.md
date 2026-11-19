# Skills

Project-level skills used to build and maintain this site.

| Skill | What it does |
| --- | --- |
| `github-pages-deploy/` | Deploy pages to this repo, the bilingual README convention, credential quirks, and the known pitfalls (DNS outage, CDN cache, screenshot viewports, typing-animation timing). |
| `epub-reader/` | Put an EPUB on `/read/` and read it in the browser. Separate from article publishing: no `build.py`, no feed/index, and the book text never enters the agent's context. |

## Using one

Point your agent at the `SKILL.md` file, or copy the folder into your agent's skills directory:

```bash
cp -r skills/github-pages-deploy ~/.claude/skills/
```

They are plain Markdown — no dependencies, no scripts.
