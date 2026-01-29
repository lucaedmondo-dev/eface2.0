from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..cloud import CloudAuthError, get_cloud_settings, validate_cloud_token
from ..core import (
    API_TOKEN,
    create_access_token,
    get_user,
    read_config,
    verify_user_password,
    write_config,
)

router = APIRouter()


class AuthPayload(BaseModel):
    # support either token-based login or username/password
    token: str | None = None
    cloud_token: str | None = None
    instance_id: str | None = None
    username: str | None = None
    password: str | None = None
    remote_host: str | None = None
    remote_token: str | None = None


@router.post("/login")
def login(payload: AuthPayload):
    # username/password login (internal panel)
    if payload.username and payload.password:
        # allow admin stored in config to login
        data = read_config()
        admin = data.get('admin', {})
        if payload.username == admin.get('username'):
            from ..core import verify_admin_password
            if verify_admin_password(payload.password):
                token = create_access_token(payload.username, is_admin=True, must_change=False)
                return {"access_token": token, "token_type": "bearer", "is_admin": True, "must_change": False}

        # verify against users list
        if verify_user_password(payload.username, payload.password):
            u = get_user(payload.username)
            is_admin = bool(u.get('is_admin'))
            must_change = bool(u.get('must_change'))
            token = create_access_token(payload.username, is_admin=is_admin, must_change=must_change)
            return {"access_token": token, "token_type": "bearer", "is_admin": is_admin, "must_change": must_change}
        raise HTTPException(status_code=401, detail="Bad credentials")

    # token-based login (legacy/dev)
    if payload.token and payload.token == API_TOKEN:
        # legacy token flow: persist remote integration if provided and return legacy token for compatibility
        if payload.remote_host:
            data = read_config()
            adv = data.get("advanced", {}) or {}
            adv["integration"] = {
                "host": payload.remote_host,
                "token": payload.remote_token,
                "enabled": True,
            }
            data["advanced"] = adv
            write_config(data)
        return {"access_token": API_TOKEN, "token_type": "bearer", "is_admin": False}

    # cloud token login
    if payload.cloud_token:
        settings = get_cloud_settings()
        force_local_password = bool(settings.get("require_local_password", True))
        try:
            cloud_info = validate_cloud_token(payload.cloud_token, payload.instance_id)
        except CloudAuthError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        integration_override = _resolve_cloud_integration(cloud_info)
        if not integration_override:
            raise HTTPException(status_code=400, detail="Cloud instance not configured locally")
        _persist_cloud_session(cloud_info, integration_override)
        if not force_local_password:
            if integration_override.get("host") and integration_override.get("token"):
                token = create_access_token(
                    cloud_info.get("username") or "cloud_user",
                    is_admin=bool(cloud_info.get("is_admin")),
                    must_change=bool(cloud_info.get("must_change")),
                )
                return {
                    "access_token": token,
                    "token_type": "bearer",
                    "is_admin": bool(cloud_info.get("is_admin")),
                    "must_change": bool(cloud_info.get("must_change")),
                }
        return {
            "require_password": True,
            "username": cloud_info.get("username"),
            "instance_id": cloud_info.get("instance_id"),
            "provider": settings.get("provider"),
        }

    raise HTTPException(status_code=401, detail="Bad token")


def _resolve_cloud_integration(cloud_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    ha_info = cloud_info.get("ha") or {}
    if ha_info.get("host") and ha_info.get("token"):
        return ha_info
    instance_id = cloud_info.get("instance_id")
    if not instance_id:
        return None
    data = read_config()
    pool = data.get("cloud_instances") or []
    for item in pool:
        if item.get("instance_id") == instance_id:
            integration = item.get("integration") or {}
            if integration.get("host") and integration.get("token"):
                return integration
    return None


def _persist_cloud_session(cloud_info: Dict[str, Any], resolved_integration: Dict[str, Any]) -> None:
    data = read_config()
    advanced = data.get("advanced") or {}
    integration = advanced.get("integration") or {}
    source = resolved_integration or (cloud_info.get("ha") or {})
    if source.get("host"):
        integration["host"] = source["host"]
    if source.get("token"):
        integration["token"] = source["token"]
    for key in ("path", "remote_host", "remote_token", "remote_path"):
        if source.get(key):
            integration[key] = source[key]
    integration["enabled"] = True
    advanced["integration"] = integration
    data["advanced"] = advanced

    context = data.get("cloud_context") or {}
    context.update(
        {
            "user_id": cloud_info.get("user_id"),
            "username": cloud_info.get("username"),
            "instance_id": cloud_info.get("instance_id"),
            "last_login_at": datetime.now(timezone.utc).isoformat(),
            "pending_username": cloud_info.get("username"),
        }
    )
    if cloud_info.get("preferences"):
        context["preferences"] = cloud_info["preferences"]
    data["cloud_context"] = context

    write_config(data)
