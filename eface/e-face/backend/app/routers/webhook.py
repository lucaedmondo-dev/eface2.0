from __future__ import annotations

import json
from collections import deque
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Request

from ..ha_ws import broadcast
from ..core import require_token

router = APIRouter(prefix="/api/webhook", tags=["webhook"])
_RECENT_WEBHOOKS = deque(maxlen=50)


def _safe_headers(request: Request) -> dict[str, str]:
    return {key.lower(): value for key, value in request.headers.items() if key and value}


async def _extract_payload(request: Request) -> Any:
    body_bytes = await request.body()
    if not body_bytes:
        return None
    content_type = (request.headers.get("content-type") or "").split(";")[0].strip().lower()
    if content_type == "application/json":
        try:
            return json.loads(body_bytes)
        except json.JSONDecodeError:
            return body_bytes.decode("utf-8", errors="ignore") or None
    try:
        return body_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return body_bytes.hex()


@router.post("/{webhook_id}")
async def accept_webhook(webhook_id: str, request: Request):
    payload = await _extract_payload(request)
    entry = {
        "webhook_id": webhook_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
        "headers": _safe_headers(request),
        "client": request.client.host if request.client else None,
    }
    _RECENT_WEBHOOKS.append(entry)
    try:
        await broadcast({"type": "webhook_event", "webhook_id": webhook_id, "payload": payload})
    except Exception:
        # Broadcast failures should not prevent webhook acknowledgement
        pass
    return {"status": "accepted"}


@router.get("/recent")
async def recent_webhooks(_=Depends(require_token)):
    return list(_RECENT_WEBHOOKS)
