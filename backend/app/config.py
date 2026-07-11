"""Application configuration and the model/price table.

All settings are read from environment variables (see ``.env.example``) using
pydantic-settings so the app is 12-factor friendly and easy to deploy.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Anchor the .env to backend/.env (this file is backend/app/config.py) so it
# loads no matter which directory the server is launched from. A relative
# "path" only works when the CWD happens to be backend/, which is a common
# cause of "the API key isn't detected".
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    """Typed application settings, populated from the environment."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ----- LLM -----
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model_fast: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL_FAST")
    gemini_model_pro: str = Field(default="gemini-2.5-pro", alias="GEMINI_MODEL_PRO")
    gemini_embed_model: str = Field(
        default="models/gemini-embedding-001", alias="GEMINI_EMBED_MODEL"
    )
    # Flash-only by default. Pro has far lower rate limits, so escalating hard
    # tasks to it (and the flash->pro fallback) is opt-in via GEMINI_USE_PRO.
    use_pro: bool = Field(default=False, alias="GEMINI_USE_PRO")

    # ----- CORS -----
    allowed_origins: str = Field(default="http://localhost:3000", alias="ALLOWED_ORIGINS")

    # ----- Extraction -----
    whisper_model: str = Field(default="base", alias="WHISPER_MODEL")
    max_file_mb: int = Field(default=25, alias="MAX_FILE_MB")

    @property
    def origins_list(self) -> list[str]:
        """Parse the comma-separated CORS origins into a list."""
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def has_llm(self) -> bool:
        """Whether a Gemini API key is configured."""
        return bool(self.gemini_api_key.strip())

    def model_for(self, prefer_pro: bool) -> str:
        """Pick the model for a call: pro only when it's enabled AND the planner
        judged the task hard; otherwise the fast (flash) model."""
        if prefer_pro and self.use_pro:
            return self.gemini_model_pro
        return self.gemini_model_fast


# Gemini pricing (USD per 1M tokens). Used by the cost estimator. These are
# approximate published rates and easy to update in one place.
PRICE_TABLE: dict[str, dict[str, float]] = {
    # Current models (standard tier, prompts <= 200k tokens) per Gemini API pricing.
    "gemini-2.5-flash": {"in": 0.30, "out": 2.50},
    "gemini-2.5-pro": {"in": 1.25, "out": 10.00},
    "gemini-2.5-flash-lite": {"in": 0.10, "out": 0.40},
    # Legacy (retired) — kept so old configs still cost-estimate.
    "gemini-2.0-flash": {"in": 0.075, "out": 0.30},
    "gemini-1.5-pro": {"in": 1.25, "out": 5.00},
    "gemini-1.5-flash": {"in": 0.075, "out": 0.30},
}


def price_for(model: str) -> dict[str, float]:
    """Return the {in, out} price per 1M tokens for a model, with a default."""
    return PRICE_TABLE.get(model, {"in": 0.30, "out": 2.50})


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton (used as a FastAPI dependency)."""
    return Settings()
