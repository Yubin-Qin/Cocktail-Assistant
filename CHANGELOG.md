# Changelog

Notable changes to the Cocktail app. Format based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Fixed
- Cellar delete button: after it auto-reverted (outside click / 5 s timeout), clicking it again failed to re-confirm. The click landed on the inner SVG `<path>`, which got detached when the button content swapped to the "Delete" label — so the document outside-click handler could no longer find the button via `closest()` and instantly reset the freshly-confirmed state. Switched to `stopPropagation()` on the button click plus an explicit confirming-button pointer.

## [0.2.0] - 2026-07-10

### Added — 智能材料替代引擎 / Smart substitution engine
- **Two-tier substitution.** A realtime rule layer (flavor-cosine + function overlap + category whitelist + bartender hard exclusions such as "a base spirit can't be replaced by a juice") plus a cached LLM layer that judges `yes | conditional | no` with conditions, dosage notes, and a reason.
- **Ingredient profiles** — structured `family / flavor / function / abv / intensity` per ingredient. A 37-entry hand-authored seed ships as `data/cellar/ingredient_profiles.example.yml`; the live file (`ingredient_profiles.yml`) is LLM-augmented and gitignored.
- **Substitution matrix** — cached LLM verdicts, keyed by ingredient pair (independent of current stock), persisted to `data/cellar/substitution_matrix.json`. Refreshed in the background **only when ingredient / substitution / profile data changes** — inventory-only reloads never trigger it, and only uncached pairs are ever judged.
- **`LLM_REFRESH_MODEL`** setting: run the background matrix refresh on a fast non-thinking model (e.g. `deepseek-chat`) while keeping the reasoning model for the bartender chat.
- New API: `DELETE /api/cellar/ingredients/{id}`; `GET /api/cellar` now exposes `matrix_status` (`refreshing | ready | stale`, pair count).

### Changed — 酒柜面板 / Cellar panel
- List grouped by category with a light section header + divider (Apple-style), in a sensible category order; the English category is shown after each item (e.g. "Cola, Mixer").
- Per-item delete button (top-right): grey ✕ → click turns into a red "Delete / 删除" pill → click again to confirm. Auto-reverts on outside click or after 5 s.
- Search and add merged into one control — name field + category dropdown (with "All / 全部") + add button; typing or changing the dropdown filters the list live.
- 冰块 / 水 (Pantry) hidden from the cellar since they are always available.

### Changed — 隐私 / Privacy
- **Custom ingredients are isolated** to `data/cellar/custom_ingredients.yml` (gitignored). `ingredients.yml` ships only the curated catalog, so anything you add via the UI never enters git.
- Substitution runtime data (profiles + matrix) gitignored; a generic seed template (`ingredient_profiles.example.yml`) is tracked.

## [0.1.0] — initial release
- Bilingual (中文 / English) cocktail-learning app: recipe library + AI bartender chat that co-designs signature drinks.
- File-backed cellar (ingredients / inventory / static substitution rules) and Markdown recipe store — no database.
