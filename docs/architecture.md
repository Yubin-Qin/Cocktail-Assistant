# Architecture

A bilingual cocktail-learning app: a FastAPI backend serving a vanilla
HTML/CSS/JS frontend, with **no database** — recipes and the cellar are
Markdown/YAML files under `data/`, and **the LLM is the only external
service** (no embeddings, no vector DB).

## Layout

- `app/` — FastAPI backend (routes, knowledge loader, cellar, substitution engine, LLM layer).
- `frontend/` — vanilla JS, no build step.
- `data/` — the knowledge base: recipes (`cocktails/`, `mocktails/`), the cellar (`cellar/`), bartender memory (`memory/`).
- `docs/` — this documentation.

## Two recipe authoring styles

Both produce the same `Recipe` model (`app/knowledge.py`):

- **Style A** — one recipe per `.md` with YAML frontmatter (the canonical `data/_TEMPLATE.md`). Used by signatures; classics/mocktails were migrated to it.
- **Style B** — many recipes per prose file (`## English 中文` + `###` subsections). Kept under `data/_style-b-source/` as a draft format (e.g. for GPT); convert with `scripts/migrate_style_b.py`.

## Smart substitution engine (`app/substitutions.py`)

When a recipe needs an ingredient you don't have, the engine proposes a
substitute in two tiers:

- **Tier A (rule, realtime, free)** — hand-authored `family / flavor / function / abv / intensity` profiles + cosine similarity + category whitelist + bartender hard exclusions. Always on; no LLM.
- **Tier B (LLM, cached)** — for promising pairs, an LLM judges `yes | conditional | no` with conditions/dosage/reason. Cached in a matrix keyed by ingredient pair (independent of stock), plus an unknown-name resolver (`unknown_aliases.json`) for names not in the catalog.

Both are **low-frequency**:
- Source changes (material/recipe) mark the engine **dirty** — the LLM is **not** run on every edit.
- A daily scheduler (configurable `SUB_REFRESH_HOUR`, default 22) refreshes if dirty.
- A manual **"替代品检索 / Refresh substitutes"** button in the cellar panel triggers it immediately.
- Refreshes are incremental (only uncached pairs/names) and atomic (temp + `os.replace`).

`evaluate()` always uses the in-memory matrix/aliases (a refresh swaps the
pointer atomically under the GIL), so the UI never blocks on the LLM.

## Few-shot calibration

`docs/fewshot/substitution_examples.json` (open-source subset) and the
optional `data/cellar/fewshot_personal.json` (personal, gitignored) hold
human-annotated substitute pairs (`substitutability` 0–10 + rationale). These
are injected as `user`/`assistant` turns into the judge and unknown-resolver
prompts, calibrating the LLM's verdicts.

## Privacy

`.env` (API key), `data/cellar/inventory.yml`, `custom_ingredients.yml`,
`ingredient_profiles.yml`, `substitution_matrix.json`, `unknown_aliases.json`,
`fewshot_personal.json`, and `data/memory/` + `data/cocktails/signatures/`
are all gitignored — your personal bar never enters the repo. See
`.gitignore` for the full list.
