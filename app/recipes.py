"""Convert generated recipes back into the canonical Markdown template and
persist them under ``data/cocktails/signatures/``.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date
from pathlib import Path

from .config import settings
from .knowledge import kb
from .schemas import RecipePayload

# reuse the flavor-keyword -> tag map for auto-deriving taxonomy tags
from .knowledge import _derive_flavor_tags  # noqa: E402


def slugify(value: str) -> str:
    """Make a filesystem-safe kebab-case slug from a name."""
    value = (value or "").strip().lower()
    # Normalize unicode (NFKD) then drop combining marks for latin transliteration
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value)  # strip punctuation
    value = re.sub(r"[\s_-]+", "-", value).strip("-")
    return value or "signature"


def _today() -> str:
    # Build an ISO date without using banned datetime calls in scripts — this is
    # normal app runtime, so date.today() is fine here.
    return date.today().isoformat()


def _variants_lines(variants: str) -> str:
    variants = (variants or "").strip()
    if not variants:
        return ""
    lines = []
    for ln in re.split(r"[\r\n]+", variants):
        ln = ln.strip().lstrip("-*•").strip()
        if ln:
            lines.append(f"- {ln}")
    return "\n".join(lines)


def payload_to_markdown(payload: RecipePayload) -> tuple[str, str]:
    """Return (slug, markdown) for a generated recipe, in the canonical template."""
    name = payload.name
    en = name.en.strip() or "Signature"
    zh = name.zh.strip()
    slug = slugify(en)

    # derive flavor tags from the flavor prose if none were supplied
    flavor_tags = payload.flavor or _derive_flavor_tags(payload.flavor_text)

    title_zh = zh or en
    title_en = en

    frontmatter_lines = [
        "---",
        f"slug: {slug}",
        "name:",
        f"  zh: {zh}",
        f"  en: {en}",
        f"type: {payload.type or 'signature'}",
        f"base: {payload.base or 'None'}",
        f"glass: {payload.glass or 'Coupe'}",
        f"garnish: {payload.garnish or ''}",
        f'abv: "{payload.abv or ""}"',
        "difficulty: medium",
        "flavor: " + ("[" + ", ".join(flavor_tags) + "]" if flavor_tags else "[]"),
        "tags: " + ("[" + ", ".join(payload.tags) + "]" if payload.tags else "[]"),
        "source: original",
        f"author: Bartender AI",
        f"created: {_today()}",
        "---",
        "",
        f"# {title_en} / {title_zh}",
        "",
        "## 故事 / Story",
        payload.story.strip() or "(generated signature)",
        "",
        "## 配方 / Ingredients",
        "| 用量 Amount | 材料 Ingredient |",
        "| --- | --- |",
    ]
    for ing in payload.ingredients:
        frontmatter_lines.append(f"| {ing.amount} | {ing.item} |")

    frontmatter_lines += [
        "",
        "## 步骤 / Steps",
    ]
    for i, step in enumerate(payload.steps, 1):
        # Strip any leading "1." the model may have included
        step = re.sub(r"^\s*\d+[.)]\s*", "", step).strip()
        frontmatter_lines.append(f"{i}. {step}")

    if payload.flavor_text.strip():
        frontmatter_lines += ["", "## 风味 / Flavor", payload.flavor_text.strip()]

    if payload.mood.strip():
        frontmatter_lines += ["", "## 情绪 / Mood", payload.mood.strip()]

    frontmatter_lines += [
        "",
        "## 调酒师笔记 / Bartender Notes",
        (payload.bartender_notes.strip() or "—"),
    ]

    variants = _variants_lines(payload.variants)
    if variants:
        frontmatter_lines += ["", "## 变体 / Variations", variants]

    markdown = "\n".join(frontmatter_lines) + "\n"
    return slug, markdown


def save_signature(payload: RecipePayload) -> tuple[str, Path]:
    """Write a generated recipe to ``signatures/`` and reload the knowledge base.

    Returns (slug, path). Appends ``-2``, ``-3``… if the slug already exists.
    """
    slug, markdown = payload_to_markdown(payload)
    target_dir = settings.data_dir / "cocktails" / "signatures"
    target_dir.mkdir(parents=True, exist_ok=True)

    candidate = slug
    n = 2
    while (target_dir / f"{candidate}.md").exists():
        candidate = f"{slug}-{n}"
        n += 1
    slug = candidate
    markdown = re.sub(r"^slug:\s*.*$", f"slug: {slug}", markdown, count=1, flags=re.MULTILINE)

    path = target_dir / f"{slug}.md"
    path.write_text(markdown, encoding="utf-8")

    # Make the new file immediately available to the app + LLM context.
    kb.reload()
    return slug, path
