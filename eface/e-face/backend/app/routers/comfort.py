from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import requests

from ..core import read_config, require_token

router = APIRouter()


# Models for cover control
class CoverPositionPayload(BaseModel):
    position: int


class CoverTiltPayload(BaseModel):
    tilt_position: int


# Models for climate control
class ClimateTemperaturePayload(BaseModel):
    temperature: float


class ClimateHvacModePayload(BaseModel):
    hvac_mode: str


class ClimatePresetPayload(BaseModel):
    preset_mode: str


class ClimateFanModePayload(BaseModel):
    fan_mode: str


def _require_integration():
    data = read_config()
    adv = data.get('advanced', {}) or {}
    integration = adv.get('integration')
    if not integration or not integration.get('enabled'):
        raise HTTPException(status_code=503, detail='integration_missing')
    host = integration.get('host')
    token = integration.get('token')
    if not host or not token:
        raise HTTPException(status_code=503, detail='integration_missing')
    return integration


def _call_ha_service(domain: str, service: str, data: dict):
    integration = _require_integration()
    host = integration.get('host')
    token = integration.get('token')
    url = host.rstrip('/') + f"/api/services/{domain}/{service}"
    headers = {
        'Authorization': f"Bearer {token}",
        'Content-Type': 'application/json'
    }
    try:
        resp = requests.post(url, headers=headers, json=data, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 400:
            raise HTTPException(status_code=400, detail='invalid_request')
        raise HTTPException(status_code=502, detail=f'ha_service_failed: {e}')
    except Exception as e:
        raise HTTPException(status_code=502, detail=f'ha_request_failed: {e}')


# COVER ENDPOINTS

@router.post("/covers/{entity_id}/open")
def open_cover(entity_id: str, token_payload=Depends(require_token)):
    """Open a cover (e.g., shutter, blind)"""
    return _call_ha_service('cover', 'open_cover', {'entity_id': entity_id})


@router.post("/covers/{entity_id}/close")
def close_cover(entity_id: str, token_payload=Depends(require_token)):
    """Close a cover"""
    return _call_ha_service('cover', 'close_cover', {'entity_id': entity_id})


@router.post("/covers/{entity_id}/stop")
def stop_cover(entity_id: str, token_payload=Depends(require_token)):
    """Stop a cover"""
    return _call_ha_service('cover', 'stop_cover', {'entity_id': entity_id})


@router.post("/covers/{entity_id}/toggle")
def toggle_cover(entity_id: str, token_payload=Depends(require_token)):
    """Toggle a cover"""
    return _call_ha_service('cover', 'toggle', {'entity_id': entity_id})


@router.post("/covers/{entity_id}/position")
def set_cover_position(entity_id: str, payload: CoverPositionPayload, token_payload=Depends(require_token)):
    """Set cover position (0-100)"""
    position = max(0, min(100, payload.position))
    return _call_ha_service('cover', 'set_cover_position', {
        'entity_id': entity_id,
        'position': position
    })


@router.post("/covers/{entity_id}/tilt")
def set_cover_tilt(entity_id: str, payload: CoverTiltPayload, token_payload=Depends(require_token)):
    """Set cover tilt position (0-100)"""
    tilt = max(0, min(100, payload.tilt_position))
    return _call_ha_service('cover', 'set_cover_tilt_position', {
        'entity_id': entity_id,
        'tilt_position': tilt
    })


# CLIMATE ENDPOINTS

@router.post("/climate/{entity_id}/turn_on")
def turn_on_climate(entity_id: str, token_payload=Depends(require_token)):
    """Turn on climate device"""
    return _call_ha_service('climate', 'turn_on', {'entity_id': entity_id})


@router.post("/climate/{entity_id}/turn_off")
def turn_off_climate(entity_id: str, token_payload=Depends(require_token)):
    """Turn off climate device"""
    return _call_ha_service('climate', 'turn_off', {'entity_id': entity_id})


@router.post("/climate/{entity_id}/temperature")
def set_temperature(entity_id: str, payload: ClimateTemperaturePayload, token_payload=Depends(require_token)):
    """Set target temperature"""
    return _call_ha_service('climate', 'set_temperature', {
        'entity_id': entity_id,
        'temperature': payload.temperature
    })


@router.post("/climate/{entity_id}/hvac_mode")
def set_hvac_mode(entity_id: str, payload: ClimateHvacModePayload, token_payload=Depends(require_token)):
    """Set HVAC mode (heat, cool, auto, off, etc.)"""
    return _call_ha_service('climate', 'set_hvac_mode', {
        'entity_id': entity_id,
        'hvac_mode': payload.hvac_mode
    })


@router.post("/climate/{entity_id}/preset_mode")
def set_preset_mode(entity_id: str, payload: ClimatePresetPayload, token_payload=Depends(require_token)):
    """Set preset mode (eco, comfort, away, etc.)"""
    return _call_ha_service('climate', 'set_preset_mode', {
        'entity_id': entity_id,
        'preset_mode': payload.preset_mode
    })


@router.post("/climate/{entity_id}/fan_mode")
def set_fan_mode(entity_id: str, payload: ClimateFanModePayload, token_payload=Depends(require_token)):
    """Set fan mode"""
    return _call_ha_service('climate', 'set_fan_mode', {
        'entity_id': entity_id,
        'fan_mode': payload.fan_mode
    })
