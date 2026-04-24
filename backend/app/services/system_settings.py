from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.db.models import SystemSettings
from app.schemas.system_settings import RuntimeSettingsOut, RuntimeSettingsUpdateRequest
from app.services.prompt_manager import PromptManager


SYSTEM_SETTINGS_ROW_ID = 1


class SystemSettingsService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def build_default_values(self) -> RuntimeSettingsUpdateRequest:
        return RuntimeSettingsUpdateRequest(
            default_target_score=self.settings.default_target_score,
            default_max_rounds=self.settings.default_max_rounds,
            default_style=self.settings.default_style,
            use_mock_llm=self._normalize_mock_mode(self.settings.use_mock_llm),
            openai_base_url=self.settings.openai_base_url,
            openai_model=self.settings.openai_model,
            openai_timeout_seconds=self.settings.openai_timeout_seconds,
            openai_max_retries=max(0, self.settings.openai_max_retries),
        )

    async def ensure_initialized(self, session: AsyncSession) -> None:
        row = await session.get(SystemSettings, SYSTEM_SETTINGS_ROW_ID)
        if row is not None:
            return

        session.add(
            SystemSettings(
                id=SYSTEM_SETTINGS_ROW_ID,
                payload=self.build_default_values().model_dump(),
            )
        )
        await session.commit()

    async def get_runtime_settings(
        self,
        session: AsyncSession,
        prompt_manager: PromptManager,
    ) -> RuntimeSettingsOut:
        row = await session.get(SystemSettings, SYSTEM_SETTINGS_ROW_ID)
        values = self._merge_payload(row.payload if row is not None else {})
        available_styles = self._list_available_styles(prompt_manager)
        default_style = self._resolve_default_style(values.default_style, available_styles)

        return RuntimeSettingsOut(
            **{
                **values.model_dump(),
                "default_style": default_style,
                "available_styles": available_styles,
                "has_openai_api_key": bool(self.settings.openai_api_key.strip()),
                "effective_llm_mode": self.resolve_llm_mode(values),
            }
        )

    async def update_runtime_settings(
        self,
        session: AsyncSession,
        prompt_manager: PromptManager,
        payload: RuntimeSettingsUpdateRequest,
    ) -> RuntimeSettingsOut:
        available_styles = self._list_available_styles(prompt_manager)
        if available_styles and payload.default_style not in available_styles:
            raise ValueError(f"default_style must be one of: {', '.join(available_styles)}")

        row = await session.get(SystemSettings, SYSTEM_SETTINGS_ROW_ID)
        if row is None:
            row = SystemSettings(id=SYSTEM_SETTINGS_ROW_ID, payload=payload.model_dump())
            session.add(row)
        else:
            row.payload = payload.model_dump()

        await session.flush()
        available_styles = self._list_available_styles(prompt_manager)
        return RuntimeSettingsOut(
            **{
                **payload.model_dump(),
                "available_styles": available_styles,
                "has_openai_api_key": bool(self.settings.openai_api_key.strip()),
                "effective_llm_mode": self.resolve_llm_mode(payload),
            }
        )

    def resolve_llm_mode(self, values: RuntimeSettingsUpdateRequest | RuntimeSettingsOut) -> str:
        return "mock" if self.should_use_mock_llm(values) else "real"

    def should_use_mock_llm(self, values: RuntimeSettingsUpdateRequest | RuntimeSettingsOut) -> bool:
        mode = values.use_mock_llm.strip().lower()
        if mode == "true":
            return True
        if mode == "false":
            return False
        return not bool(self.settings.openai_api_key.strip())

    def _merge_payload(self, payload: object) -> RuntimeSettingsUpdateRequest:
        defaults = self.build_default_values().model_dump()
        if isinstance(payload, dict):
            defaults.update(payload)
        return RuntimeSettingsUpdateRequest.model_validate(defaults)

    def _list_available_styles(self, prompt_manager: PromptManager) -> list[str]:
        items = {
            item.name.strip()
            for item in prompt_manager.list_metadata()
            if item.group == "style" and item.name.strip()
        }
        if items:
            return sorted(items)
        fallback = self.settings.default_style.strip()
        return [fallback] if fallback else []

    def _resolve_default_style(self, default_style: str, available_styles: list[str]) -> str:
        if not available_styles:
            return default_style
        if default_style in available_styles:
            return default_style
        if self.settings.default_style in available_styles:
            return self.settings.default_style
        return available_styles[0]

    @staticmethod
    def _normalize_mock_mode(value: str) -> str:
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on", "mock"}:
            return "true"
        if normalized in {"0", "false", "no", "off", "real"}:
            return "false"
        return "auto"
