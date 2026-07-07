"""Load and index the Markdown recipe knowledge base.

Two authoring styles are supported so contributors can pick whichever they
prefer:

* **Format A — single recipe per file** (see ``data/_TEMPLATE.md``):
  YAML frontmatter + one ``# Title`` + ``##`` sections. Used by signatures
  and the canonical template.

* **Format B — many recipes per file** (the prose style used in the seeded
  ``经典鸡尾酒.md`` / ``经典无酒精鸡尾酒.md``):
  no frontmatter; each recipe is a ``## English 中文`` heading followed by
  ``### 配方 / 调制方法 / 调制要点 / 风味特征 / 情绪特征 / 背景故事`` subsections.
  The loader splits these into individual recipes and infers the taxonomy
  (type, base, glass, flavor tags) from the content.

Either way, everything becomes a :class:`Recipe`, and the bartender prompt is
grounded in the resulting knowledge.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import frontmatter

from .config import settings
from .schemas import Ingredient, LocalizedName, Recipe, RecipeSummary


# --------------------------------------------------------------------------- #
# Generic section splitting
# --------------------------------------------------------------------------- #

def _split_at_level(md: str, level: int) -> dict[str, str]:
    """Split Markdown into ``{header: body}`` at a given ``#`` level (2 or 3)."""
    pat = r"^" + "#" * level + r"\s+(.*)$"
    parts = re.split(pat, md, flags=re.MULTILINE)
    sections: dict[str, str] = {}
    i = 1
    while i < len(parts):
        title = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        sections[title] = body
        i += 2
    return sections


def _find_section(sections: dict[str, str], *keywords: str) -> str:
    for title, body in sections.items():
        low = title.lower()
        if any(kw.lower() in low for kw in keywords):
            return body
    return ""


# --------------------------------------------------------------------------- #
# Body parsers (shared)
# --------------------------------------------------------------------------- #

