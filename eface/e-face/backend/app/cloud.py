"""Cloud authentication helpers for e-face."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict

import jwt
import requests

from .core import read_config


DEFAULT_CLOUD_SETTINGS = {
    "enabled": True,
    "mode": "jwt",
    "require_local_password": True,
}


class CloudAuthError(Exception):
    """Raised when a cloud token or configuration is invalid."""


SAFE_CLOUD_KEYS = {
    "enabled",
    "login_url",
    "provider",
    "issuer",
    "audience",
    "mode",
    "support",
    "require_local_password",
}


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes", "on"}
    return bool(value)


def get_cloud_settings() -> Dict[str, Any]:
    data = read_config()
    cloud = data.get("cloud") if isinstance(data.get("cloud"), dict) else {}
    merged: Dict[str, Any] = {**DEFAULT_CLOUD_SETTINGS, **(cloud or {})}
    merged["enabled"] = _coerce_bool(merged.get("enabled"))
    if not merged.get("mode"):
        merged["mode"] = DEFAULT_CLOUD_SETTINGS["mode"]
    return merged


def sanitize_cloud_settings(settings: Dict[str, Any] | None) -> Dict[str, Any]:
    base = settings if isinstance(settings, dict) else {}
    merged = {**DEFAULT_CLOUD_SETTINGS, **base}
    sanitized = {key: merged.get(key) for key in SAFE_CLOUD_KEYS if merged.get(key) is not None}
    sanitized["enabled"] = _coerce_bool(merged.get("enabled"))
    sanitized["mode"] = merged.get("mode") or DEFAULT_CLOUD_SETTINGS["mode"]
    sanitized["require_local_password"] = _coerce_bool(merged.get("require_local_password"))
    return sanitized


def _call_introspection(settings: Dict[str, Any], token: str, instance_id: str | None) -> Dict[str, Any]:
    url = settings.get("introspect_url")
    if not url:
        raise CloudAuthError("Cloud introspection URL not configured")
    payload = {"token": token}
    if instance_id:
        payload["instance_id"] = instance_id
    client_id = settings.get("client_id")
    client_secret = settings.get("client_secret")
    if client_id:
        payload["client_id"] = client_id
    if client_secret:
        payload["client_secret"] = client_secret
    try:
        resp = requests.post(url, json=payload, timeout=float(settings.get("timeout", 8)))
        resp.raise_for_status()
    except Exception as exc:
        raise CloudAuthError(f"Cloud introspection request failed: {exc}") from exc
    try:
        data = resp.json()
    except json.JSONDecodeError as exc:
        raise CloudAuthError("Cloud introspection returned invalid JSON") from exc
    if isinstance(data, dict):
        active = data.get("active")
        valid = data.get("valid")
        if active is False or valid is False:
            raise CloudAuthError("Cloud token was rejected")
    return data


def _decode_jwt(settings: Dict[str, Any], token: str) -> Dict[str, Any]:
    public_key = settings.get("public_key")
    if not public_key:
        raise CloudAuthError("Cloud public key missing")
    audience = settings.get("audience")
    issuer = settings.get("issuer")
    algorithms = settings.get("algorithms") or ["RS256"]
    options = {"verify_aud": bool(audience), "verify_signature": True}
    try:
        return jwt.decode(
            token,
            public_key,
            algorithms=algorithms,
            audience=audience if audience else None,
            issuer=issuer if issuer else None,
            options=options,
        )
    except Exception as exc:
        raise CloudAuthError(f"Cloud token validation failed: {exc}") from exc


def _normalize_payload(raw: Dict[str, Any]) -> Dict[str, Any]:
    payload = raw.get("data") if isinstance(raw.get("data"), dict) else raw
    if not isinstance(payload, dict):
        raise CloudAuthError("Cloud payload missing data")
    user = payload.get("user") or {}
    ha_meta = payload.get("ha") or payload.get("home_assistant") or {}
    username = (
        payload.get("username")
        or user.get("username")
        or user.get("email")
        or payload.get("sub")
        or user.get("id")
    )
    is_admin = payload.get("is_admin")
    if is_admin is None:
        is_admin = user.get("is_admin")
    must_change = payload.get("must_change")
    if must_change is None:
        must_change = user.get("must_change")
    normalized = {
        "username": username or "cloud_user",
        "user_id": payload.get("user_id") or user.get("id") or payload.get("sub") or username,
        "is_admin": _coerce_bool(is_admin),
        "must_change": _coerce_bool(must_change),
        "instance_id": payload.get("instance_id") or ha_meta.get("instance_id"),
        "ha": {
            "host": ha_meta.get("host"),
            "token": ha_meta.get("token"),
            "path": ha_meta.get("path"),
            "remote_host": ha_meta.get("remote_host"),
            "remote_token": ha_meta.get("remote_token"),
            "remote_path": ha_meta.get("remote_path"),
        },
        "preferences": payload.get("preferences") or user.get("preferences") or {},
    }
    return normalized


def validate_cloud_token(token: str, instance_id: str | None = None) -> Dict[str, Any]:
    settings = get_cloud_settings()
    if not settings.get("enabled"):
        raise CloudAuthError("Cloud authentication disabled")
    mode = (settings.get("mode") or "jwt").lower()
    if mode == "introspection":
        raw = _call_introspection(settings, token, instance_id)
    else:
        raw = _decode_jwt(settings, token)
    normalized = _normalize_payload(raw)
    normalized["issued_at"] = datetime.now(timezone.utc).isoformat()
    return normalized
