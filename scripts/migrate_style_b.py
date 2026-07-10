#!/usr/bin/env python3
"""Convert a Style B recipe file (many recipes, no frontmatter) into Style A
files (one recipe per file, with YAML frontmatter).

Reuses app.knowledge's parsers so the inferred slug / base / glass / flavor
tags match exactly what the loader would compute from the Style B source —
i.e. the migrated recipes are drop-in equivalent.

Usage:
    python scripts/migrate_style_b.py <input.md> <output_dir> [--type classic|mocktail]

This is also the tool for the ongoing workflow: drop a GPT-generated Style B
file into data/_style-b-source/, then run this to mint Style A files.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import knowledge as K  # noqa: E402


def _yaml_list(items: list[str]) -> str:
    return "[" + ", ".join(items) + "]" if items else "[]"


def _quote(v: str) -> str:
    v = str(v)
    if v and (":" in v or v[0] in "\"'#" or v[0] in "-?"):
        return '"' + v.replace('"', '\\"') + '"'
    return v


def migrate(src: Path, out_dir: Path, rtype: str) -> int:
    is_mocktail = rtype == "mocktail"
    raw = src.read_text(encoding="utf-8")
    out_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for title, body in K._split_at_level(raw, 2).items():
        sub = K._split_at_level(body, 3)
        ing_text = K._find_section(sub, "配方", "ingredient", "recipe")
        if not ing_text:
            continue  # intro / principles, not a recipe
        name = K._split_title(title)
        slug = K._slugify(name.en or name.zh)
        story = K._find_section(sub, "背景", "story", "故事")
        flavor_prose = K._find_section(sub, "风味", "flavor")
        mood = K._find_section(sub, "情绪", "mood")
        notes = K._find_section(sub, "调制要点", "bartender", "笔记", "notes")
        steps = K._parse_numbered(K._find_section(sub, "调制方法", "step", "步骤", "method"))
        ings = K._parse_ingredients_table(ing_text) or K._parse_ingredients_bullets(ing_text)
        variants = K._parse_bullets(K._find_section(sub, "变体", "variation"))
        base = K._infer_base(ing_text, is_mocktail)
        flavor_tags = K._derive_flavor_tags(flavor_prose, " ".join(i.item for i in ings))
        glass = K._infer_glass(slug)

        lines = ["---",
                 f"slug: {slug}",
                 "name:",
                 f"  zh: {_quote(name.zh)}",
                 f"  en: {_quote(name.en)}",
                 f"type: {rtype}",
                 f"base: {base}"]
        if glass and glass != "—":
            lines.append(f"glass: {glass}")
        lines += [f"flavor: {_yaml_list(flavor_tags)}", "tags: []", "source: classic", "---", ""]
        heading = f"# {name.en} / {name.zh}" if (name.en and name.zh) else f"# {name.en or name.zh}"
        lines += [heading, ""]
        if story:
            lines += ["## 故事 / Story", story, ""]
        if ings:
            lines += ["## 配方 / Ingredients", "| 用量 Amount | 材料 Ingredient |", "| --- | --- |"]
            lines += [f"| {i.amount} | {i.item} |" for i in ings]
            lines.append("")
        if steps:
            lines.append("## 步骤 / Steps")
            lines += [f"{idx}. {s}" for idx, s in enumerate(steps, 1)]
            lines.append("")
        if flavor_prose:
            lines += ["## 风味 / Flavor", flavor_prose, ""]
        if mood:
            lines += ["## 情绪 / Mood", mood, ""]
        if notes:
            lines += ["## 调酒师笔记 / Bartender Notes", notes, ""]
        if variants:
            lines.append("## 变体 / Variations")
            lines += [f"- {v}" for v in variants]
            lines.append("")

        (out_dir / f"{slug}.md").write_text("\n".join(lines), encoding="utf-8")
        n += 1
        print(f"  {slug:28} {name.en} / {name.zh}")
    return n


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("src")
    ap.add_argument("out_dir")
    ap.add_argument("--type", default="classic", choices=["classic", "mocktail"])
    args = ap.parse_args()
    n = migrate(Path(args.src), Path(args.out_dir), args.type)
    print(f"wrote {n} recipes to {args.out_dir}")


if __name__ == "__main__":
    main()
