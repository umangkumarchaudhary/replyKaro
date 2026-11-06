# -*- coding: utf-8 -*-

"""

    Module :mod:`core.utils.config`

    Environment-driven settings shared by every package. Values come from
    environment variables or a ``.env`` file in the working directory.

"""

# ----------- START: Native Imports ---------- #
from functools import lru_cache
# ----------- END: Native Imports ---------- #

# ----------- START: Third Party Imports ---------- #
from pydantic_settings import BaseSettings, SettingsConfigDict
# ----------- END: Third Party Imports ---------- #

__all__ = ["Settings", "get_settings"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./replykaro.db"
    anthropic_api_key: str | None = None

    # Everyday customer chats run on Haiku (cheap + fast); change with CHAT_MODEL.
    chat_model: str = "claude-haiku-5-5"
    chat_effort: str = "low"
    max_tokens: int = 4096
    max_tool_rounds: int = 5
    history_limit: int = 20  # last N messages sent to the model


@lru_cache
def get_settings() -> Settings:
    return Settings()
