"""Local cellar inventory and recipe availability analysis.

The cellar is intentionally file-backed, matching the rest of the app: a
catalog of known ingredients, a user-editable inventory, and a small set of
substitution rules all live under ``data/cellar``.
"""
from __future__ import annotations

import re
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .config import settings
from .schemas import Ingredient, Recipe

CELLAR_DIR = settings.data_dir / "cellar"
INGREDIENTS_FILE = CELLAR_DIR / "ingredients.yml"
# User-added custom ingredients live in a separate file so they stay out of
# git (ingredients.yml is tracked app data; custom_ingredients.yml is personal).
CUSTOM_INGREDIENTS_FILE = CELLAR_DIR / "custom_ingredients.yml"
INVENTORY_FILE = CELLAR_DIR / "inventory.yml"
SUBSTITUTIONS_FILE = CELLAR_DIR / "substitutions.yml"

IN_STOCK_STATUSES = {"in_stock", "low"}
NON_BLOCKING_CATEGORIES = {"garnish", "pantry", "seasoning"}
OPTIONAL_WORDS = ("可选", "optional", "可加入少量")


@dataclass
class IngredientDef:
    id: str
    zh: str
    en: str
    category: str
    aliases: list[str] = field(default_factory=list)
    parent: str = ""
    custom: bool = False

    @property
    def label(self) -> str:
        if self.zh and self.en:
            return f"{self.zh} / {self.en}"
        return self.zh or self.en or self.id

    @property
    def search_terms(self) -> list[str]:
        terms = [self.id.replace("_", " "), self.zh, self.en, *self.aliases]
        return sorted({t.strip() for t in terms if t and t.strip()}, key=len, reverse=True)


@dataclass
class Substitution:
    missing: str
    substitute: str
    confidence: str = "medium"
    impact: str = ""
    suitable_for: list[str] = field(default_factory=list)
    # Smart-substitution extras (empty for hand-authored substitutions.yml rows).
    conditions: str = ""
    dosage_note: str = ""
    reason: str = ""
    source: str = "manual"  # manual | rule | llm


@dataclass
class NormalizedNeed:
    raw_item: str
    amount: str
    ingredient_ids: list[str]
    required: bool
    role: str


