from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from ..core import read_config, write_config, require_token, verify_admin_password
from ..core import fetch_ha_rooms, refresh_room_snapshot
from ..ha_ws import get_status
from ..registry_cache import get_registry_snapshot
import requests
import time

def _check_admin(payload, x_admin_pass: str | None):
    # prefer JWT is_admin claim
    if isinstance(payload, dict) and payload.get('is_admin'):
        return True
    # fallback to header admin password
    if x_admin_pass and verify_admin_password(x_admin_pass):
        return True
    return False

router = APIRouter()


class AdminConfigPayload(BaseModel):
    integration: dict | None = None
    rooms: list | None = None


@router.get("")
def get_admin_config(payload=Depends(require_token), x_admin_pass: str | None = Header(None)):
    if not _check_admin(payload, x_admin_pass):
        raise HTTPException(status_code=403, detail="Admin required")
    data = read_config()
    return {"advanced": data.get("advanced", {}), "rooms": data.get("rooms", [])}


@router.post("")
def post_admin_config(payload: AdminConfigPayload, token_payload=Depends(require_token), x_admin_pass: str | None = Header(None)):
    if not _check_admin(token_payload, x_admin_pass):
        raise HTTPException(status_code=403, detail="Admin required")
    data = read_config()
    if payload.integration is not None:
        adv = data.get("advanced", {}) or {}
        adv["integration"] = payload.integration
        data["advanced"] = adv
    if payload.rooms is not None:
        data["rooms"] = payload.rooms
    write_config(data)
    return {"ok": True}


@router.post("/rooms/{room_id}/background")
def set_room_background(room_id: str, payload: dict, token_payload=Depends(require_token), x_admin_pass: str | None = Header(None)):
    bg = payload.get('background', '')
    data = read_config()
    rooms = data.get('rooms', [])
    target = None
    for r in rooms:
        if r.get('id') == room_id:
            target = r
            break

    if not target:
        # room may exist only in the live HA snapshot; synthesize a minimal entry so background can be stored
        integration = (data.get('advanced') or {}).get('integration') or {}
        try:
            live_rooms = fetch_ha_rooms(integration)
        except Exception:
            live_rooms = []
        live = next((r for r in live_rooms if r.get('id') == room_id), None)
        if live:
            target = {
                'id': room_id,
                'name': live.get('name') or room_id,
                'background': '',
                'luci': live.get('luci') or []
            }
            rooms.append(target)

    if not target:
        raise HTTPException(status_code=404, detail='Room not found')

    target['background'] = bg
    data['rooms'] = rooms
    write_config(data)
    return {"ok": True, "room": target}


@router.post('/test-integration')
def test_integration(payload: dict, token_payload=Depends(require_token), x_admin_pass: str | None = Header(None)):
    if not _check_admin(token_payload, x_admin_pass):
        raise HTTPException(status_code=403, detail="Admin required")
    integration = payload.get('integration') or {}
    try:
        rooms = fetch_ha_rooms(integration)
        return { 'ok': True, 'rooms': rooms }
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post('/refresh')
def refresh_configuration(token_payload=Depends(require_token), x_admin_pass: str | None = Header(None)):
    if not _check_admin(token_payload, x_admin_pass):
        raise HTTPException(status_code=403, detail="Admin required")
    data = read_config()
    advanced = data.get('advanced') or {}
    integration = (advanced.get('integration') or {}).copy()
    if not integration.get('enabled'):
        raise HTTPException(status_code=400, detail="integration_disabled")
    if not integration.get('host') or not integration.get('token'):
        raise HTTPException(status_code=400, detail="integration_missing_credentials")
    try:
        snapshot = refresh_room_snapshot(integration, data.get('rooms', []))
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    data['rooms'] = snapshot.get('rooms', [])
    data['synced'] = {
        'tracked_entities': snapshot.get('tracked_entities', []),
        'synced_at': snapshot.get('synced_at'),
        'extra_entities': snapshot.get('extra_entities', [])
    }
    # persist normalized extra entities back into integration config
    integration['extra_entities'] = snapshot.get('extra_entities', [])
    advanced['integration'] = integration
    data['advanced'] = advanced
    write_config(data)

    return {
        'ok': True,
        'rooms_count': len(snapshot.get('rooms', [])),
        'entities_count': len(snapshot.get('tracked_entities', [])),
        'synced_at': snapshot.get('synced_at'),
        'rooms': snapshot.get('rooms', [])
    }


@router.get('/diagnostics')
def diagnostics(token_payload=Depends(require_token), x_admin_pass: str | None = Header(None)):
    if not _check_admin(token_payload, x_admin_pass):
        raise HTTPException(status_code=403, detail="Admin required")
    data = read_config()
    integration = (data.get('advanced') or {}).get('integration') or {}
    status = get_status()
    # attempt quick HTTP ping to HA states endpoint to measure latency
    latency = None
    last_error = None
    if integration.get('enabled') and integration.get('host') and integration.get('token'):
        try:
            headers = { 'Authorization': f"Bearer {integration.get('token')}", 'Accept': 'application/json' }
            url = integration.get('host').rstrip('/') + '/api/states'
            t0 = time.time()
            r = requests.get(url, headers=headers, timeout=5)
            latency = round((time.time() - t0) * 1000)
            if r.status_code != 200:
                last_error = f"HTTP {r.status_code}"
        except Exception as e:
            last_error = str(e)

    return { 'integration': integration, 'ha_ws': status, 'ping_ms': latency, 'last_error': last_error }


@router.get('/events')
def get_events(token_payload=Depends(require_token), x_admin_pass: str | None = Header(None)):
    if not _check_admin(token_payload, x_admin_pass):
        raise HTTPException(status_code=403, detail="Admin required")
    # return recent events
    from ..ha_ws import recent_events
    # convert timestamps to readable format
    out = []
    for it in recent_events[-100:]:
        out.append({ 'ts': it.get('ts'), 'event': it.get('event') })
    return { 'events': out }


@router.get('/registry')
def get_registry(token_payload=Depends(require_token), x_admin_pass: str | None = Header(None)):
    if not _check_admin(token_payload, x_admin_pass):
        raise HTTPException(status_code=403, detail="Admin required")
    snap = get_registry_snapshot()
    return { 'registry': snap }


@router.post('/clear-events')
def post_clear_events(token_payload=Depends(require_token), x_admin_pass: str | None = Header(None)):
    if not _check_admin(token_payload, x_admin_pass):
        raise HTTPException(status_code=403, detail="Admin required")
    from ..ha_ws import clear_recent_events
    clear_recent_events()
    return { 'ok': True }
