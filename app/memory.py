"""Persistent bartender memory, stored as Markdown (the app's only data store).

Two kinds of memory:

* **Rolling short-term memory** — ``data/memory/bartender.md``. A line-per-note
  "little black book" the bartender reads each turn so it can recall prior
  visits ("last time you had a Negroni"). Updated incrementally; cleared from
  Settings.

* **Per-signature design conversations** — ``data/memory/conversations/<slug>.md``.
  When a designed drink is saved, the design thread is distilled into a short
  narrative and stored here, then fed back as context. Deleted together with
  the signature.
"""
from __future__ import annotations

from pathlib import Path

from .config import settings

MEMORY_DIR = settings.data_dir / "memory"
CONVERSATIONS_DIR = MEMORY_DIR / "conversations"
ROLLING_FILE = MEMORY_DIR / "bartender.md"

MAX_ROLLING_LINES = 60  # keep the rolling memory bounded; oldest trimmed


def _ensure_dirs() -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- #
# Rolling memory
# --------------------------------------------------------------------------- #

def load_rolling() -> str:
    if not ROLLING_FILE.exists():
        return ""
    return ROLLING_FILE.read_text(encoding="utf-8").strip()


def append_rolling(note: str) -> None:
    note = (note or "").strip()
    if not note:
        return
    _ensure_dirs()
    existing = load_rolling()
    lines = [ln for ln in existing.splitlines() if ln.strip()]
    lines.append(note)
    # bound the size — drop the oldest
    if len(lines) > MAX_ROLLING_LINES:
        lines = lines[-MAX_ROLLING_LINES:]
    ROLLING_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def clear_rolling() -> None:
    if ROLLING_FILE.exists():
        ROLLING_FILE.write_text("", encoding="utf-8")


# --------------------------------------------------------------------------- #
# Per-signature conversations
# --------------------------------------------------------------------------- #

def conversation_path(slug: str) -> Path:
    return CONVERSATIONS_DIR / f"{slug}.md"


def save_conversation(slug: str, distilled: str) -> Path:
    _ensure_dirs()
    path = conversation_path(slug)
    path.write_text(distilled.strip() + "\n", encoding="utf-8")
    return path


def delete_conversation(slug: str) -> bool:
    path = conversation_path(slug)
    if path.exists():
        path.unlink()
        return True
    return False


def load_conversations_compact() -> str:
    """Concatenate all design-conversation memories for the bartender prompt."""
    if not CONVERSATIONS_DIR.exists():
        return ""
    chunks: list[str] = []
    for p in sorted(CONVERSATIONS_DIR.glob("*.md")):
        body = p.read_text(encoding="utf-8").strip()
        if body:
            chunks.append(f"- {p.stem}：{body.replace(chr(10), ' ')}")
    return "\n".join(chunks)


def conversation_for_slug(slug: str) -> str:
    path = conversation_path(slug)
    return path.read_text(encoding="utf-8").strip() if path.exists() else ""


# --------------------------------------------------------------------------- #
# Wipe everything
# --------------------------------------------------------------------------- #

def clear_all() -> dict:
    """Clear rolling memory + all stored conversations. Returns counts."""
    convs = list(CONVERSATIONS_DIR.glob("*.md")) if CONVERSATIONS_DIR.exists() else []
    n = len(convs)
    clear_rolling()
    for p in convs:
        p.unlink()
    return {"rolling_cleared": True, "conversations_cleared": n}
