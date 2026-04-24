from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class TaskCreateRequest(BaseModel):
    input_text: str = Field(min_length=20, max_length=20000)
    target_score: float | None = Field(default=None, ge=1, le=100)
    max_rounds: int | None = Field(default=None, ge=1, le=10)
    style: str | None = Field(default=None, min_length=1, max_length=64)


class TaskIterationOut(BaseModel):
    round: int
    prompt_version: str
    rewritten_text: str
    detector_score: float
    detector_label: str
    llm_mode: str | None = None
    latency_ms: int
    created_at: datetime


class TaskLogOut(BaseModel):
    level: str
    stage: str
    message: str
    detail: dict = Field(default_factory=dict)
    created_at: datetime


class TaskResultOut(BaseModel):
    id: str
    status: str
    input_text: str
    best_text: str | None
    best_score: float | None
    met_target: bool
    target_score: float
    max_rounds: int
    rounds_used: int
    style: str
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None
    elapsed_seconds: int | None = None
    iterations: list[TaskIterationOut] = Field(default_factory=list)
    logs: list[TaskLogOut] = Field(default_factory=list)


class TaskListItemOut(BaseModel):
    id: str
    status: str
    target_score: float
    best_score: float | None
    met_target: bool
    rounds_used: int
    style: str
    created_at: datetime
    completed_at: datetime | None
    elapsed_seconds: int | None = None


class TaskListResponse(BaseModel):
    items: list[TaskListItemOut]
    total: int
    page: int
    page_size: int
