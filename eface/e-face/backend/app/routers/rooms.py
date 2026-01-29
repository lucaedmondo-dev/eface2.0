from fastapi import APIRouter, Depends, HTTPException
from ..core import read_config, require_token, fetch_ha_rooms

router = APIRouter()


@router.get("")
def list_rooms(token_payload=Depends(require_token)):
    data = read_config()
    adv = data.get('advanced', {}) or {}
    integration = adv.get('integration')
    # require HA integration: if present and enabled, try to fetch; otherwise return 503 so frontend shows message
    if not integration or not integration.get('enabled'):
        raise HTTPException(status_code=503, detail="integration_missing")
    try:
        rooms, meta = fetch_ha_rooms(integration, include_meta=True)
        response = {"rooms": rooms, "source": "ha"}
        if isinstance(meta, dict):
            response.update(meta)
        return response
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"integration_failed:{str(e)}")


@router.get("/{room_id}")
def get_room(room_id: str, token_payload=Depends(require_token)):
    data = read_config()
    adv = data.get('advanced', {}) or {}
    integration = adv.get('integration')
    if not integration or not integration.get('enabled'):
        raise HTTPException(status_code=503, detail="integration_missing")
    try:
        rooms = fetch_ha_rooms(integration)
        for r in rooms:
            if r.get('id') == room_id:
                return r
        raise HTTPException(status_code=404, detail='Room not found')
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"integration_failed:{str(e)}")
