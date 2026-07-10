"""Pydantic models for API request/response payloads."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class LocalizedName(BaseModel):
    zh: str = ""
    en: str = ""


class Ingredient(BaseModel):
    amount: str = ""
    item: str = ""


class IngredientAvailability(BaseModel):
    raw_item: str = ""
    amount: str = ""
    status: str = "unknown"  # available | substitutable | missing | unknown
    required: bool = True
    role: str = "ingredient"
    ingredient_id: str | None = None
    name: str = ""
    substitute_id: str | None = None
    substitute_name: str | None = None
    substitute_confidence: str | None = None
    substitute_impact: str | None = None
    # Smart-substitution extras (only set when a substitute was resolved).
    substitute_conditions: Optional[str] = None
    substitute_dosage: Optional[str] = None
    substitute_reason: Optional[str] = None
    substitute_source: Optional[str] = None  # manual | rule | llm


class Availability(BaseModel):
    status: str = "unknown"  # available | substitutable | missing | unknown
    summary: str = ""
    details: list[IngredientAvailability] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    non_blocking_missing: list[str] = Field(default_factory=list)
    substitutions: list[IngredientAvailability] = Field(default_factory=list)
    unknown: list[str] = Field(default_factory=list)


class RecipeSummary(BaseModel):
    """Lightweight view used by the grid/list endpoint."""

    slug: str
    name: LocalizedName
    type: str
    base: str
    glass: str
    abv: Optional[str] = None
    difficulty: Optional[str] = None
    flavor: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    blurb: str = ""
    mood: str = ""
    availability: Availability | None = None


class Recipe(RecipeSummary):
    """Full detail view, with the parsed body sections."""

    garnish: Optional[str] = None
    source: Optional[str] = None
    author: Optional[str] = None
    story: str = ""
    flavor_text: str = ""   # 风味特征 prose
    mood: str = ""          # 情绪特征 prose
    ingredients: list[Ingredient] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    notes: str = ""
    variants: list[str] = Field(default_factory=list)
    body_markdown: str = ""  # raw rendered body, for fallback display


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    context_summary: str = ""


class RecipePayload(BaseModel):
    """A generated recipe submitted via the 'save as .md' button."""

    name: LocalizedName
    type: str = "signature"
    base: str = ""
    glass: str = ""
    garnish: str = ""
    abv: str = ""
    flavor: list[str] = Field(default_factory=list)   # taxonomy tags (optional; auto-derived if empty)
    flavor_text: str = ""                              # 风味 prose
    mood: str = ""                                     # 情绪 prose
    tags: list[str] = Field(default_factory=list)
    story: str = ""
    ingredients: list[Ingredient] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    bartender_notes: str = ""
    variants: str = ""
    conversation: list[ChatMessage] = Field(default_factory=list)  # design thread → distilled to memory


class LLMConfigRequest(BaseModel):
    """Optional partial LLM config for the Settings UI (test / save)."""

    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None


class CellarInventoryUpdate(BaseModel):
    ingredient_id: str
    status: str
    note: str = ""


class CellarIngredientCreate(BaseModel):
    name: str
    category: str = "liqueur"
    status: str = "in_stock"
