# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this app is

A bilingual (中文 / English) cocktail-learning app: a FastAPI backend plus a vanilla HTML/CSS/JS frontend (no build step). Users browse recipes and chat with an AI bartender that answers questions and co-designs signature drinks. **The files under `data/` are the only data store — there is no database.** The LLM is the **only** external service (no vector DB, no embeddings, no other networked deps); keeping it that way is an explicit project constraint (see `CONTRIBUTING.md`).

## Commands

```bash
bash run.sh                       # create ./venv, install requirements.txt, serve on HOST:PORT (LAN-reachable)
source venv/bin/activate
uvicorn app.main:app --reload     # dev server with hot reload
python -c "import app.main"       # smoke test: imports cleanly iff no syntax/runtime errors at import
```

Configure via `.env` (copy from `.env.example`): `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `HOST`, `PORT`, `DATA_DIR`. Override per-run with env vars, e.g. `PORT=8010 uvicorn app.main:app --reload` (port 8000 may be in use on this machine — use 8010+). The in-app Settings UI also edits these and persists to `.env` live.

There is **no test suite and no linter configured**. The checks in `CONTRIBUTING.md` are exactly: `python -c "import app.main"` and booting `bash run.sh`.

## Architecture

The app loads three Markdown/YAML data stores under `data/`, each behind a **module-level singleton built at import time**: `kb` (`knowledge.py`), `cellar` (`cellar.py`), and `settings` (`config.py`). The OpenAI client `_client` (`llm.py`) is lazy — importing `llm` never requires a key.

- **Recipes** — `data/cocktails/{classics,signatures}/`, `data/mocktails/` → `KnowledgeBase`.
- **Cellar** — `data/cellar/{ingredients,inventory,substitutions}.yml` → `Cellar`.
- **Memory** — `data/memory/bartender.md` (rolling notes) + `data/memory/conversations/<slug>.md` → `memory.py`.

**After any backend write to these stores, call the matching `.reload()`** (`kb.reload()`; `cellar` reloads itself inside its mutators) so the in-memory index and the LLM prompt pick up the change.

### Dual-format Markdown loader (`knowledge.py`)

The loader understands two authoring styles in the same tree (documented in `data/README.md`):

- **Style A** — YAML frontmatter + `# Title` + `## 中文 / English` sections, one recipe per file. Used by signatures and `_TEMPLATE.md`. Taxonomy (`base`/`glass`/`flavor`) comes from frontmatter.
- **Style B** — no frontmatter; many recipes per file, each a `## English 中文` heading with `###` subsections. The classics/mocktails catalogs were migrated to Style A; Style B examples live in `data/_style-b-source/` (skipped by the loader — any path component starting with `_` is) as a draft format for GPT, converted to Style A via `scripts/migrate_style_b.py`. The loader **infers** `base`/`glass`/`flavor` tags from Chinese keyword tables (`_BASE_KEYWORDS`, `_FLAVOR_KEYWORDS`, `_GLASS_BY_SLUG`) and splits the file.

Both become a `Recipe`. `slug` = filename stem, kebab-case, globally unique; collisions are last-writer-wins. Malformed files are skipped with a `[knowledge] skipping …` log line. The shared parsing primitives (`_split_at_level`, `_parse_table`, `_parse_numbered`, `_find_section` by keyword) drive both styles.

### Bartender chat flow (`main.py` `/api/chat`, `llm.py`)

1. `kb.build_chat_context()` assembles the system prompt by **grounding directly in the corpus** (no embeddings): principles/intros, rolling memory, past design conversations, all signatures as a compact style index, a top-k retrieval of relevant references, and the cellar inventory (`cellar.build_context()`).
2. Retrieval (`retrieve()` / `_score`) ranks recipes by English flavor-tag hits in the query plus Chinese character-bigram overlap — it is deliberately embedding-free.
3. The reply streams as **SSE** (`data: {"delta": ...}` … `data: [DONE]`).
4. When finalizing, the model emits a natural-language preamble **then** a fenced JSON recipe block. The frontend hides the JSON and renders a card; `llm.extract_recipe()` (regex on the last fenced JSON object) is the server-side counterpart.
5. A fire-and-forget background task (`_maybe_remember`) appends at most one durable note to rolling memory via `llm.extract_memory_delta`. Memory operations are best-effort and must never raise into the chat path (wrapped in `except`).

### The save flywheel (`recipes.py` + `/api/recipes/save`)

Saving a signature writes canonical Style-A Markdown to `data/cocktails/signatures/<slug>.md` (appending `-2`, `-3`, … on slug collision), then `kb.reload()` so the new file **immediately** becomes extra context and a few-shot example for future designs. If a conversation thread is attached, `llm.distill_conversation` summarizes it into `data/memory/conversations/<slug>.md`. Deleting a signature removes the file + its conversation memory and reloads.

### Cellar coupling (`cellar.py`)

The cellar does double duty. `evaluate()` annotates **every** recipe (both the list and detail endpoints) with availability (`available` / `substitutable` / `missing`), driving the frontend filter; and `build_context()` is injected into every chat prompt so the bartender designs within in-stock ingredients. Ingredient text is normalized against `ingredients.yml` by substring match on search terms (id, zh, en, aliases); `parent` relationships collapse sub-types; `substitutions.yml` provides `missing → substitute` fallbacks; `NON_BLOCKING_CATEGORIES` (garnish/pantry/seasoning) and `OPTIONAL_WORDS` (可选/optional) make those misses non-fatal. Inventory writes persist YAML and reload.

### Live config (`config.py`)

The Settings UI calls `config.update_llm_config()` (rewrites the relevant `KEY=` line in `.env` in place + mutates the `settings` singleton) then `llm.reset_client()` so the next request rebuilds the client — no restart. An empty or `•`-masked `api_key` keeps the existing key, so URL/model edits don't require re-entering it.

### Routing & static files

`/api/*` routes are registered **before** `app.mount("/", StaticFiles(...))`, so the API always wins; the SPA frontend is served from `frontend/` at `/`. Interactive API docs at `/docs`. The startup `lifespan` prints the local + LAN URLs and the LLM config status.

## Conventions

- **Bilingual content**: author in both languages; `## 中文 / English` headings throughout. The bartender replies in the user's language.
- **Recipes are data, not code**: adding/editing a recipe is a Markdown edit under `data/` — no backend change, no restart (content is reloaded on the next request). Start from `data/_TEMPLATE.md` (Style A) and follow the field reference in `data/README.md`.
- **Metrics only** for quantities (ml / g / dash), spirit listed first; `abv` is the approximate % of the *built drink*, not spirit proof.
- Filesystem-safe IDs/paths are produced by `slugify` (in `recipes.py`, ASCII-transliterated) and `_slugify` (in `knowledge.py`); the delete endpoint guards against path traversal via `relative_to(sig_dir)`.