def _read_yaml(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or default
    return data if isinstance(data, dict) else default


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


class Cellar:
    def __init__(self) -> None:
        self.ingredients: dict[str, IngredientDef] = {}
        self.inventory: dict[str, dict[str, str]] = {}
        self.substitutions: list[Substitution] = []
        self.reload()

    def reload(self) -> None:
        self.ingredients = self._load_ingredients()
        self.inventory = self._load_inventory()
        self.substitutions = self._load_substitutions()
        # Kick off a background matrix refresh if the ingredient/substitution/
        # profile data changed (inventory-only reloads do NOT trigger it —
        # the engine fingerprint excludes inventory.yml).
        from . import substitutions
        substitutions.engine.maybe_refresh(self)

    def _load_ingredients(self) -> dict[str, IngredientDef]:
        out: dict[str, IngredientDef] = {}
        for path in (INGREDIENTS_FILE, CUSTOM_INGREDIENTS_FILE):
            raw = _read_yaml(path, {"ingredients": []})
            for item in raw.get("ingredients", []):
                if not isinstance(item, dict) or not item.get("id"):
                    continue
                ing = IngredientDef(
                    id=str(item.get("id", "")).strip(),
                    zh=str(item.get("zh", "")).strip(),
                    en=str(item.get("en", "")).strip(),
                    category=str(item.get("category", "")).strip(),
                    aliases=[str(a).strip() for a in item.get("aliases", []) if str(a).strip()],
                    parent=str(item.get("parent", "")).strip(),
                    custom=bool(item.get("custom", False)),
                )
                out[ing.id] = ing
        return out

    def _load_inventory(self) -> dict[str, dict[str, str]]:
        raw = _read_yaml(INVENTORY_FILE, {"inventory": []})
        out: dict[str, dict[str, str]] = {}
        for item in raw.get("inventory", []):
            if not isinstance(item, dict) or not item.get("ingredient_id"):
                continue
            ingredient_id = str(item.get("ingredient_id", "")).strip()
            out[ingredient_id] = {
                "status": str(item.get("status") or "missing").strip(),
                "note": str(item.get("note") or "").strip(),
            }
        return out

    def _load_substitutions(self) -> list[Substitution]:
        raw = _read_yaml(SUBSTITUTIONS_FILE, {"substitutions": []})
        out: list[Substitution] = []
        for item in raw.get("substitutions", []):
            if not isinstance(item, dict) or not item.get("missing") or not item.get("substitute"):
                continue
            out.append(Substitution(
                missing=str(item.get("missing", "")).strip(),
                substitute=str(item.get("substitute", "")).strip(),
                confidence=str(item.get("confidence") or "medium").strip(),
                impact=str(item.get("impact") or "").strip(),
                suitable_for=[str(s).strip() for s in item.get("suitable_for", []) if str(s).strip()],
            ))
        return out

    # -- public API ------------------------------------------------------- #

    def summary(self) -> dict:
        categories: dict[str, int] = {}
        status_counts: dict[str, int] = {}
        items = []
        for ing in self.ingredients.values():
            inv = self.inventory.get(ing.id, {})
            status = inv.get("status", "missing")
            categories[ing.category] = categories.get(ing.category, 0) + 1
            status_counts[status] = status_counts.get(status, 0) + 1
            items.append({
                "id": ing.id,
                "zh": ing.zh,
                "en": ing.en,
                "label": ing.label,
                "category": ing.category,
                "status": status,
                "note": inv.get("note", ""),
                "custom": ing.custom,
            })
        return {
            "items": sorted(items, key=lambda x: (x["category"], x["label"])),
            "categories": categories,
            "status_counts": status_counts,
        }

    def update_inventory(self, ingredient_id: str, status: str, note: str = "") -> dict:
        if ingredient_id not in self.ingredients:
            raise ValueError(f"Unknown ingredient: {ingredient_id}")
        status = (status or "").strip()
        if status not in {"in_stock", "low", "missing", "ignored"}:
            raise ValueError("status must be in_stock, low, missing, or ignored")

        raw = _read_yaml(INVENTORY_FILE, {"inventory": []})
        rows = raw.get("inventory", [])
        if not isinstance(rows, list):
            rows = []
        found = False
        for row in rows:
            if isinstance(row, dict) and row.get("ingredient_id") == ingredient_id:
                row["status"] = status
                if note:
                    row["note"] = note
                elif "note" in row:
                    row.pop("note")
                found = True
                break
        if not found:
            row = {"ingredient_id": ingredient_id, "status": status}
            if note:
                row["note"] = note
            rows.append(row)
        _write_yaml(INVENTORY_FILE, {"inventory": rows})
        self.reload()
        return self.summary()

    def add_ingredient(self, name: str, category: str = "liqueur", status: str = "in_stock") -> dict:
        name = (name or "").strip()
        if not name:
            raise ValueError("Ingredient name is required")
        category = (category or "liqueur").strip()
        status = (status or "in_stock").strip()
        if status not in {"in_stock", "low", "missing", "ignored"}:
            raise ValueError("status must be in_stock, low, missing, or ignored")

        existing = self._find_existing_by_name(name)
        if existing:
            return self.update_inventory(existing, status)

        zh, en = self._split_display_name(name)
        ingredient_id = self._custom_id(en or zh)

        raw = _read_yaml(CUSTOM_INGREDIENTS_FILE, {"ingredients": []})
        rows = raw.get("ingredients", [])
        if not isinstance(rows, list):
            rows = []
        while any(isinstance(row, dict) and row.get("id") == ingredient_id for row in rows):
            ingredient_id = self._custom_id(f"{name}-{len(rows)}")
        rows.append({
            "id": ingredient_id,
            "zh": zh,
            "en": en,
            "category": category,
            "aliases": [name],
            "custom": True,
        })
        _write_yaml(CUSTOM_INGREDIENTS_FILE, {"ingredients": rows})

        inv = _read_yaml(INVENTORY_FILE, {"inventory": []})
        inv_rows = inv.get("inventory", [])
        if not isinstance(inv_rows, list):
            inv_rows = []
        inv_rows.append({"ingredient_id": ingredient_id, "status": status})
        _write_yaml(INVENTORY_FILE, {"inventory": inv_rows})
        self.reload()
        return self.summary()

    def delete_ingredient(self, ingredient_id: str) -> dict:
        if ingredient_id not in self.ingredients:
            raise ValueError(f"Unknown ingredient: {ingredient_id}")
        target = CUSTOM_INGREDIENTS_FILE if self.ingredients[ingredient_id].custom else INGREDIENTS_FILE
        raw = _read_yaml(target, {"ingredients": []})
        rows = [r for r in raw.get("ingredients", [])
                if isinstance(r, dict) and r.get("id") != ingredient_id]
        _write_yaml(target, {"ingredients": rows})
        inv = _read_yaml(INVENTORY_FILE, {"inventory": []})
        inv_rows = [r for r in (inv.get("inventory") or [])
                    if isinstance(r, dict) and r.get("ingredient_id") != ingredient_id]
        _write_yaml(INVENTORY_FILE, {"inventory": inv_rows})
        self.reload()
        return self.summary()

    def evaluate(self, recipe: Recipe) -> dict:
        needs = self.normalize_recipe(recipe.ingredients)
        details = []
        blocking_missing: list[str] = []
        non_blocking_missing: list[str] = []
        substitutions = []
        unknown = []

        for need in needs:
            result = self._evaluate_need(need, recipe.slug)
            details.append(result)
            if result["status"] == "missing":
                target = result.get("name") or result["raw_item"]
                if result["required"]:
                    blocking_missing.append(target)
                else:
                    non_blocking_missing.append(target)
            elif result["status"] == "substitutable":
                substitutions.append(result)
            elif result["status"] == "unknown":
                unknown.append(result["raw_item"])

        if blocking_missing:
            status = "missing"
        elif substitutions:
            status = "substitutable"
        else:
            status = "available"

        summary = self._summary_line(status, blocking_missing, non_blocking_missing, substitutions, unknown)
        return {
            "status": status,
            "summary": summary,
            "details": details,
            "missing": blocking_missing,
            "non_blocking_missing": non_blocking_missing,
            "substitutions": substitutions,
            "unknown": unknown,
        }

    def normalize_recipe(self, ingredients: list[Ingredient]) -> list[NormalizedNeed]:
        return [self._normalize_one(ing) for ing in ingredients]

    def build_context(self, limit: int = 80) -> str:
        stocked = []
        missing = []
        for ing in sorted(self.ingredients.values(), key=lambda x: (x.category, x.label)):
            status = self.status_of(ing.id)
            line = f"- {ing.label}"
            note = self.inventory.get(ing.id, {}).get("note")
            if note:
                line += f" ({note})"
            if status in IN_STOCK_STATUSES:
                stocked.append(line)
            elif status == "missing":
                missing.append(line)

        stocked_text = "\n".join(stocked[:limit]) or "- （暂无记录）"
        missing_text = "\n".join(missing[:limit]) or "- （暂无记录）"
        return (
            "## 当前酒库 / Current cellar\n"
            "调酒师必须优先使用“当前拥有”的材料。杯具不算库存；冰块和水默认可用。"
            "如果必须使用缺失材料，先说明并提出替代，最终配方默认不要越过库存。\n\n"
            "### 当前拥有 / In stock\n"
            f"{stocked_text}\n\n"
            "### 当前缺少 / Missing\n"
            f"{missing_text}\n"
        )

    def _find_existing_by_name(self, name: str) -> str:
        needle = name.casefold()
        for ing in self.ingredients.values():
            if any(term.casefold() == needle for term in ing.search_terms):
                return ing.id
        return ""

    @staticmethod
    def _split_display_name(name: str) -> tuple[str, str]:
        parts = [p.strip() for p in re.split(r"\s*/\s*|\s+\|\s+", name, maxsplit=1) if p.strip()]
        if len(parts) == 2:
            left, right = parts
            if any(ord(ch) > 127 for ch in left):
                return left, right
            return right, left
        if any(ord(ch) > 127 for ch in name):
            return name, ""
        return "", name

    @staticmethod
    def _custom_id(name: str) -> str:
        base = (name or "").strip().lower()
        if any(ord(ch) > 127 for ch in base):
            base = ""
        base = re.sub(r"[^a-z0-9_\s-]", "", base)
        base = re.sub(r"[\s-]+", "_", base).strip("_")
        if base:
            return base[:48]
        digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:10]
        return f"custom_{digest}"

    # -- normalization ---------------------------------------------------- #

    def _normalize_one(self, ing: Ingredient) -> NormalizedNeed:
        raw = (ing.item or "").strip()
        required = not any(word.lower() in raw.lower() for word in OPTIONAL_WORDS)
        ids = self._match_ids(raw)
        role = self._role_for(raw, ids)
        if role in {"garnish", "pantry"}:
            required = False
        return NormalizedNeed(
            raw_item=raw,
            amount=ing.amount,
            ingredient_ids=ids,
            required=required,
            role=role,
        )

    def _match_ids(self, raw: str) -> list[str]:
        text = raw.lower()
        matches: list[str] = []
        for ing in self.ingredients.values():
            for term in ing.search_terms:
                if not term:
                    continue
                low = term.lower()
                if low in text:
                    matches.append(ing.id)
                    break
        matches = self._remove_parent_matches(matches)
        if "或" in raw or re.search(r"\bor\b", raw, flags=re.IGNORECASE):
            return matches
        if len(matches) > 1:
            # Keep multiple only for real compound items like honey-agave syrup;
            # otherwise prefer the most specific matched ingredient.
            matches.sort(key=lambda iid: max((len(t) for t in self.ingredients[iid].search_terms), default=0), reverse=True)
            return matches[:1]
        return matches

    def _remove_parent_matches(self, matches: list[str]) -> list[str]:
        unique = list(dict.fromkeys(matches))
        parents = {self.ingredients[i].parent for i in unique if self.ingredients.get(i) and self.ingredients[i].parent}
        return [i for i in unique if i not in parents]

    def _role_for(self, raw: str, ids: list[str]) -> str:
        if any(i == "ice" for i in ids):
            return "pantry"
        if "装饰" in raw or any((self.ingredients.get(i) and self.ingredients[i].category == "garnish") for i in ids):
            return "garnish"
        if any((self.ingredients.get(i) and self.ingredients[i].category == "base_spirit") for i in ids):
            return "base"
        if any((self.ingredients.get(i) and self.ingredients[i].category == "citrus_juice") for i in ids):
            return "acid"
        if any((self.ingredients.get(i) and self.ingredients[i].category == "sweetener") for i in ids):
            return "sweetener"
        return "ingredient"

    # -- availability ----------------------------------------------------- #

    def _evaluate_need(self, need: NormalizedNeed, recipe_slug: str) -> dict:
        base = {
            "raw_item": need.raw_item,
            "amount": need.amount,
            "required": need.required,
            "role": need.role,
            "ingredient_ids": need.ingredient_ids,
        }
        if not need.ingredient_ids:
            return {**base, "status": "available" if not need.required else "unknown", "name": need.raw_item}

        available_id = next((iid for iid in need.ingredient_ids if self.is_available(iid)), "")
        if available_id:
            return {**base, "status": "available", "ingredient_id": available_id, "name": self.label(available_id)}

        if not need.required:
            first = need.ingredient_ids[0]
            return {**base, "status": "missing", "ingredient_id": first, "name": self.label(first)}

        sub = self.find_substitution(need.ingredient_ids, recipe_slug)
        if sub:
            missing_id = next((iid for iid in need.ingredient_ids if iid == sub.missing), need.ingredient_ids[0])
            return {
                **base,
                "status": "substitutable",
                "ingredient_id": missing_id,
                "name": self.label(missing_id),
                "substitute_id": sub.substitute,
                "substitute_name": self.label(sub.substitute),
                "substitute_confidence": sub.confidence,
                "substitute_impact": sub.impact,
                "substitute_conditions": sub.conditions,
                "substitute_dosage": sub.dosage_note,
                "substitute_reason": sub.reason,
                "substitute_source": sub.source,
            }

        first = need.ingredient_ids[0]
        return {**base, "status": "missing", "ingredient_id": first, "name": self.label(first)}

    def status_of(self, ingredient_id: str) -> str:
        return self.inventory.get(ingredient_id, {}).get("status", "missing")

    def is_available(self, ingredient_id: str) -> bool:
        status = self.status_of(ingredient_id)
        if status in IN_STOCK_STATUSES:
            return True
        ing = self.ingredients.get(ingredient_id)
        if ing and ing.parent and self.status_of(ing.parent) in IN_STOCK_STATUSES:
            return True
        return False

    def find_substitution(self, missing_ids: list[str], recipe_slug: str) -> Substitution | None:
        for sub in self.substitutions:
            if sub.missing not in missing_ids:
                continue
            if sub.suitable_for and recipe_slug not in sub.suitable_for:
                continue
            if self.is_available(sub.substitute):
                return sub
        for sub in self.substitutions:
            if sub.missing in missing_ids and self.is_available(sub.substitute):
                return sub
        # Fall back to the smart substitution engine (Tier-A rules + cached
        # Tier-B LLM verdicts) for pairs the hand-authored table doesn't cover.
        from . import substitutions
        smart = substitutions.engine.find_smart_substitution(missing_ids, self)
        if smart:
            return Substitution(
                missing=smart.missing,
                substitute=smart.substitute,
                confidence=smart.confidence,
                impact=smart.conditions,
                conditions=smart.conditions,
                dosage_note=smart.dosage_note,
                reason=smart.reason,
                source=smart.source,
            )
        return None

    def label(self, ingredient_id: str) -> str:
        ing = self.ingredients.get(ingredient_id)
        return ing.label if ing else ingredient_id

    def _summary_line(
        self,
        status: str,
        blocking_missing: list[str],
        non_blocking_missing: list[str],
        substitutions: list[dict],
        unknown: list[str],
    ) -> str:
        if status == "available":
            if non_blocking_missing:
                return "核心材料齐全；少量装饰或可选项缺失。"
            if unknown:
                return "已识别材料基本齐全；少量材料未能规范识别。"
            return "当前酒库材料齐全，可以调制。"
        if status == "substitutable":
            names = [f"{s.get('name')}→{s.get('substitute_name')}" for s in substitutions[:2]]
            return "可用替代方案调制：" + "，".join(names)
        return "缺少关键材料：" + "，".join(blocking_missing[:3])


cellar = Cellar()
