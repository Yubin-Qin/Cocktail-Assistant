# Contributing

Thanks for helping improve this project! This guide covers how to add recipes (the most common contribution) and how to work on the code.

## Adding or editing a recipe

All bartending knowledge lives in `data/` as Markdown — no code changes needed.

1. **Read [`data/README.md`](data/README.md)** for the full field reference.
2. **Copy [`data/_TEMPLATE.md`](data/_TEMPLATE.md)** to the right folder:
   - `data/cocktails/classics/` — traditional / canonical cocktails
   - `data/cocktails/signatures/` — original designs (also used as few-shot examples for the AI bartender)
   - `data/mocktails/` — non-alcoholic
3. **Filename = `slug`.** Use lowercase kebab-case, e.g. `penicillin.md` → slug `penicillin`. The slug must match the `slug:` field in frontmatter and be unique across the whole `data/` tree.
4. **Fill in frontmatter + bilingual body.** Provide both `zh` and `en` for `name`. Body sections use the `## 中文 / English` convention.
5. **Reload the app.** Content changes are picked up without a restart.

### Quality bar for a recipe
- Quantities in metric (ml / g), with the spirit first.
- Steps are numbered, actionable, and end with the serve/garnish.
- `abv` is an approximate % for a built drink (not the spirit proof).
- Include a short, accurate **Story** and at least one practical **Bartender Note**.
- Add `## 变体 / Variations` where useful.

## Working on the code

### Setup
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then edit
uvicorn app.main:app --reload
```

Never install packages into your system Python — always use the `venv`.

### Style
- Python: small, single-purpose modules; type hints; Google-style docstrings; keep dependencies minimal.
- Frontend: vanilla JS (no framework), small focused functions, the design tokens live at the top of `css/style.css`.
- Keep the LLM the **only** external service. Don't introduce databases, vector stores, or other networked deps without discussion.

### Before opening a PR
- [ ] `python -c "import app.main"` imports cleanly (no syntax errors).
- [ ] `bash run.sh` boots and the seeded recipes render.
- [ ] New/edited recipes have unique slugs and valid frontmatter.
- [ ] No secrets committed (`.env` is gitignored; never copy real keys into `.env.example`).

### Commit & PR flow
1. Fork & branch from `main`: `feat/...`, `fix/...`, `data/...`.
2. One logical change per PR. Recipe additions can be batched.
3. Write a clear PR description; attach a screenshot for UI changes.
4. Ensure the checks above pass.

## License

By contributing you agree your changes are licensed under the project's [MIT license](LICENSE).
