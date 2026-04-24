from __future__ import annotations

import uuid

import pytest


async def _login(client, username: str, password: str) -> dict:
    response = await client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_runtime_settings_can_be_read_and_updated(client) -> None:
    admin = await _login(client, "admin", "Admin@123456")
    admin_headers = {"Authorization": f"Bearer {admin['access_token']}"}

    initial_resp = await client.get("/api/v1/system-settings/runtime", headers=admin_headers)
    assert initial_resp.status_code == 200, initial_resp.text
    initial_payload = initial_resp.json()
    assert "deai_external" in initial_payload["available_styles"]

    update_resp = await client.put(
        "/api/v1/system-settings/runtime",
        json={
            "default_target_score": 18,
            "default_max_rounds": 4,
            "default_style": "deai_external",
            "use_mock_llm": "true",
            "openai_base_url": "https://example.com/v1",
            "openai_model": "demo-model",
            "openai_timeout_seconds": 120,
            "openai_max_retries": 2,
        },
        headers=admin_headers,
    )
    assert update_resp.status_code == 200, update_resp.text
    updated = update_resp.json()
    assert updated["default_target_score"] == 18
    assert updated["default_max_rounds"] == 4
    assert updated["use_mock_llm"] == "true"
    assert updated["openai_base_url"] == "https://example.com/v1"
    assert updated["openai_model"] == "demo-model"
    assert updated["openai_timeout_seconds"] == 120
    assert updated["openai_max_retries"] == 2
    assert updated["effective_llm_mode"] == "mock"

    reload_resp = await client.get("/api/v1/system-settings/runtime", headers=admin_headers)
    assert reload_resp.status_code == 200, reload_resp.text
    reloaded = reload_resp.json()
    assert reloaded["default_target_score"] == 18
    assert reloaded["openai_model"] == "demo-model"


@pytest.mark.asyncio
async def test_runtime_settings_drive_task_defaults(client) -> None:
    admin = await _login(client, "admin", "Admin@123456")
    admin_headers = {"Authorization": f"Bearer {admin['access_token']}"}

    operator_name = f"operator_{uuid.uuid4().hex[:8]}"
    create_user_resp = await client.post(
        "/api/v1/users",
        json={"username": operator_name, "password": "Passw0rd!", "role": "operator"},
        headers=admin_headers,
    )
    assert create_user_resp.status_code == 200, create_user_resp.text

    update_resp = await client.put(
        "/api/v1/system-settings/runtime",
        json={
            "default_target_score": 12,
            "default_max_rounds": 5,
            "default_style": "deai_external",
            "use_mock_llm": "true",
            "openai_base_url": "https://api.openai.com/v1",
            "openai_model": "gpt-4o-mini",
            "openai_timeout_seconds": 90,
            "openai_max_retries": 1,
        },
        headers=admin_headers,
    )
    assert update_resp.status_code == 200, update_resp.text

    operator = await _login(client, operator_name, "Passw0rd!")
    operator_headers = {"Authorization": f"Bearer {operator['access_token']}"}

    get_resp = await client.get("/api/v1/system-settings/runtime", headers=operator_headers)
    assert get_resp.status_code == 200, get_resp.text
    assert get_resp.json()["default_target_score"] == 12

    create_task_resp = await client.post(
        "/api/v1/tasks",
        json={
            "input_text": "这是一段用于验证系统设置默认值的测试文本，省略目标分数和轮次后应自动读取数据库中的运行参数。",
        },
        headers=operator_headers,
    )
    assert create_task_resp.status_code == 200, create_task_resp.text
    created = create_task_resp.json()
    assert created["target_score"] == 12
    assert created["max_rounds"] == 5
    assert created["style"] == "deai_external"
