from __future__ import annotations

from pathlib import Path


def test_initial_migration_contains_required_tables() -> None:
    migration_file = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0001_initial.py"
    assert migration_file.exists()
    content = migration_file.read_text(encoding="utf-8")
    for table in ["users", "roles", "user_roles", "rewrite_tasks", "task_iterations", "audit_logs"]:
        assert f"\"{table}\"" in content


def test_task_logs_migration_exists() -> None:
    migration_file = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0002_add_task_logs.py"
    assert migration_file.exists()
    content = migration_file.read_text(encoding="utf-8")
    assert "\"task_logs\"" in content


def test_system_settings_migration_exists() -> None:
    migration_file = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "0003_add_system_settings.py"
    assert migration_file.exists()
    content = migration_file.read_text(encoding="utf-8")
    assert "\"system_settings\"" in content
