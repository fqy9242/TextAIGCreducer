from __future__ import annotations

import uuid

import pytest


async def _login(client, username: str, password: str) -> dict:
    resp = await client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.mark.asyncio
async def test_authorization_scope_enforced(client) -> None:
    admin = await _login(client, "admin", "Admin@123456")
    admin_headers = {"Authorization": f"Bearer {admin['access_token']}"}

    viewer_name = f"viewer_{uuid.uuid4().hex[:8]}"
    operator_name = f"operator_{uuid.uuid4().hex[:8]}"

    for username, role in [(viewer_name, "viewer"), (operator_name, "operator")]:
        create_resp = await client.post(
            "/api/v1/users",
            json={"username": username, "password": "Passw0rd!", "role": role},
            headers=admin_headers,
        )
        assert create_resp.status_code == 200, create_resp.text

    viewer = await _login(client, viewer_name, "Passw0rd!")
    operator = await _login(client, operator_name, "Passw0rd!")
    viewer_headers = {"Authorization": f"Bearer {viewer['access_token']}"}
    operator_headers = {"Authorization": f"Bearer {operator['access_token']}"}

    viewer_create_task = await client.post(
        "/api/v1/tasks",
        json={
            "input_text": "viewer 尝试创建任务，这段文本长度足够用于验证权限控制逻辑。",
            "target_score": 20,
            "max_rounds": 3,
            "style": "deai_external",
        },
        headers=viewer_headers,
    )
    assert viewer_create_task.status_code == 403

    operator_create_task = await client.post(
        "/api/v1/tasks",
        json={
            "input_text": "operator 创建任务用于检查 viewer 是否可以访问非本人任务。",
            "target_score": 20,
            "max_rounds": 3,
            "style": "deai_external",
        },
        headers=operator_headers,
    )
    assert operator_create_task.status_code == 200, operator_create_task.text
    task_id = operator_create_task.json()["id"]

    viewer_read_other = await client.get(f"/api/v1/tasks/{task_id}", headers=viewer_headers)
    assert viewer_read_other.status_code == 403

    operator_update_prompt = await client.put(
        "/api/v1/prompts/style/deai_external",
        json={
            "version": "1.0.0",
            "variables": ["text"],
            "system": "",
            "human": "",
            "instruction": "test",
        },
        headers=operator_headers,
    )
    assert operator_update_prompt.status_code == 403

    operator_update_settings = await client.put(
        "/api/v1/system-settings/runtime",
        json={
            "default_target_score": 18,
            "default_max_rounds": 4,
            "default_style": "deai_external",
            "use_mock_llm": "true",
            "openai_base_url": "https://api.openai.com/v1",
            "openai_model": "gpt-4o-mini",
            "openai_timeout_seconds": 60,
            "openai_max_retries": 0,
        },
        headers=operator_headers,
    )
    assert operator_update_settings.status_code == 403


@pytest.mark.asyncio
async def test_bootstrap_admin_role_is_immutable(client) -> None:
    admin = await _login(client, "admin", "Admin@123456")
    admin_headers = {"Authorization": f"Bearer {admin['access_token']}"}

    users_resp = await client.get("/api/v1/users", headers=admin_headers)
    assert users_resp.status_code == 200, users_resp.text
    users = users_resp.json()
    admin_user = next((item for item in users if item["username"] == "admin"), None)
    assert admin_user is not None

    patch_resp = await client.patch(
        f"/api/v1/users/{admin_user['id']}/role",
        json={"role": "viewer"},
        headers=admin_headers,
    )
    assert patch_resp.status_code == 403
    assert "immutable" in patch_resp.text.lower()
