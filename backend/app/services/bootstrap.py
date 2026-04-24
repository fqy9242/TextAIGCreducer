from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.models import Role, User
from app.services.audit import write_audit_log
from app.services.system_settings import SystemSettingsService


ROLE_DESCRIPTIONS = {
    "admin": "System administrator",
    "operator": "Task operator",
    "viewer": "Read-only user",
}


async def bootstrap_defaults(session_factory: async_sessionmaker) -> None:
    settings = get_settings()
    system_settings_service = SystemSettingsService(settings)
    async with session_factory() as session:
        await ensure_roles(session)
        await system_settings_service.ensure_initialized(session)

        existing_admin = await session.scalar(
            select(User)
            .options(selectinload(User.roles))
            .where(User.username == settings.admin_bootstrap_username)
        )
        if existing_admin is None:
            admin_role = await session.scalar(select(Role).where(Role.name == "admin"))
            assert admin_role is not None

            admin = User(
                username=settings.admin_bootstrap_username,
                password_hash=hash_password(settings.admin_bootstrap_password),
                is_active=True,
            )
            admin.roles.append(admin_role)
            session.add(admin)
            await write_audit_log(
                session,
                action="auth.bootstrap_admin",
                detail={"username": settings.admin_bootstrap_username},
            )
            await session.commit()


async def ensure_roles(session) -> None:
    existing_roles = await session.scalars(select(Role))
    existing_role_names = {role.name for role in existing_roles}

    dirty = False
    for role_name, description in ROLE_DESCRIPTIONS.items():
        if role_name not in existing_role_names:
            session.add(Role(name=role_name, description=description))
            dirty = True

    if dirty:
        await session.commit()
