from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


MockLLMMode = Literal["auto", "true", "false"]


class RuntimeSettingsBase(BaseModel):
    default_target_score: float = Field(default=20.0, ge=1, le=100)
    default_max_rounds: int = Field(default=3, ge=1, le=10)
    default_style: str = Field(default="deai_external", min_length=1, max_length=64)
    use_mock_llm: MockLLMMode = Field(default="auto")
    openai_base_url: str = Field(default="https://api.openai.com/v1", min_length=1, max_length=500)
    openai_model: str = Field(default="gpt-4o-mini", min_length=1, max_length=128)
    openai_timeout_seconds: int = Field(default=60, ge=1, le=3600)
    openai_max_retries: int = Field(default=0, ge=0, le=20)

    @field_validator("default_style", "openai_base_url", "openai_model", mode="before")
    @classmethod
    def _strip_string_fields(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class RuntimeSettingsUpdateRequest(RuntimeSettingsBase):
    pass


class RuntimeSettingsOut(RuntimeSettingsBase):
    available_styles: list[str] = Field(default_factory=list)
    has_openai_api_key: bool = False
    effective_llm_mode: Literal["mock", "real"] = "mock"
