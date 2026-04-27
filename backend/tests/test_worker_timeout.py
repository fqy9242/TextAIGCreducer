from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.security import hash_password
from app.db.models import RewriteTask, User
from app.db.session import AsyncSessionFactory
from app.services.task_worker import TaskWorker


class SlowRewriteAgent:
    async def run_task(self, session, task) -> None:  # noqa: ANN001
        await asyncio.sleep(2)


class CrashRewriteAgent:
    async def run_task(self, session, task) -> None:  # noqa: ANN001
        raise RuntimeError("mock agent crash")


class ConcurrentSuccessAgent:
    def __init__(self) -> None:
        self.active = 0
        self.max_active = 0
        self.started = asyncio.Event()
        self._lock = asyncio.Lock()

    async def run_task(self, session, task) -> None:  # noqa: ANN001
        async with self._lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            if self.max_active >= 2:
                self.started.set()

        try:
            await asyncio.wait_for(self.started.wait(), timeout=1)
            await asyncio.sleep(0.1)
            task.best_text = task.input_text
            task.best_score = 10.0
            task.met_target = True
            task.rounds_used = 1
            task.status = "success"
            task.completed_at = datetime.now(timezone.utc)
            await session.commit()
        finally:
            async with self._lock:
                self.active -= 1


@pytest.mark.asyncio
async def test_worker_marks_task_failed_on_timeout() -> None:
    agent = SlowRewriteAgent()
    worker = TaskWorker(
        session_factory=AsyncSessionFactory,
        rewrite_agent=agent,  # type: ignore[arg-type]
        execution_timeout_seconds=1,
    )

    async with AsyncSessionFactory() as session:
        user = User(username=f"user_{uuid.uuid4().hex[:8]}", password_hash=hash_password("password"))
        task = RewriteTask(
            user=user,
            input_text="这是一段用于验证任务执行超时处理逻辑的文本，长度足够。",
            target_score=20,
            max_rounds=3,
            style="deai_external",
            status="queued",
        )
        session.add_all([user, task])
        await session.commit()
        await session.refresh(task)

    await worker._process_task(task.id)

    async with AsyncSessionFactory() as session:
        loaded = await session.scalar(
            select(RewriteTask)
            .options(selectinload(RewriteTask.logs))
            .where(RewriteTask.id == task.id)
        )

    assert loaded is not None
    assert loaded.status == "failed"
    assert loaded.error_message is not None
    assert "timeout" in loaded.error_message.lower()
    assert len(loaded.logs) >= 2


@pytest.mark.asyncio
async def test_worker_marks_task_failed_on_agent_exception() -> None:
    agent = CrashRewriteAgent()
    worker = TaskWorker(
        session_factory=AsyncSessionFactory,
        rewrite_agent=agent,  # type: ignore[arg-type]
        execution_timeout_seconds=5,
    )

    async with AsyncSessionFactory() as session:
        user = User(username=f"user_{uuid.uuid4().hex[:8]}", password_hash=hash_password("password"))
        task = RewriteTask(
            user=user,
            input_text="这是一段用于验证任务执行异常处理逻辑的文本，长度足够。",
            target_score=20,
            max_rounds=3,
            style="deai_external",
            status="queued",
        )
        session.add_all([user, task])
        await session.commit()
        await session.refresh(task)

    await worker._process_task(task.id)

    async with AsyncSessionFactory() as session:
        loaded = await session.scalar(
            select(RewriteTask)
            .options(selectinload(RewriteTask.logs))
            .where(RewriteTask.id == task.id)
        )

    assert loaded is not None
    assert loaded.status == "failed"
    assert loaded.error_message is not None
    assert "mock agent crash" in loaded.error_message
    assert len(loaded.logs) >= 2


@pytest.mark.asyncio
async def test_worker_processes_multiple_tasks_concurrently() -> None:
    agent = ConcurrentSuccessAgent()
    worker = TaskWorker(
        session_factory=AsyncSessionFactory,
        rewrite_agent=agent,  # type: ignore[arg-type]
        execution_timeout_seconds=5,
        worker_concurrency=2,
    )

    async with AsyncSessionFactory() as session:
        user = User(username=f"user_{uuid.uuid4().hex[:8]}", password_hash=hash_password("password"))
        tasks = [
            RewriteTask(
                user=user,
                input_text=f"这是一段用于验证并发任务执行能力的文本_{index}，长度足够。",
                target_score=20,
                max_rounds=3,
                style="deai_external",
                status="queued",
            )
            for index in range(2)
        ]
        session.add(user)
        session.add_all(tasks)
        await session.commit()
        for task in tasks:
            await session.refresh(task)

    await worker.start()
    for task in tasks:
        await worker.enqueue(task.id)
    await asyncio.wait_for(worker.queue.join(), timeout=3)
    await worker.stop()

    async with AsyncSessionFactory() as session:
        loaded_tasks = (
            await session.scalars(
                select(RewriteTask)
                .options(selectinload(RewriteTask.logs))
                .where(RewriteTask.id.in_([task.id for task in tasks]))
            )
        ).all()

    assert agent.max_active >= 2
    assert len(loaded_tasks) == 2
    assert all(task.status == "success" for task in loaded_tasks)
    assert all(task.completed_at is not None for task in loaded_tasks)


@pytest.mark.asyncio
async def test_worker_marks_running_task_cancelled() -> None:
    agent = SlowRewriteAgent()
    worker = TaskWorker(
        session_factory=AsyncSessionFactory,
        rewrite_agent=agent,  # type: ignore[arg-type]
        execution_timeout_seconds=5,
    )

    async with AsyncSessionFactory() as session:
        user = User(username=f"user_{uuid.uuid4().hex[:8]}", password_hash=hash_password("password"))
        task = RewriteTask(
            user=user,
            input_text="这是一段用于验证运行中任务取消状态的文本，长度足够。",
            target_score=20,
            max_rounds=3,
            style="deai_external",
            status="queued",
        )
        session.add_all([user, task])
        await session.commit()
        await session.refresh(task)

    await worker.start()
    await worker.enqueue(task.id)

    for _ in range(20):
        async with AsyncSessionFactory() as session:
            loaded = await session.scalar(select(RewriteTask).where(RewriteTask.id == task.id))
        if loaded is not None and loaded.status == "running":
            break
        await asyncio.sleep(0.05)

    was_cancelled = await worker.cancel_task(task.id)
    assert was_cancelled is True

    await asyncio.wait_for(worker.queue.join(), timeout=3)
    await worker.stop()

    async with AsyncSessionFactory() as session:
        loaded = await session.scalar(
            select(RewriteTask)
            .options(selectinload(RewriteTask.logs))
            .where(RewriteTask.id == task.id)
        )

    assert loaded is not None
    assert loaded.status == "cancelled"
    assert loaded.error_message == "任务已手动取消。"
    assert any(log.message == "任务已手动取消。" for log in loaded.logs)
