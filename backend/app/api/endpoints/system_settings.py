from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session, require_permission
from app.db.models import User
from app.schemas.system_settings import RuntimeSettingsOut, RuntimeSettingsUpdateRequest
from app.services.audit import write_audit_log
from app.services.rbac import PERM_USER_MANAGE


router = APIRouter(prefix="/system-settings", tags=["system-settings"])


@router.get("/runtime", response_model=RuntimeSettingsOut)
async def get_runtime_settings(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_user),
) -> RuntimeSettingsOut:
    service = request.app.state.system_settings_service
    prompt_manager = request.app.state.prompt_manager
    return await service.get_runtime_settings(session, prompt_manager)


@router.put("/runtime", response_model=RuntimeSettingsOut)
async def update_runtime_settings(
    payload: RuntimeSettingsUpdateRequest,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    admin: User = Depends(require_permission(PERM_USER_MANAGE)),
) -> RuntimeSettingsOut:
    service = request.app.state.system_settings_service
    prompt_manager = request.app.state.prompt_manager
    try:
        updated = await service.update_runtime_settings(session, prompt_manager, payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    await write_audit_log(
        session,
        action="system_settings.runtime_update",
        user_id=admin.id,
        detail=payload.model_dump(),
    )
    await session.commit()
    return updated
