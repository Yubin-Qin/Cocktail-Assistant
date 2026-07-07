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