def _parse_table(text: str) -> list[tuple[str, str]]:
    """Parse a Markdown ``| a | b |`` table into (col0, col1) tuples."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip().startswith("|")]
    sep_clean = lines[1].replace("|", "").replace(" ", "").strip() if len(lines) >= 2 else ""
    if sep_clean and set(sep_clean) <= set("-:"):
        lines = lines[2:]  # drop header + separator
    rows: list[tuple[str, str]] = []
    for ln in lines:
        cells = [c.strip() for c in ln.strip("|").split("|")]
        if len(cells) >= 2 and (cells[0] or cells[1]):
            rows.append((cells[0], cells[1]))
    return rows


_LIST_RE = re.compile(r"^\s*(?:\d+[.)]|[-*•])\s+(.*)$")


def _parse_numbered(text: str) -> list[str]:
    """Parse Markdown numbered steps into strings, dropping the leading index."""
    items: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^\s*(\d+[.)])\s+(.*)$", line)
        if m:
            items.append(m.group(2).strip())
    return items


def _parse_bullets(text: str) -> list[str]:
    """Parse Markdown bulleted list items into strings (marker stripped)."""
    items: list[str] = []
    for line in text.splitlines():
        m = _LIST_RE.match(line)
        if m:
            items.append(m.group(1).strip())
    return items


def _bullet_to_ingredient(line: str) -> Ingredient:
    """Turn a bullet like '琴酒 60 ml' (material + trailing quantity) into an Ingredient."""
    line = re.sub(r"[，,]\s*可选.*$", "", line).strip()  # drop "，可选..." notes
    line = line.lstrip("-*• ").strip()
    tokens = line.split()
    idx = next((i for i, tok in enumerate(tokens) if tok[:1].isdigit()), None)
    if idx and idx > 0:
        item = " ".join(tokens[:idx])
        amount = " ".join(tokens[idx:])
    else:
        item, amount = line, ""
    return Ingredient(amount=amount, item=item)


def _parse_ingredients_table(text: str) -> list[Ingredient]:
    return [Ingredient(amount=a, item=b) for a, b in _parse_table(text)]


def _parse_ingredients_bullets(text: str) -> list[Ingredient]:
    return [_bullet_to_ingredient(ln) for ln in _parse_bullets(text)]


def _blurb(story: str, limit: int = 90) -> str:
    story = story.strip()
    if not story:
        return ""
    first = story.split("\n", 1)[0].strip()
    return (first[:limit] + "…") if len(first) > limit else first


# --------------------------------------------------------------------------- #
# Taxonomy inference (for frontmatter-less Format B recipes)
# --------------------------------------------------------------------------- #

_BASE_KEYWORDS = [
    ("琴酒", "Gin"), ("金酒", "Gin"),
    ("威士忌", "Whisky"), ("波本", "Bourbon"), ("黑麦", "Rye"),
    ("朗姆", "Rum"),
    ("龙舌兰", "Tequila"),
    ("伏特加", "Vodka"),
    ("干邑", "Cognac"), ("白兰地", "Brandy"),
    ("香槟", "Sparkling"), ("起泡酒", "Sparkling"), ("起泡", "Sparkling"),
]

_FLAVOR_KEYWORDS = [
    ("苦", "bitter"), ("甜", "sweet"), ("酸", "sour"), ("烟熏", "smoky"),
    ("花", "floral"), ("草本", "herbal"), ("杜松", "botanical"),
    ("柑橘", "citrus"), ("柠檬", "citrus"), ("青柠", "citrus"), ("葡萄柚", "citrus"),
    ("咖啡", "coffee"), ("可可", "cocoa"), ("焦糖", "caramel"),
    ("薄荷", "mint"), ("姜", "spicy"), ("辛辣", "spicy"), ("辣", "spicy"),
    ("奶油", "creamy"), ("椰", "creamy"),
    ("清爽", "refreshing"), ("气泡", "fizzy"), ("木桶", "woody"), ("橡木", "woody"),
    ("咸鲜", "savory"), ("鲜味", "savory"), ("热带", "fruity"), ("果", "fruity"),
]

# slug -> glass, for recipes that don't state one explicitly
_GLASS_BY_SLUG = {
    "martini": "Coupe", "manhattan": "Coupe", "old-fashioned": "Rocks",
    "negroni": "Rocks", "daiquiri": "Coupe", "margarita": "Margarita",
    "mojito": "Highball", "whiskey-sour": "Rocks", "sidecar": "Coupe",
    "gimlet": "Coupe", "moscow-mule": "Copper mug", "french-75": "Flute",
    "espresso-martini": "Coupe", "gin-tonic": "Copa",
    "shirley-temple": "Highball", "roy-rogers": "Highball", "virgin-mojito": "Highball",
    "arnold-palmer": "Highball", "virgin-mary": "Highball",
    "virgin-pina-colada": "Hurricane", "lemon-squash": "Highball",
    "fruit-punch": "Punch bowl", "cucumber-cooler": "Highball",
    "ginger-lime-fizz": "Highball", "no-groni": "Rocks",
}


def _infer_base(text: str, is_mocktail: bool) -> str:
    if is_mocktail:
        return "None"
    for kw, base in _BASE_KEYWORDS:
        if kw in text:
            return base
    return "—"


def _derive_flavor_tags(*texts: str) -> list[str]:
    hay = " ".join(texts)
    found: list[str] = []
    for kw, tag in _FLAVOR_KEYWORDS:
        if kw in hay and tag not in found:
            found.append(tag)
    return found[:4]


def _infer_glass(slug: str) -> str:
    return _GLASS_BY_SLUG.get(slug, "—")


def _split_title(title: str) -> LocalizedName:
    """'Old Fashioned 古典鸡尾酒' -> {en:'Old Fashioned', zh:'古典鸡尾酒'}."""
    for i, ch in enumerate(title):
        if ord(ch) > 127:
            return LocalizedName(en=title[:i].strip(), zh=title[i:].strip())
    return LocalizedName(en=title.strip())


# --------------------------------------------------------------------------- #
# Frontmatter coercion (Format A)
# --------------------------------------------------------------------------- #

def _localized(value) -> LocalizedName:
    if isinstance(value, dict):
        return LocalizedName(zh=str(value.get("zh", "")), en=str(value.get("en", "")))
    if isinstance(value, str) and value:
        return LocalizedName(en=value)
    return LocalizedName()


def _as_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str) and value.strip():
        return [s.strip() for s in re.split(r"[,，;；]", value) if s.strip()]
    return []


def _type_from_path(rel_parts: tuple[str, ...]) -> str:
    if not rel_parts:
        return "classic"
    folder = rel_parts[0].lower()
    if folder == "mocktails":
        return "mocktail"
    if folder == "cocktails":
        sub = rel_parts[1].lower() if len(rel_parts) > 1 else ""
        return "signature" if sub == "signatures" else "classic"
    return "classic"


# --------------------------------------------------------------------------- #
# Knowledge base
# --------------------------------------------------------------------------- #

class KnowledgeBase:
    """In-memory index of all recipes + general principles, reloadable."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        self.recipes: dict[str, Recipe] = {}
        self.principles: str = ""  # general bartending notes from intros
        self.reload()

    # -- loading ------------------------------------------------------------ #

    def reload(self) -> None:
        self.recipes = {}
        self.principles = ""
        if not self.data_dir.exists():
            print(f"[knowledge] data dir not found: {self.data_dir}")
            return
        for md_path in sorted(self.data_dir.rglob("*.md")):
            if md_path.name.startswith("_") or md_path.name.upper() == "README.MD":
                continue
            try:
                self._load_file(md_path)
            except Exception as exc:  # noqa: BLE001 — skip malformed files
                print(f"[knowledge] skipping {md_path}: {exc}")
        print(f"[knowledge] loaded {len(self.recipes)} recipes from {self.data_dir}")

    def _load_file(self, path: Path) -> None:
        rel_parts = path.relative_to(self.data_dir).parts
        default_type = _type_from_path(rel_parts)
        raw = path.read_text(encoding="utf-8")

        # Format A: frontmatter present -> single recipe from frontmatter + body.
        if frontmatter.checks(raw):
            post = frontmatter.loads(raw)
            recipe = self._recipe_from_frontmatter(post, path, default_type)
            if recipe:
                self._add(recipe)
            return

        # Format B: no frontmatter -> many recipes split by `## `, plus intro.
        self._load_multi_recipe(raw, default_type)

    def _add(self, recipe: Recipe) -> None:
        # last-writer-wins on slug collisions
        self.recipes[recipe.slug] = recipe

    def _recipe_from_frontmatter(self, post, path: Path, default_type: str) -> Recipe | None:
        meta = post.metadata
        slug = str(meta.get("slug") or path.stem).strip().lower()
        rtype = str(meta.get("type") or default_type).strip().lower()
        body = post.content.strip()
        sections = _split_at_level(body, 2)

        flavor_prose = _find_section(sections, "风味", "flavor")
        return Recipe(
            slug=slug,
            name=_localized(meta.get("name")),
            type=rtype,
            base=str(meta.get("base") or "None").strip(),
            glass=str(meta.get("glass") or "").strip(),
            garnish=str(meta.get("garnish") or "").strip() or None,
            abv=str(meta.get("abv") or "").strip() or None,
            difficulty=str(meta.get("difficulty") or "").strip() or None,
            flavor=_as_list(meta.get("flavor")),
            tags=_as_list(meta.get("tags")),
            source=str(meta.get("source") or "").strip() or None,
            author=str(meta.get("author") or "").strip() or None,
            story=_find_section(sections, "story", "背景", "故事"),
            ingredients=_parse_ingredients_table(_find_section(sections, "ingredient", "配方", "recipe")),
            steps=_parse_numbered(_find_section(sections, "step", "调制方法", "步骤", "method")),
            notes=_find_section(sections, "bartender", "调制要点", "笔记", "notes"),
            flavor_text=flavor_prose,
            mood=_find_section(sections, "情绪", "mood"),
            variants=_parse_bullets(_find_section(sections, "variation", "变体")),
            body_markdown=body,
            blurb=_blurb(_find_section(sections, "story", "背景", "故事")),
        )

    def _load_multi_recipe(self, raw: str, default_type: str) -> None:
        is_mocktail = default_type == "mocktail"
        intro_bits: list[str] = []

        top = _split_at_level(raw, 2)
        for title, body in top.items():
            sub = _split_at_level(body, 3)
            # A real recipe has a 配方 (ingredients) subsection; otherwise it's intro.
            if not (_find_section(sub, "配方", "ingredient", "recipe")):
                intro_bits.append(f"## {title}\n{body}".strip())
                continue

            name = _split_title(title)
            slug = _slugify(name.en or name.zh)
            ing_text = _find_section(sub, "配方", "ingredient", "recipe")
            story = _find_section(sub, "背景", "story", "故事")
            flavor_prose = _find_section(sub, "风味", "flavor")
            mood = _find_section(sub, "情绪", "mood")
            ingredients = _parse_ingredients_table(ing_text) or _parse_ingredients_bullets(ing_text)
            base = _infer_base(ing_text, is_mocktail)
            flavor_tags = _derive_flavor_tags(flavor_prose, " ".join(i.item for i in ingredients))

            recipe = Recipe(
                slug=slug,
                name=name,
                type=default_type,
                base=base,
                glass=_infer_glass(slug),
                abv=None if is_mocktail else None,
                difficulty=None,
                flavor=flavor_tags,
                tags=[],
                source="classic",
                story=story,
                ingredients=ingredients,
                steps=_parse_numbered(_find_section(sub, "调制方法", "step", "步骤", "method")),
                notes=_find_section(sub, "调制要点", "bartender", "笔记", "notes"),
                flavor_text=flavor_prose,
                mood=mood,
                variants=_parse_bullets(_find_section(sub, "变体", "variation")),
                body_markdown=body,
                blurb=_blurb(story),
            )
            self._add(recipe)

        if intro_bits:
            self.principles += ("\n\n" if self.principles else "") + "\n\n".join(intro_bits)

    # -- queries ------------------------------------------------------------ #

    def list(self, type: str | None = None, q: str | None = None) -> list[RecipeSummary]:
        q = (q or "").strip().lower()
        out: list[RecipeSummary] = []
        for r in self.recipes.values():
            if type and type != "all" and r.type != type:
                continue
            if q:
                hay = " ".join(
                    [r.name.zh, r.name.en, r.base, r.glass or "", r.mood or "",
                     *r.flavor, *r.tags]
                ).lower()
                if q not in hay:
                    continue
            out.append(_to_summary(r))
        return out

    def get(self, slug: str) -> Recipe | None:
        return self.recipes.get(slug)

    def by_type(self, rtype: str) -> Iterable[Recipe]:
        return (r for r in self.recipes.values() if r.type == rtype)

    def counts(self) -> dict[str, int]:
        c: dict[str, int] = {}
        for r in self.recipes.values():
            c[r.type] = c.get(r.type, 0) + 1
        return c

    # -- LLM context -------------------------------------------------------- #

    def _compact(self, r: Recipe) -> str:
        bits = [f"- {r.name.en or r.name.zh}"]
        if r.name.zh and r.name.en:
            bits.append(f" / {r.name.zh}")
        bits.append(f" | base: {r.base} | glass: {r.glass}")
        if r.flavor:
            bits.append(f" | flavor: {', '.join(r.flavor)}")
        if r.mood:
            bits.append(f" | mood: {r.mood[:40]}")
        return "".join(bits)

    def build_chat_context(self) -> str:
        signatures = list(self.by_type("signature"))
        classics = list(self.by_type("classic"))
        mocktails = list(self.by_type("mocktail"))

        parts: list[str] = ["# 酒吧知识库 / Bar Knowledge Base"]

        if self.principles:
            parts.append("\n## 吧台基础与原则 / Bar fundamentals & principles\n"
                         + self.principles.strip() + "\n")

        parts.append(
            "\n## 本店特调 — 风格参考与范例 / House Signatures (style reference & examples)\n"
            "These define the bar's house style and the expected output format. "
            "Study their balance, naming, and bartender notes.\n"
        )
        for r in signatures[:6]:
            parts.append(f"\n### {r.name.en} / {r.name.zh}\n{r.body_markdown}\n")
        if not signatures:
            parts.append("(no signatures yet)\n")

        parts.append("\n## 经典鸡尾酒索引 / Classic cocktails (compact index)\n")
        for r in classics:
            parts.append(self._compact(r))

        parts.append("\n\n## 无酒精索引 / Mocktails (compact index)\n")
        for r in mocktails:
            parts.append(self._compact(r))

        return "\n".join(parts)


# --------------------------------------------------------------------------- #
# Helpers used across modules
# --------------------------------------------------------------------------- #

def _slugify(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"[^\w\s-]", "", value)
    value = re.sub(r"[\s_-]+", "-", value).strip("-")
    return value or "signature"


def _to_summary(r: Recipe) -> RecipeSummary:
    return RecipeSummary(
        slug=r.slug,
        name=r.name,
        type=r.type,
        base=r.base,
        glass=r.glass,
        abv=r.abv,
        difficulty=r.difficulty,
        flavor=r.flavor,
        tags=r.tags,
        blurb=r.blurb,
        mood=r.mood,
    )


# Module-level singleton, reloaded when recipes are saved.
kb = KnowledgeBase(settings.data_dir)
