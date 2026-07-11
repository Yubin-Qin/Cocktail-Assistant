"""Application configuration, loaded from environment / .env.

All settings have sensible defaults so the app runs out of the box for
browsing recipes. The LLM-related keys (LLM_API_KEY etc.) come from a
``.env`` file — see ``.env.example``.
"""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed settings sourced from the process environment and .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- LLM (OpenAI-compatible) -----------------------------------------
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_refresh_model: str = ""  # optional faster/non-thinking model for background substitution refresh
    sub_refresh_hour: int = 22  # local hour when the daily substitution refresh may run

    # --- Server ----------------------------------------------------------
    host: str = "0.0.0.0"
    port: int = 8000

    # --- Data ------------------------------------------------------------
    data_dir: Path = Path("data")

    @property
    def llm_configured(self) -> bool:
        """True if a non-placeholder API key is set."""
        return bool(self.llm_api_key) and not self.llm_api_key.startswith("sk-your")


settings = Settings()


# --------------------------------------------------------------------------- #
# Runtime LLM config updates (Settings UI) — mutates the singleton + .env
# --------------------------------------------------------------------------- #

_ENV_PATH = Path(".env")


def key_hint() -> str:
    """A non-sensitive hint about the stored key, e.g. '••••2785'."""
    k = settings.llm_api_key
    if not k:
        return ""
    return ("•" * min(8, max(0, len(k) - 4))) + k[-4:] if len(k) > 4 else "••••"


def _set_env_key(key: str, value: str) -> None:
    """Replace (or append) one ``KEY=value`` line in .env without touching others."""
    lines = _ENV_PATH.read_text(encoding="utf-8").splitlines() if _ENV_PATH.exists() else []
    prefix = key + "="
    out: list[str] = []
    found = False
    for ln in lines:
        if ln.startswith(prefix) or ln.startswith(key + " ="):
            out.append(f"{key}={value}")
            found = True
        else:
            out.append(ln)
    if not found:
        out.append(f"{key}={value}")
    _ENV_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")


def update_llm_config(
    base_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> None:
    """Update in-memory settings and persist changed values to ``.env``.

    An empty/None ``api_key`` (or one starting with the mask char) keeps the
    existing key, so the UI can save URL/model changes without re-entering it.
    """
    if base_url and base_url.strip():
        settings.llm_base_url = base_url.strip()
        _set_env_key("LLM_BASE_URL", settings.llm_base_url)
    if model and model.strip():
        settings.llm_model = model.strip()
        _set_env_key("LLM_MODEL", settings.llm_model)
    if api_key and api_key.strip() and not api_key.strip().startswith("•"):
        settings.llm_api_key = api_key.strip()
        _set_env_key("LLM_API_KEY", settings.llm_api_key)
