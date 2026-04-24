from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.models import RewriteTask
from app.services.rewrite_agent import RewriteAgent
from app.services.task_log import add_task_log


logger = logging.getLogger(__name__)


class TaskWorker:
    def __init__(
        self,
        session_factory: async_sessionmaker,
        rewrite_agent: RewriteAgent,
        execution_timeout_seconds: int = 180,
    ):
        self.session_factory = session_factory
        self.rewrite_agent = rewrite_agent
        self.execution_timeout_seconds = max(1, execution_timeout_seconds)
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        await self.recover_pending_tasks()
        self._worker_task = asyncio.create_task(self._worker_loop(), name="rewrite-task-worker")

    async def stop(self) -> None:
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None

    async def enqueue(self, task_id: str) -> None:
        await self.queue.put(task_id)

    async def recover_pending_tasks(self) -> None:
        async with self.session_factory() as session:
            result = await session.scalars(
                select(RewriteTask.id).where(RewriteTask.status.in_(["queued", "running"]))
            )
            for task_id in result.all():
                await self.queue.put(task_id)

    async def _worker_loop(self) -> None:
        while self._running:
            task_id = await self.queue.get()
            try:
                await self._process_task(task_id)
            except Exception as exc:  # pragma: no cover - defensive guard
                logger.exception("Task worker loop failed for task_id=%s: %s", task_id, exc)
                await self._mark_task_failed(task_id, str(exc))
            finally:
                self.queue.task_done()

    async def _process_task(self, task_id: str) -> None:
        async with self.session_factory() as session:
            task = await session.scalar(select(RewriteTask).where(RewriteTask.id == task_id))
            if task is None:
                return
            if task.status not in {"queued", "running"}:
                return

            task.status = "running"
            if task.started_at is None:
                task.started_at = datetime.now(timezone.utc)
            await add_task_log(
                session,
                task_id=task.id,
                stage="worker",
                level="info",
                message="任务进入执行队列，开始处理。",
                detail={"status": task.status},
            )
            await session.commit()

            try:
                await asyncio.wait_for(
                    self.rewrite_agent.run_task(session, task),
                    timeout=self.execution_timeout_seconds,
                )
            except asyncio.TimeoutError:
                await session.rollback()
                await self._fail_task(
                    session=session,
                    task_id=task_id,
                    error_message=f"Task execution timeout after {self.execution_timeout_seconds} seconds",
                    message="任务执行超时，已终止。",
                    detail={"timeout_seconds": self.execution_timeout_seconds},
                )
            except Exception as exc:
                await session.rollback()
                detail = {"error": str(exc), "error_type": type(exc).__name__}
                if type(exc).__name__ == "APITimeoutError":
                    timeout_seconds = None
                    if hasattr(self.rewrite_agent, "get_runtime_settings"):
                        try:
                            runtime_settings = await self.rewrite_agent.get_runtime_settings(session)
                            timeout_seconds = runtime_settings.openai_timeout_seconds
                        except Exception:  # pragma: no cover - fallback hint only
                            timeout_seconds = None
                    detail["openai_timeout_seconds"] = timeout_seconds
                    detail["hint"] = (
                        "Increase openai_timeout_seconds in system settings "
                        "or check openai_base_url/model/network."
                    )
                await self._fail_task(
                    session=session,
                    task_id=task_id,
                    error_message=str(exc),
                    message="任务执行失败。",
                    detail=detail,
                )

    async def _mark_task_failed(self, task_id: str, message: str) -> None:
        async with self.session_factory() as session:
            task = await session.scalar(select(RewriteTask).where(RewriteTask.id == task_id))
            if task is None:
                return
            task.status = "failed"
            task.error_message = message[:2000]
            task.completed_at = datetime.now(timezone.utc)
            await add_task_log(
                session,
                task_id=task.id,
                stage="worker",
                level="error",
                message="任务执行器出现异常，任务被标记为失败。",
                detail={"error": message[:2000]},
            )
            await session.commit()

    async def _fail_task(
        self,
        *,
        session: AsyncSession,
        task_id: str,
        error_message: str,
        message: str,
        detail: dict,
    ) -> None:
        task = await session.scalar(select(RewriteTask).where(RewriteTask.id == task_id))
        if task is None:
            return
        task.status = "failed"
        task.error_message = error_message[:2000]
        task.completed_at = datetime.now(timezone.utc)
        await add_task_log(
            session,
            task_id=task_id,
            stage="worker",
            level="error",
            message=message,
            detail=detail,
        )
        await session.commit()
