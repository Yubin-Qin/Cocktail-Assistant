# Substitution engine — developer notes

Where `app/substitutions.py` and `app/llm.py` meet.

## Tier A — rule scoring

`rule_score(missing, sub, missing_cat, sub_cat)` → 0.0–1.0:

- `0.40 × family` (same flavor clan) + `0.30 × flavor-cosine` + `0.20 × function-Jaccard` + `0.10 × category-compatible`.
- Same-family physical mismatch (e.g. liqueur ↔ juice) is damped by the abv/intensity gap.
- Hard exclusions (`_NON_SUBSTITUTE_CATEGORIES`, `_CATEGORY_WHITELIST`): a base spirit can only be replaced by a base spirit; garnish/pantry/seasoning never participate.

Thresholds:

- `_RULE_CANDIDATE = 0.60` — min to send a pair to the LLM.
- `_RULE_STRONG = 0.75` — proposed even before the LLM runs (same family + function).
- `_RULE_PROPOSE = 0.55` — min to propose when the LLM is not configured (degraded mode).

## Tier B — cached LLM

- `judge_substitutions` — verdicts per pair, cached in `substitution_matrix.json` (keyed by `missing → substitute`, stock-independent).
- `resolve_unknown_materials` — maps unrecognized names to catalog entries (synonym) or in-stock substitutes; cached in `unknown_aliases.json`. **Conservative: uncertain → null (no hallucination).**
- Both run on `LLM_REFRESH_MODEL` (a fast non-thinking model, e.g. `deepseek-chat`) via a private per-thread `AsyncOpenAI` (the global client is bound to the uvicorn loop, so the background thread uses its own).

## Profiles

`data/cellar/ingredient_profiles.yml` — `family / flavor (13 axes, 0–3) / function / abv / intensity / source`. A 37-entry hand-authored seed ships as `ingredient_profiles.example.yml`; the rest are LLM-inferred on first refresh. Add/edit freely.

## Few-shot

`docs/fewshot/substitution_examples.json` — annotated pairs (0–10 + `missing_purpose` + `rationale`). The loader prefers `data/cellar/fewshot_personal.json` (personal, includes custom ingredients) if present. Picked samples (≤16 judge, ≤8 resolve, mixed across the score range so the model sees both good and bad substitutes) are injected as turns — see `_judge_fewshot_turns` / `_resolve_fewshot_turns` in `app/llm.py`.

## Triggers (low-frequency)

- `Cellar.reload()` / recipe save / delete → `engine.mark_dirty()` (no LLM).
- Daily scheduler thread (`SUB_REFRESH_HOUR`, daemon) → `force_refresh()` if dirty, at most once per calendar day.
- Manual: cellar panel **"替代品检索"** button → `POST /api/cellar/refresh` → `force_refresh()`.
- `force_refresh` funnels matrix + unknown-name resolution into one background pass, guarded by a single `_refreshing` lock — manual, scheduler, and any stale triggers can't double-run.

On startup, the engine recovers dirty state by comparing the persisted matrix
fingerprint against the current source files, so a restart after a data
change still gets picked up by the next scheduled refresh.

## Unknown-name handling in `evaluate`

A required ingredient the loader can't match becomes `unknown`, which now
**blocks** (the recipe is not shown as makeable). The background resolver may
later turn it into a `mapped_id` (recognized → available/missing by stock) or
a `substitute_id` (in-stock stand-in with conditions), or leave it null
(stays blocked) — see `app/cellar.py` `_evaluate_need`.
