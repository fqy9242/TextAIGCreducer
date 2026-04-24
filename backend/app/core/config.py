from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Text AIGC Reducer"
    api_v1_prefix: str = "/api/v1"
    debug: str = "false"

    secret_key: str = "replace-this-in-production"
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 60 * 24 * 7
    jwt_algorithm: str = "HS256"

    database_url: str = "sqlite+aiosqlite:///./aigc_reducer.db"
    sync_database_url: str | None = None

    cors_origins: str = Field(default="http://localhost:5173")

    prompts_root: Path = ROOT_DIR / "prompts" / "zh-CN"
    default_target_score: float = 20.0
    default_max_rounds: int = 3
    default_style: str = "deai_external"

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    use_mock_llm: str = "auto"
    openai_timeout_seconds: int = 60
    openai_max_retries: int = 0

    detector_provider: str = "mock"
    detector_http_url: str = "http://127.0.0.1:9000/detect"
    detector_http_timeout_seconds: int = 20
    task_execution_timeout_seconds: int = 1800

    external_skill_enabled: str = "true"
    external_skill_repo_root: Path = ROOT_DIR / "backend" / "skills"
    external_skill_mode: str = "de-AI-writing"
    external_skill_max_items: int = 12

    admin_bootstrap_username: str = "admin"
    admin_bootstrap_password: str = "Admin@123456"

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def debug_enabled(self) -> bool:
        return self.debug.strip().lower() in {"1", "true", "yes", "on", "debug"}

    @property
    def use_mock_llm_flag(self) -> bool:
        value = self.use_mock_llm.strip().lower()
        if value in {"1", "true", "yes", "on", "mock"}:
            return True
        if value in {"0", "false", "no", "off", "real"}:
            return False
        # auto mode: use real model when API key exists, otherwise fall back to mock.
        return not bool(self.openai_api_key.strip())

    @property
    def external_skill_enabled_flag(self) -> bool:
        return self.external_skill_enabled.strip().lower() in {"1", "true", "yes", "on"}

    @property
    def effective_sync_database_url(self) -> str:
        if self.sync_database_url:
            return self.sync_database_url
        if self.database_url.startswith("mysql+aiomysql://"):
            return self.database_url.replace("mysql+aiomysql://", "mysql+pymysql://", 1)
        if self.database_url.startswith("sqlite+aiosqlite://"):
            return self.database_url.replace("sqlite+aiosqlite://", "sqlite://", 1)
        return self.database_url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
