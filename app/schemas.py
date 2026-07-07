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
