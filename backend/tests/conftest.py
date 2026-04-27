from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Awaitable, Callable

from unittest.mock import patch

import httpx
import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager


ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT_DIR / "backend"
PROMPTS_DIR = ROOT_DIR / "prompts" / "zh-CN"
DB_PATH = Path(tempfile.gettempdir()) / "text_aigc_reducer_test.db"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{DB_PATH.as_posix()}")
os.environ.setdefault("SYNC_DATABASE_URL", f"sqlite:///{DB_PATH.as_posix()}")
os.environ.setdefault("PROMPTS_ROOT", str(PROMPTS_DIR))
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ADMIN_BOOTSTRAP_USERNAME", "admin")
os.environ.setdefault("ADMIN_BOOTSTRAP_PASSWORD", "Admin@123456")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")
os.environ.setdefault("OPENAI_API_KEY", "test-key")


from app.core.config import get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import engine  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()


@pytest_asyncio.fixture(autouse=True)
async def prepare_database() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def app():
    application = create_app()
    async with LifespanManager(application):
        yield application


@pytest_asyncio.fixture(autouse=True)
async def mock_openai_ainvoke():
    with patch("langchain_openai.ChatOpenAI.ainvoke") as mock_ainvoke:
        class DummyResult:
            content = '{"score": 20, "label": "human_like", "reason": "mocked in tests"}'
        mock_ainvoke.return_value = DummyResult()
        yield mock_ainvoke



@pytest_asyncio.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client


@pytest_asyncio.fixture
async def login_as(client) -> Callable[[str, str], Awaitable[dict[str, Any]]]:
    async def _login(username: str, password: str) -> dict[str, Any]:
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": password},
        )
        assert response.status_code == 200, response.text
        return response.json()

    return _login
