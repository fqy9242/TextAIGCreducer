from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.db.session import AsyncSessionFactory
from app.services.bootstrap import bootstrap_defaults
from app.services.detectors import build_detector
from app.services.external_skill_rules import ExternalSkillRulesLoader
from app.services.llm_rewriter import LLMRewriter
from app.services.prompt_manager import PromptManager
from app.services.rewrite_agent import RewriteAgent
from app.services.system_settings import SystemSettingsService
from app.services.task_worker import TaskWorker


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, debug=settings.debug_enabled)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    prompt_manager = PromptManager(settings.prompts_root)
    system_settings_service = SystemSettingsService(settings)
    detector = build_detector(settings)
    external_rules_loader = ExternalSkillRulesLoader(
        enabled=settings.external_skill_enabled_flag,
        repo_root=settings.external_skill_repo_root,
        mode=settings.external_skill_mode,
        max_items=settings.external_skill_max_items,
    )
    llm_rewriter = LLMRewriter(settings=settings)
    rewrite_agent = RewriteAgent(
        prompt_manager=prompt_manager,
        llm_rewriter=llm_rewriter,
        detector=detector,
        external_rules_loader=external_rules_loader,
        system_settings_service=system_settings_service,
    )
    task_worker = TaskWorker(
        session_factory=AsyncSessionFactory,
        rewrite_agent=rewrite_agent,
        execution_timeout_seconds=settings.task_execution_timeout_seconds,
    )

    app.state.prompt_manager = prompt_manager
    app.state.task_worker = task_worker
    app.state.external_rules_loader = external_rules_loader
    app.state.system_settings_service = system_settings_service

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.on_event("startup")
    async def on_startup() -> None:
        await bootstrap_defaults(AsyncSessionFactory)
        await task_worker.start()

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        await task_worker.stop()

    return app


app = create_app()
