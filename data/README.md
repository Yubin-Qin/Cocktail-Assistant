# `data/` — the recipe knowledge base

Every cocktail in this app is a Markdown file. **No database, no code.** Edit a `.md`, reload the page, done. This file is the authoritative reference for the format.

## Two authoring styles — pick whichever you like

The loader understands both. Use whichever feels more natural; you can even mix them in the same folder.

### Style A — one recipe per file (canonical template)
Copy `_TEMPLATE.md`, rename to `<slug>.md`, fill in the YAML frontmatter + bilingual body.
Best for **signatures** and when you want precise taxonomy (filtering by base/glass/flavor).

```
---
slug: my-signature
name: { zh: 我的特调, en: My Signature }
type: signature            # classic | signature | mocktail
base: Gin
glass: Coupe
flavor: [sweet, sour]
tags: [refreshing]
---
# My Signature / 我的特调
## 故事 / Story …
## 配方 / Ingredients …
## 步骤 / Steps …
## 风味 / Flavor …
## 情绪 / Mood …
## 调酒师笔记 / Bartender Notes …
```

### Style B — many recipes in one prose file
No frontmatter. Each recipe is a `## English 中文` heading, then `###` subsections.
This is the style of the examples in `data/_style-b-source/` (`经典鸡尾酒.md` / `经典无酒精鸡尾酒.md`). The live classics/mocktails catalogs were migrated to Style A; use Style B as a draft format (e.g. for GPT) and convert with `scripts/migrate_style_b.py`.
The loader splits the file into individual recipes and **infers** type (from folder), base, glass and flavor tags from the content.

```
## Negroni 尼格罗尼
### 配方
- 琴酒 30 ml
- 金巴利 30 ml
### 调制方法
1. …
### 调制要点
- …
### 风味特征
苦甜、橙皮、草本…
### 情绪特征
成熟、明亮…
### 背景故事
…
```

Recognized subsection titles (either language): `配方/Ingredients`, `调制方法/Steps`, `调制要点/Bartender Notes`, `风味特征/Flavor`, `情绪特征/Mood`, `背景故事/Story`, `变体/Variations`. Any `## ` block **without** a `配方` subsection is treated as general intro material (it still feeds the AI bartender as "principles").

## Where files go

| Folder | `type:` (Style A) | Notes |
| --- | --- | --- |
| `cocktails/classics/` | `classic` | Traditional / canonical cocktails |
| `cocktails/signatures/` | `signature` | Original designs — **also the few-shot examples the AI bartender learns your house style from**. Saved designs land here. |
| `mocktails/` | `mocktail` | Non-alcoholic |

## Frontmatter reference (Style A)

| Field | Required | Type | Notes |
| --- | --- | --- | --- |
| `slug` | ✅ | string | kebab-case, matches filename, globally unique |
| `name` | ✅ | `{zh, en}` | bilingual display name |
| `type` | ✅ | enum | `classic` \| `signature` \| `mocktail` |
| `base` | ✅ | string | primary base spirit; `None` for mocktails |
| `glass` | string | recommended glassware |
| `garnish` | string | e.g. `橙皮 / Orange peel` |
| `abv` | string | approximate % of the *built drink* |
| `difficulty` | enum | `easy` \| `medium` \| `hard` |
| `flavor` | string[] | taste tags (drives filtering + cards) |
| `tags` | string[] | free-form tags for search/filter |
| `source` | string | `IBA` \| `original` \| `adapted` \| `classic` |
| `author`, `created` | | optional, for signatures |

## Body sections

Use the `## 中文 / English` heading convention. Renderer expects:

- `## 故事 / Story` — origin, mood, or idea behind the drink
- `## 配方 / Ingredients` — a Markdown **table** in Style A, or `### 配方` bullets in Style B
- `## 步骤 / Steps` — numbered list
- `## 风味 / Flavor` — 1–2 sentences on the taste profile ✨
- `## 情绪 / Mood` — the feeling/occasion it suits ✨ (powers mood-based design)
- `## 调酒师笔记 / Bartender Notes` — practical tips
- `## 变体 / Variations` (optional)

✨ **Flavor and Mood are first-class** — they make the AI bartender much better at matching a drink to a story or feeling. Fill them in whenever you can.

## Validation

If a file is malformed, the backend logs a `[knowledge] skipping …` warning and continues. Check the server output if a recipe doesn't appear. Duplicate slugs: the last one loaded wins.
