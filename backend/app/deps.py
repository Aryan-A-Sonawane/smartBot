"""Dependency-injection providers used by FastAPI ``Depends`` and the executor.

Singletons (Gemini client, tool registry) are created lazily and cached so the
expensive setup happens once per process.
"""

from __future__ import annotations

from functools import lru_cache

from .config import Settings, get_settings
from .gemini_client import GeminiClient
from .tools.registry import ToolRegistry, build_registry


@lru_cache
def get_gemini_client() -> GeminiClient:
    return GeminiClient(get_settings())


@lru_cache
def get_registry() -> ToolRegistry:
    return build_registry()


def get_settings_dep() -> Settings:
    return get_settings()
