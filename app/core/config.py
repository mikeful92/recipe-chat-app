import os
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recipe_generator: Literal["stub", "openai"] = "stub"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"

    @model_validator(mode="after")
    def _validate_openai(self) -> "Settings":
        if self.recipe_generator == "openai" and not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when RECIPE_GENERATOR=openai")
        return self


@lru_cache
def get_settings() -> Settings:
    raw = {
        "recipe_generator": os.getenv("RECIPE_GENERATOR", "stub").strip().lower(),
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
        "openai_model": os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
    }
    try:
        return Settings.model_validate(raw)
    except ValidationError as exc:
        raise RuntimeError(f"Invalid configuration: {exc}") from exc
