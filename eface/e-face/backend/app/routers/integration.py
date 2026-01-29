from fastapi import APIRouter, Depends, HTTPException
from ..core import read_config, require_token

router = APIRouter()


def _integration_settings():
    cfg = read_config()
    return (cfg.get('advanced') or {}).get('integration') or {}


@router.get("/ws-info")
def get_ws_info(_=Depends(require_token)):
    integration = _integration_settings()
    if not integration or not integration.get('enabled'):
        raise HTTPException(status_code=503, detail="integration_missing")
    host = integration.get('host')
    token = integration.get('token')
    remote_host = integration.get('remote_host')
    remote_path = integration.get('remote_ws_path') or integration.get('ws_path') or '/api/websocket'
    if not host or not token:
        raise HTTPException(status_code=503, detail="integration_missing")

    # allow integrators to disable direct client connections explicitly
    if integration.get('direct_ws_disabled'):
        return {"direct_enabled": False, "host": host, "path": integration.get('ws_path') or '/api/websocket', "remote_host": remote_host, "remote_path": remote_path}

    return {
        "direct_enabled": True,
        "host": host,
        "token": token,
        "path": integration.get('ws_path') or '/api/websocket',
        "remote_host": remote_host,
        "remote_path": remote_path
    }
