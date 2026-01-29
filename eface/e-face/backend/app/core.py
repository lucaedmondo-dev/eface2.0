import os
import json
import asyncio
import re
import copy
import requests
from collections import defaultdict
from fastapi import Header, HTTPException
from datetime import datetime, timedelta
import jwt
import logging
from typing import List
import time
from urllib.parse import quote

from .registry_cache import get_registry_snapshot, set_registry_snapshot

API_TOKEN = os.environ.get("EFACE_API_TOKEN", "devtoken123")
JWT_SECRET = os.environ.get("EFACE_JWT_SECRET", "dev_jwt_secret_change_me")
JWT_ALGORITHM = "HS256"
# Default JWT expiry in minutes. Set to ~3 months (129600 minutes) by default.
JWT_EXPIRES_MINUTES = int(os.environ.get("EFACE_JWT_EXP_MIN", "129600"))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config_store.json")
REGISTRY_CACHE_TTL = max(0, int(os.environ.get("EFACE_REGISTRY_TTL", "0")))


def read_config():
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w") as f:
            json.dump({"site_name": "e-face demo", "advanced": {}, "devices": [], "users": [], "admin": {"username": "admin", "password_hash": ""}}, f)
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


def write_config(data):
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)


def create_access_token(subject: str, is_admin: bool = False, must_change: bool = False, expires_minutes: int | None = None):
    now = datetime.utcnow()
    if expires_minutes is None:
        # ensure a sane default even if environment variable was set to 0
        expires_minutes = JWT_EXPIRES_MINUTES if (isinstance(JWT_EXPIRES_MINUTES, int) and JWT_EXPIRES_MINUTES > 0) else 60
    exp = now + timedelta(minutes=expires_minutes)
    # PyJWT accepts datetimes for exp, but normalize to UTC timestamp for clarity
    payload = {"sub": subject, "is_admin": bool(is_admin), "must_change": bool(must_change), "exp": int(exp.timestamp())}
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token


def decode_access_token(token: str):
    logger = logging.getLogger('e-face.core')
    try:
        # allow small clock skew (leeway) to tolerate minor time differences
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM], leeway=30)
        logger.debug('Decoded JWT payload: %s', payload)
        return payload
    except jwt.ExpiredSignatureError as e:
        logger.info('JWT expired: %s', e)
        # log token expiry vs server time for debugging
        try:
            import time
            raw = jwt.decode(token, options={"verify_signature": False, "verify_exp": False})
            exp = int(raw.get('exp', 0))
            logger.info('Token exp claim: %s, server_time: %s', exp, int(time.time()))
        except Exception:
            logger.debug('Could not decode token for exp inspection')
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        logger.warning('Invalid JWT token: %s', e)
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    except Exception as e:
        logger.exception('Unexpected error decoding token: %s', e)
        raise HTTPException(status_code=401, detail="Invalid token")


def require_token(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    if authorization.startswith("Bearer "):
        token = authorization.split(" ", 1)[1]
    else:
        token = authorization

    # allow legacy API_TOKEN for compatibility
    if token == API_TOKEN:
        return {"sub": "service", "is_admin": False}

    payload = decode_access_token(token)
    return payload


def verify_admin_password(password: str) -> bool:
    # read stored hash from config and compare sha256
    import hashlib
    data = read_config()
    admin = data.get("admin", {})
    stored = admin.get("password_hash")
    if not stored:
        return False
    h = hashlib.sha256(password.encode('utf-8')).hexdigest()
    return h == stored


def hash_password(password: str) -> str:
    import hashlib
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def get_user(username: str):
    data = read_config()
    users = data.get('users', [])
    for u in users:
        if u.get('username') == username:
            return u
    return None


def create_user(username: str, password: str, must_change: bool = True, is_admin: bool = False):
    data = read_config()
    users = data.get('users', [])
    if any(u.get('username') == username for u in users):
        return False
    users.append({
        'username': username,
        'password_hash': hash_password(password),
        'must_change': bool(must_change),
        'is_admin': bool(is_admin)
    })
    data['users'] = users
    write_config(data)
    return True


def verify_user_password(username: str, password: str) -> bool:
    u = get_user(username)
    if not u:
        return False
    return hash_password(password) == u.get('password_hash')


def set_user_password(username: str, new_password: str, must_change: bool = False):
    data = read_config()
    users = data.get('users', [])
    for u in users:
        if u.get('username') == username:
            u['password_hash'] = hash_password(new_password)
            u['must_change'] = bool(must_change)
            data['users'] = users
            write_config(data)
            return True
    return False


def load_registry_snapshot(integration: dict, allow_ws_fallback: bool = True) -> dict:
    """Load Home Assistant area/device/entity registries.
    Prefers cached data, then REST endpoints, finally websocket fallback when necessary.
    """
    import requests
    cached = get_registry_snapshot()
    ttl = REGISTRY_CACHE_TTL
    if cached and ttl > 0:
        ts = cached.get('ts')
        if isinstance(ts, (int, float)) and (time.time() - ts) < ttl:
            return cached
    if not integration:
        raise Exception("integration not configured")
    host = integration.get('host')
    token = integration.get('token')
    if not host or not token:
        raise Exception("integration missing host or token")

    base = host.rstrip('/')
    headers = {
        'Authorization': f"Bearer {token}",
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }

    def _fetch(path: str, fallback_path: str | None = None):
        url = base + path
        try:
            resp = requests.post(url, headers=headers, json={}, timeout=8)
            if resp.status_code == 200:
                data = resp.json() or []
                if isinstance(data, list):
                    return data
        except Exception:
            pass
        if fallback_path:
            try:
                resp = requests.get(base + fallback_path, headers=headers, timeout=8)
                if resp.status_code == 200:
                    data = resp.json() or []
                    if isinstance(data, list):
                        return data
            except Exception:
                pass
        return []

    areas_raw = _fetch('/api/config/area_registry/list', '/api/areas')
    devices_raw = _fetch('/api/config/device_registry/list', '/api/devices')
    entities_raw = _fetch('/api/config/entity_registry/list', '/api/config/entity_registry/list')

    if areas_raw or devices_raw or entities_raw:
        snapshot = _compose_registry_snapshot(areas_raw, devices_raw, entities_raw)
        set_registry_snapshot(snapshot)
        return snapshot

    if allow_ws_fallback:
        snapshot = _fetch_registry_via_ws(host, token)
        if snapshot:
            set_registry_snapshot(snapshot)
            return snapshot

    if cached:
        return cached

    snapshot = _compose_registry_snapshot([], [], [])
    set_registry_snapshot(snapshot)
    return snapshot


def _compose_registry_snapshot(areas_raw, devices_raw, entities_raw):
    area_map = {}
    for area in areas_raw or []:
        area_id = area.get('area_id') or area.get('id') or area.get('slug')
        if not area_id:
            continue
        area_map[area_id] = area.get('name') or area_id

    device_map = {}
    for dev in devices_raw or []:
        dev_id = dev.get('id') or dev.get('device_id')
        if not dev_id:
            continue
        device_map[dev_id] = {
            'name': dev.get('name') or dev.get('name_by_user') or dev.get('original_name') or dev_id,
            'area_id': dev.get('area_id') or dev.get('area')
        }

    entity_map = {}
    for ent in entities_raw or []:
        ent_id = ent.get('entity_id')
        if not ent_id:
            continue
        entity_map[ent_id] = {
            'device_id': ent.get('device_id'),
            'area_id': ent.get('area_id') or ent.get('area'),
            'hidden_by': ent.get('hidden_by') or ent.get('entity_registry_hidden_by'),
            'entity_category': ent.get('entity_category'),
            'original_name': ent.get('original_name') or ent.get('name'),
            'labels': ent.get('labels') or []
        }

    table = []
    for ent_id, meta in entity_map.items():
        dev_id = meta.get('device_id')
        dev = device_map.get(dev_id) if dev_id else None
        resolved_area = meta.get('area_id') or (dev.get('area_id') if dev else None)
        table.append({
            'entity_id': ent_id,
            'device_id': dev_id,
            'device_name': (dev or {}).get('name'),
            'area_id': resolved_area,
            'area_name': area_map.get(resolved_area)
        })

    return {
        'areas': area_map,
        'devices': device_map,
        'entities': entity_map,
        'table': table
    }


def _fetch_registry_via_ws(host: str, token: str) -> dict | None:
    import json
    try:
        import websockets
    except Exception:
        return None

    if not host or not token:
        return None

    if host.startswith('https://'):
        ws_url = 'wss://' + host[len('https://'):]
    elif host.startswith('http://'):
        ws_url = 'ws://' + host[len('http://'):]
    else:
        ws_url = 'ws://' + host
    ws_url = ws_url.rstrip('/') + '/api/websocket'

    async def _collect():
        async with websockets.connect(ws_url, ping_interval=15, ping_timeout=10) as ws:
            try:
                await ws.recv()  # auth_required
            except Exception:
                pass
            await ws.send(json.dumps({'type': 'auth', 'access_token': token}))
            auth_resp = json.loads(await ws.recv())
            if auth_resp.get('type') != 'auth_ok':
                return None

            reg_map = {
                'areas': ('config/area_registry/list', 7001),
                'devices': ('config/device_registry/list', 7002),
                'entities': ('config/entity_registry/list', 7003)
            }
            for cmd, ident in [(v[0], v[1]) for v in reg_map.values()]:
                await ws.send(json.dumps({'id': ident, 'type': cmd}))

            pending = {v[1]: k for k, v in reg_map.items()}
            results = {k: [] for k in reg_map.keys()}

            while pending:
                msg = await asyncio.wait_for(ws.recv(), timeout=10)
                data = json.loads(msg)
                if data.get('type') == 'result' and data.get('id') in pending:
                    key = pending.pop(data['id'])
                    results[key] = data.get('result') or []

            return _compose_registry_snapshot(results['areas'], results['devices'], results['entities'])

    try:
        return asyncio.run(_collect())
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_collect())
        finally:
            loop.close()
    except Exception:
        return None


def _truthy(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {'1', 'true', 'yes', 'on'}
    return bool(value)


def _collect_labels(*sources) -> list[str]:
    labels: list[str] = []
    for source in sources:
        if not source:
            continue
        items = source if isinstance(source, (list, tuple, set)) else [source]
        for item in items:
            if not isinstance(item, str):
                continue
            val = item.strip()
            if not val:
                continue
            normalized = val.lower()
            if normalized not in labels:
                labels.append(normalized)
                alias = normalized.replace('_', '-').strip('-')
                if alias and alias not in labels:
                    labels.append(alias)
    return labels


def _has_tvcc_label(labels: list[str]) -> bool:
    for label in labels or []:
        if not label:
            continue
        normalized = label.strip().lower()
        if not normalized:
            continue
        slug = normalized.replace('_', '-').strip('-')
        if normalized == 'tvcc' or slug.startswith('tvcc:') or slug.startswith('tvcc-'):
            return True
    return False


def _should_hide_entity(attrs: dict, registry_entry: dict | None, labels: list[str]) -> bool:
    attrs = attrs or {}
    registry_entry = registry_entry or {}
    if _truthy(attrs.get('hidden')):
        return True
    visible = attrs.get('visible')
    if visible is not None and not _truthy(visible):
        return True
    attr_hidden_by = attrs.get('entity_registry_hidden_by') or attrs.get('hidden_by')
    if attr_hidden_by:
        return True
    attr_visible = attrs.get('entity_registry_visible')
    if attr_visible is not None and not _truthy(attr_visible):
        return True
    hidden_by = registry_entry.get('hidden_by')
    if hidden_by:
        return True
    if 'hidden' in labels:
        return True
    return False


def _resolve_room_for_entity(registry_entry: dict | None, attrs: dict | None, device_map: dict) -> str | None:
    attrs = attrs or {}
    registry_entry = registry_entry or {}
    area_id = registry_entry.get('area_id') or attrs.get('area_id')
    if area_id:
        return area_id
    device_id = registry_entry.get('device_id')
    if device_id and device_map.get(device_id):
        return device_map[device_id].get('area_id')
    return None


def _collect_camera_entities(state_map: dict, entity_registry: dict, device_map: dict) -> list[dict]:
    cameras: list[dict] = []
    if not isinstance(state_map, dict):
        return cameras
    for entity_id, state in state_map.items():
        if not isinstance(entity_id, str) or not entity_id.startswith('camera.'):
            continue
        attrs = (state or {}).get('attributes') or {}
        registry_entry = entity_registry.get(entity_id) or {}
        labels = _collect_labels(
            attrs.get('labels'),
            attrs.get('tags'),
            attrs.get('label'),
            registry_entry.get('labels'),
            attrs.get('eface_tags'),
            attrs.get('custom_tags')
        )
        if not _has_tvcc_label(labels):
            continue
        if _should_hide_entity(attrs, registry_entry, labels):
            continue
        room_id = _resolve_room_for_entity(registry_entry, attrs, device_map)
        cameras.append({
            'id': entity_id,
            'entity_id': entity_id,
            'name': attrs.get('friendly_name') or registry_entry.get('name') or entity_id,
            'state': state.get('state'),
            'labels': labels,
            'room_id': room_id,
            'attributes': {
                'entity_picture': attrs.get('entity_picture'),
                'frontend_stream_type': attrs.get('frontend_stream_type'),
                'stream_type': attrs.get('stream_type'),
                'supported_features': attrs.get('supported_features')
            }
        })
    return cameras


def _has_alarm_partition_label(labels: list[str]) -> bool:
    for label in labels or []:
        if ('alarm' in label or 'allarme' in label) and any(
            token in label for token in ('part', 'partition', 'partiz', 'area')
        ):
            return True
    return False


def _has_alarm_zone_label(labels: list[str]) -> bool:
    for label in labels or []:
        if ('alarm' in label or 'allarme' in label) and any(
            token in label for token in ('zone', 'zona', 'sensor', 'sensore')
        ):
            return True
    return False


def _has_alarm_status_label(labels: list[str]) -> bool:
    for label in labels or []:
        if not label:
            continue
        normalized = label.strip().lower()
        if not normalized:
            continue
        slug = normalized.replace('_', '-').replace('  ', ' ')
        if slug.startswith('alarm-status') or slug.startswith('alarm status') or slug.startswith('alarmstatus'):
            return True
    return False


def _normalize_tag_slug(value: str | None) -> str:
    if not value:
        return ''
    return re.sub(r'[^a-z0-9]+', '-', value.strip().lower()).strip('-')


def _has_tag_prefix(labels: list[str], prefix: str) -> bool:
    prefix = (prefix or '').strip().lower()
    if not prefix:
        return False
    for label in labels or []:
        slug = _normalize_tag_slug(label)
        if not slug:
            continue
        if slug == prefix or slug.startswith(prefix + '-'):
            return True
    return False


def _has_doorbell_label(labels: list[str]) -> bool:
    return _has_tag_prefix(labels, 'doorbell')


def _has_gate_label(labels: list[str]) -> bool:
    return _has_tag_prefix(labels, 'gate')


def _looks_like_alarm_partition(domain: str, labels: list[str]) -> bool:
    _ = domain  # unused but kept for signature compatibility
    return _has_alarm_partition_label(labels)


def _looks_like_alarm_zone(domain: str, attrs: dict, labels: list[str]) -> bool:
    _ = (domain, attrs)  # unused; detection is tag-based per requirements
    return _has_alarm_zone_label(labels)


def _looks_like_alarm_status(labels: list[str]) -> bool:
    return _has_alarm_status_label(labels)


def _collect_security_entities(state_map: dict, entity_registry: dict, device_map: dict, area_map: dict) -> list[dict]:
    entries: list[dict] = []
    if not isinstance(state_map, dict):
        return entries
    for entity_id, state in state_map.items():
        if not isinstance(entity_id, str):
            continue
        attrs = (state or {}).get('attributes') or {}
        registry_entry = entity_registry.get(entity_id) or {}
        labels = _collect_labels(
            attrs.get('labels'),
            attrs.get('tags'),
            attrs.get('label'),
            registry_entry.get('labels')
        )
        if _should_hide_entity(attrs, registry_entry, labels):
            continue
        domain = entity_id.split('.', 1)[0] if '.' in entity_id else ''
        category = None
        if _looks_like_alarm_partition(domain, labels):
            category = 'partition'
        elif _looks_like_alarm_zone(domain, attrs, labels):
            category = 'zone'
        elif _looks_like_alarm_status(labels):
            category = 'status'
        is_doorbell_related = _has_doorbell_label(labels) or _has_gate_label(labels)
        if not category and not is_doorbell_related:
            continue
        entry_category = category or 'doorbell'
        room_id = _resolve_room_for_entity(registry_entry, attrs, device_map)
        area_label = area_map.get(room_id) if room_id else None
        if not area_label:
            area_label = attrs.get('room_name') or attrs.get('room') or attrs.get('area')
        entries.append({
            'id': entity_id,
            'entity_id': entity_id,
            'type': domain,
            'domain': domain,
            'category': entry_category,
            'name': attrs.get('friendly_name') or registry_entry.get('original_name') or entity_id,
            'state': state.get('state'),
            'device_class': attrs.get('device_class'),
            'area_id': room_id,
            'area_name': area_label,
            'labels': labels,
            'tags': labels,
            'attributes': attrs,
            'last_changed': state.get('last_changed'),
            'last_updated': state.get('last_updated')
        })
    return entries


def _attach_cameras_to_rooms(room_list: list, camera_entries: list[dict]) -> list:
    if not isinstance(room_list, list):
        return []
    camera_entries = camera_entries or []
    cameras_by_room = defaultdict(list)
    global_cameras: list[dict] = []
    for camera in camera_entries:
        room_id = camera.get('room_id')
        if room_id:
            cameras_by_room[room_id].append(camera)
        else:
            global_cameras.append(camera)
    for room in room_list:
        room_id = room.get('id')
        combined: list[dict] = []
        specific = cameras_by_room.get(room_id) or []
        if specific:
            combined.extend(copy.deepcopy(specific))
        if global_cameras:
            combined.extend(copy.deepcopy(global_cameras))
        room['cameras'] = combined
    return room_list


def _normalize_room_hint(value: str | None) -> str | None:
    if not value:
        return None
    slug = re.sub(r'[^a-z0-9]+', '_', value.lower()).strip('_')
    return slug or value.strip().lower()


def _room_hint_from_labels(labels: list[str]) -> str | None:
    if not labels:
        return None
    prefixes = ('room:', 'room=', 'area:', 'area=')
    for label in labels:
        if not isinstance(label, str):
            continue
        trimmed = label.strip().lower()
        for prefix in prefixes:
            if trimmed.startswith(prefix):
                remainder = trimmed[len(prefix):].strip()
                hint = _normalize_room_hint(remainder)
                if hint:
                    return hint
    return None


def _append_light_scene(entity_id: str, domain: str, attrs: dict, registry_entry: dict, labels: list[str], device_map: dict, scenes_by_room: dict, fallback: list):
    if not entity_id or domain not in {'button', 'input_button', 'scene'}:
        return
    if 'light-scene' not in labels:
        return
    if _should_hide_entity(attrs, registry_entry, labels):
        return
    room_id = _resolve_room_for_entity(registry_entry, attrs, device_map)
    if not room_id:
        room_id = _room_hint_from_labels(labels)
    scene = {
        'id': entity_id,
        'name': attrs.get('friendly_name') or registry_entry.get('original_name') or entity_id,
        'icon': attrs.get('icon'),
        'domain': domain,
        'service': 'press' if domain in {'button', 'input_button'} else 'turn_on'
    }
    target = scenes_by_room.setdefault(room_id, []) if room_id else fallback
    target.append(scene)


def _gather_light_scenes(state_map: dict, entity_registry: dict, device_map: dict):
    scenes_by_room: dict[str | None, list] = {}
    fallback: list = []
    processed: set[str] = set()

    for entity_id, ent in state_map.items():
        if not entity_id:
            continue
        domain = entity_id.split('.', 1)[0]
        attrs = (ent or {}).get('attributes') or {}
        registry_entry = entity_registry.get(entity_id) or {}
        labels = _collect_labels(
            attrs.get('labels'),
            attrs.get('tags'),
            registry_entry.get('labels')
        )
        _append_light_scene(entity_id, domain, attrs, registry_entry, labels, device_map, scenes_by_room, fallback)
        processed.add(entity_id)

    for entity_id, registry_entry in (entity_registry or {}).items():
        if not entity_id or entity_id in processed:
            continue
        domain = entity_id.split('.', 1)[0]
        labels = _collect_labels(registry_entry.get('labels'))
        attrs = {}
        _append_light_scene(entity_id, domain, attrs, registry_entry or {}, labels, device_map, scenes_by_room, fallback)

    return scenes_by_room, fallback


def _has_valid_room_templates(room_templates: list | None) -> bool:
    if not room_templates:
        return False
    meaningful = [r for r in room_templates if isinstance(r, dict) and r.get('luci')]
    if not meaningful:
        return False
    # ignore legacy placeholder room "manual" which grouped everything together
    non_manual = [r for r in meaningful if (r.get('id') or '').lower() not in {'', 'manual', 'default'}]
    return bool(non_manual)


def _coerce_str_list(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple, set)):
        items: list[str] = []
        for item in value:
            if isinstance(item, str) and item:
                items.append(item)
        return items
    return []


def _shape_weather_payload(entity_id: str, state: dict | None) -> dict | None:
    if not entity_id or not state:
        return None
    attrs = (state.get('attributes') or {}) if isinstance(state, dict) else {}
    return {
        'entity_id': entity_id,
        'id': entity_id,
        'state': state.get('state'),
        'attributes': attrs,
        'last_changed': state.get('last_changed'),
        'last_updated': state.get('last_updated')
    }


def _extract_weather_snapshot(state_map: dict, preferred_ids: list[str] | None = None) -> dict | None:
    if not isinstance(state_map, dict):
        return None
    candidates = [c for c in (preferred_ids or []) if isinstance(c, str) and c]
    for entity_id in candidates:
        state = state_map.get(entity_id)
        shaped = _shape_weather_payload(entity_id, state)
        if shaped:
            return shaped
    for entity_id, state in state_map.items():
        if isinstance(entity_id, str) and entity_id.lower().startswith('weather.'):
            shaped = _shape_weather_payload(entity_id, state)
            if shaped:
                return shaped
    return None


def _fetch_weather_forecast(host: str, token: str, entity_id: str, forecast_type: str | None = None):
    if not host or not token or not entity_id:
        return None
    import requests
    base = host.rstrip('/')
    entity_segment = quote(entity_id, safe='')
    url = f"{base}/api/weather/forecast/{entity_segment}"
    params = {}
    if forecast_type:
        params['type'] = forecast_type
    headers = {'Authorization': f"Bearer {token}", 'Accept': 'application/json'}
    try:
        resp = requests.get(url, headers=headers, params=params or None, timeout=6)
        resp.raise_for_status()
        payload = resp.json()
        if isinstance(payload, dict):
            data = payload.get('forecast')
            if isinstance(data, list):
                return data
        if isinstance(payload, list):
            return payload
    except Exception as exc:
        logging.getLogger('e-face.core').debug('Weather forecast fetch failed (%s, %s): %s', entity_id, forecast_type, exc)
    return None


def _enrich_weather_forecast(snapshot: dict, host: str, token: str) -> dict:
    if not snapshot or not isinstance(snapshot, dict):
        return snapshot
    entity_id = snapshot.get('entity_id') or snapshot.get('id')
    attrs = snapshot.get('attributes') or {}
    hourly = _fetch_weather_forecast(host, token, entity_id, 'hourly')
    daily = _fetch_weather_forecast(host, token, entity_id, 'daily')
    if hourly:
        attrs['forecast_hourly'] = hourly
    if daily:
        attrs['forecast_daily'] = daily
    if not attrs.get('forecast') and hourly:
        attrs['forecast'] = hourly
    snapshot['attributes'] = attrs
    return snapshot


def _collect_cover_entities(state_map: dict, entity_registry: dict, device_map: dict) -> dict:
    """Collect cover entities (shutters, blinds) by room."""
    covers_by_room = defaultdict(list)
    if not isinstance(state_map, dict):
        return {}
    
    for entity_id, state in state_map.items():
        if not isinstance(entity_id, str) or not entity_id.startswith('cover.'):
            continue
        attrs = (state or {}).get('attributes') or {}
        registry_entry = entity_registry.get(entity_id) or {}
        labels = _collect_labels(
            attrs.get('labels'),
            attrs.get('tags'),
            registry_entry.get('labels')
        )
        if _should_hide_entity(attrs, registry_entry, labels):
            continue
        
        dev_id = registry_entry.get('device_id') or attrs.get('device_id')
        dev = device_map.get(dev_id) if dev_id else None
        area_id = registry_entry.get('area_id') or (dev or {}).get('area_id') or attrs.get('area_id')
        
        # Skip covers without area
        if not area_id:
            continue
        
        cover_data = {
            'id': entity_id,
            'entity_id': entity_id,
            'name': attrs.get('friendly_name') or registry_entry.get('original_name') or entity_id,
            'state': state.get('state'),
            'current_position': attrs.get('current_position'),
            'current_tilt_position': attrs.get('current_tilt_position'),
            'device_class': attrs.get('device_class'),
            'supported_features': attrs.get('supported_features'),
            'labels': labels,
            'attributes': {
                'current_position': attrs.get('current_position'),
                'current_tilt_position': attrs.get('current_tilt_position'),
                'device_class': attrs.get('device_class'),
                'supported_features': attrs.get('supported_features')
            }
        }
        covers_by_room[area_id].append(cover_data)
    
    return dict(covers_by_room)


def _collect_climate_entities(state_map: dict, entity_registry: dict, device_map: dict) -> dict:
    """Collect climate entities (thermostats, HVAC) by room.
    
    ONLY adds climate entities that are explicitly configured in room templates.
    Does NOT auto-discover climate entities based on area_id.
    """
    climate_by_room = defaultdict(list)
    if not isinstance(state_map, dict):
        return {}
    
    # Check if we have a climate map from config
    if not hasattr(_collect_climate_entities, '_room_climate_map'):
        # No climate configured in any room, return empty
        print("DEBUG Climate: No climate entities in configuration, skipping auto-discovery")
        return {}
    
    climate_map_from_config = _collect_climate_entities._room_climate_map
    
    for entity_id, state in state_map.items():
        if not isinstance(entity_id, str) or not entity_id.startswith('climate.'):
            continue
        
        # ONLY process climate entities that are explicitly in the configuration
        if entity_id not in climate_map_from_config:
            continue
        
        area_id = climate_map_from_config.get(entity_id)
        if not area_id:
            continue
        
        attrs = (state or {}).get('attributes') or {}
        registry_entry = entity_registry.get(entity_id) or {}
        labels = _collect_labels(
            attrs.get('labels'),
            attrs.get('tags'),
            registry_entry.get('labels')
        )
        if _should_hide_entity(attrs, registry_entry, labels):
            continue
        
        climate_data = {
            'id': entity_id,
            'entity_id': entity_id,
            'name': attrs.get('friendly_name') or registry_entry.get('original_name') or entity_id,
            'state': state.get('state'),
            'current_temperature': attrs.get('current_temperature'),
            'target_temperature': attrs.get('temperature'),
            'target_temp_high': attrs.get('target_temp_high'),
            'target_temp_low': attrs.get('target_temp_low'),
            'hvac_mode': attrs.get('hvac_mode') or state.get('state'),
            'hvac_modes': attrs.get('hvac_modes') or [],
            'preset_mode': attrs.get('preset_mode'),
            'preset_modes': attrs.get('preset_modes') or [],
            'fan_mode': attrs.get('fan_mode'),
            'fan_modes': attrs.get('fan_modes') or [],
            'humidity': attrs.get('current_humidity'),
            'labels': labels,
            'attributes': {
                'current_temperature': attrs.get('current_temperature'),
                'temperature': attrs.get('temperature'),
                'target_temp_high': attrs.get('target_temp_high'),
                'target_temp_low': attrs.get('target_temp_low'),
                'hvac_modes': attrs.get('hvac_modes') or [],
                'preset_modes': attrs.get('preset_modes') or [],
                'fan_modes': attrs.get('fan_modes') or [],
                'min_temp': attrs.get('min_temp'),
                'max_temp': attrs.get('max_temp'),
                'target_temp_step': attrs.get('target_temp_step'),
                'supported_features': attrs.get('supported_features')
            }
        }
        climate_by_room[area_id].append(climate_data)
        print(f"DEBUG Climate {entity_id}: ADDED to room {area_id}")
    
    print(f"DEBUG Climate: Total collected: {dict((k, len(v)) for k, v in climate_by_room.items())}")
    return dict(climate_by_room)

def _collect_room_temperature_sensors(state_map: dict, entity_registry: dict, device_map: dict) -> dict:
    """Collect temperature sensors with 'room-temp' tag by room."""
    temp_sensors_by_room = defaultdict(list)
    if not isinstance(state_map, dict):
        return {}
    
    for entity_id, state in state_map.items():
        if not isinstance(entity_id, str) or not entity_id.startswith('sensor.'):
            continue
        
        attrs = (state or {}).get('attributes') or {}
        registry_entry = entity_registry.get(entity_id) or {}
        
        # Collect labels from all sources
        labels = _collect_labels(
            attrs.get('labels'),
            attrs.get('tags'),
            registry_entry.get('labels')
        )
        
        # Check if has room-temp tag
        if 'room-temp' not in labels:
            continue
        
        # Check if it's a temperature sensor (numeric value)
        device_class = attrs.get('device_class')
        unit = attrs.get('unit_of_measurement', '')
        state_val = state.get('state')
        
        # Must be numeric and ideally temperature-related
        try:
            temp_value = float(state_val) if state_val not in ('unknown', 'unavailable', None) else None
        except (ValueError, TypeError):
            continue
        
        # Get area from entity registry
        area_id = registry_entry.get('area_id')
        if not area_id:
            # Try to get from device
            device_id = registry_entry.get('device_id')
            if device_id:
                device = device_map.get(device_id) or {}
                area_id = device.get('area_id')
        
        if not area_id:
            continue
        
        # Skip hidden entities
        if _should_hide_entity(attrs, registry_entry, labels):
            continue
        
        sensor_data = {
            'id': entity_id,
            'entity_id': entity_id,
            'name': attrs.get('friendly_name') or registry_entry.get('original_name') or entity_id,
            'state': state_val,
            'value': temp_value,
            'unit': unit,
            'device_class': device_class,
            'labels': labels
        }
        
        temp_sensors_by_room[area_id].append(sensor_data)
        print(f"DEBUG RoomTemp {entity_id}: ADDED to room {area_id} (value: {temp_value}{unit})")
    
    print(f"DEBUG RoomTemp: Total collected: {dict((k, len(v)) for k, v in temp_sensors_by_room.items())}")
    return dict(temp_sensors_by_room)

def fetch_ha_rooms(integration: dict, include_meta: bool = False):
    if not isinstance(integration, dict):
        raise Exception("integration not configured")
    host = integration.get('host')
    token = integration.get('token')
    if not host or not token:
        raise Exception("integration missing host or token")

    cfg = read_config()
    synced = cfg.get('synced') or {}
    tracked_entities: List[str] = [e for e in (synced.get('tracked_entities') or []) if isinstance(e, str)]
    room_templates = cfg.get('rooms') or []
    background_map = {}
    for template in room_templates:
        if not isinstance(template, dict):
            continue
        room_id = template.get('id')
        if room_id:
            background_map[room_id] = template.get('background', '')

    headers = {'Authorization': f"Bearer {token}", 'Accept': 'application/json'}
    states_url = host.rstrip('/') + '/api/states'

    # fetch all states (will be filtered down using tracked_entities)
    try:
        sresp = requests.get(states_url, headers=headers, timeout=10)
        sresp.raise_for_status()
        states = sresp.json()
    except Exception as e:
        raise Exception(f"failed to fetch states: {e}")

    state_map = {it.get('entity_id'): it for it in states if it.get('entity_id')}

    try:
        registry = load_registry_snapshot(integration)
    except Exception:
        registry = {'areas': {}, 'devices': {}, 'entities': {}}
    
    entity_registry = registry.get('entities') or {}
    device_map = registry.get('devices') or {}
    area_map = registry.get('areas') or {}
    
    # If registry is empty (WebSocket failed), try to fetch via REST API
    if not entity_registry:
        try:
            headers = {'Authorization': f'Bearer {token}'}
            reg_resp = requests.get(f'{host}/api/config/entity_registry/list', headers=headers, timeout=10)
            if reg_resp.status_code == 200:
                entities_list = reg_resp.json()
                for ent in entities_list:
                    entity_id = ent.get('entity_id')
                    if entity_id:
                        entity_registry[entity_id] = {
                            'entity_id': entity_id,
                            'area_id': ent.get('area_id'),
                            'device_id': ent.get('device_id'),
                            'original_name': ent.get('original_name'),
                            'labels': ent.get('labels') or []
                        }
        except Exception:
            pass
    
    scenes_by_room, fallback_scenes = _gather_light_scenes(state_map, entity_registry, device_map)

    # Build climate mapping from room templates for fallback when registry is empty
    climate_map_from_config = {}
    for template in room_templates:
        if not isinstance(template, dict):
            continue
        room_id = template.get('id')
        climate_list = template.get('climate') or []
        for climate_entry in climate_list:
            if isinstance(climate_entry, dict):
                entity_id = climate_entry.get('entity_id')
                if entity_id:
                    climate_map_from_config[entity_id] = room_id
    print(f"DEBUG: Climate map from config: {climate_map_from_config}")
    _collect_climate_entities._room_climate_map = climate_map_from_config

    preferred_weather = []
    adv = cfg.get('advanced') or {}
    integration_pref = integration.get('weather_entity') or (adv.get('weather_entity') if isinstance(adv, dict) else None)
    preferred_weather.extend(_coerce_str_list(integration_pref))
    synced_pref = synced.get('weather_entity') if isinstance(synced, dict) else None
    preferred_weather.extend([p for p in _coerce_str_list(synced_pref) if p not in preferred_weather])
    extra_weather = [ent for ent in (synced.get('extra_entities') or []) if isinstance(ent, str) and ent.startswith('weather.')] if isinstance(synced, dict) else []
    for ent in extra_weather:
        if ent not in preferred_weather:
            preferred_weather.append(ent)
    weather_snapshot = _extract_weather_snapshot(state_map, preferred_weather)
    if weather_snapshot:
        weather_snapshot = _enrich_weather_forecast(weather_snapshot, host, token)
    camera_entries = _collect_camera_entities(state_map, entity_registry, device_map)
    security_devices = _collect_security_entities(state_map, entity_registry, device_map, area_map)
    
    # Collect comfort devices (covers and climate)
    covers_by_room = _collect_cover_entities(state_map, entity_registry, device_map)
    climate_by_room = _collect_climate_entities(state_map, entity_registry, device_map)
    room_temp_sensors = _collect_room_temperature_sensors(state_map, entity_registry, device_map)

    # if no synced template is available yet, fall back to legacy discovery logic
    if not tracked_entities or not _has_valid_room_templates(room_templates):
        rooms_only = _legacy_room_fetch(state_map, integration, background_map)
        rooms_only = _attach_cameras_to_rooms(rooms_only, camera_entries)
        if include_meta:
            return rooms_only, ({'weather': weather_snapshot} if weather_snapshot else {})
        return rooms_only

    # Build the full room list with devices
    rooms = []
    for template in room_templates:
        if not isinstance(template, dict):
            continue
        room_id = template.get('id')
        # Skip manual room - lights without assigned area
        if room_id.lower() == 'manual':
            continue
        devices = []
        for light in template.get('luci') or []:
            entity_id = light.get('entity_id')
            if not entity_id or entity_id not in tracked_entities:
                continue
            st = state_map.get(entity_id)
            attrs = (st or {}).get('attributes') or {}
            registry_entry = entity_registry.get(entity_id) or {}
            labels = _collect_labels(light.get('labels'), attrs.get('labels'), attrs.get('tags'), registry_entry.get('labels'))
            if _should_hide_entity(attrs, registry_entry, labels):
                continue
            device_entry = {
                'id': entity_id,
                'type': 'light',
                'name': light.get('name') or attrs.get('friendly_name') or entity_id,
                'state': (st or {}).get('state', light.get('state')),
                'brightness': attrs.get('brightness', light.get('brightness', 0))
            }
            # preserve HA capability metadata so the frontend can expose the right controls
            capability_attrs = {
                'brightness': attrs.get('brightness', light.get('brightness')),
                'rgb_color': attrs.get('rgb_color'),
                'hs_color': attrs.get('hs_color'),
                'xy_color': attrs.get('xy_color'),
                'color_temp': attrs.get('color_temp'),
                'color_mode': attrs.get('color_mode') or light.get('color_mode'),
                'supported_color_modes': attrs.get('supported_color_modes') or light.get('supported_color_modes'),
                'supported_features': attrs.get('supported_features') or light.get('supported_features'),
                'min_mireds': attrs.get('min_mireds') or light.get('min_mireds'),
                'max_mireds': attrs.get('max_mireds') or light.get('max_mireds')
            }
            device_entry.update({
                'rgb_color': capability_attrs['rgb_color'],
                'color_temp': capability_attrs['color_temp'],
                'color_mode': capability_attrs['color_mode'],
                'attributes': capability_attrs,
                'labels': labels
            })
            devices.append(device_entry)

        room_scenes = list(scenes_by_room.get(room_id) or [])
        if fallback_scenes:
            room_scenes.extend(fallback_scenes)

        # Add covers and climate for this room
        room_covers = covers_by_room.get(room_id) or []
        room_climate = climate_by_room.get(room_id) or []
        room_temperatures = room_temp_sensors.get(room_id) or []

        rooms.append({
            'id': room_id,
            'name': template.get('name') or room_id,
            'background': template.get('background', ''),
            'devices': devices,
            'scenes': room_scenes,
            'covers': room_covers,
            'climate': room_climate,
            'temperatures': room_temperatures
        })

    rooms = _attach_cameras_to_rooms(rooms, camera_entries)

    if include_meta:
        return rooms, ({'weather': weather_snapshot} if weather_snapshot else {})

    return rooms


def _legacy_room_fetch(state_map: dict, integration: dict, backgrounds: dict | None = None) -> list:
    """Fallback to previous discovery behaviour when no synced config exists."""
    try:
        registry = load_registry_snapshot(integration)
    except Exception:
        registry = {'areas': {}, 'devices': {}, 'entities': {}, 'table': []}

    area_map = registry.get('areas') or {}
    device_map = registry.get('devices') or {}
    entity_registry = registry.get('entities') or {}

    rooms = {}
    backgrounds = backgrounds or {}
    for entity_id, ent in state_map.items():
        if not entity_id:
            continue
        domain = entity_id.split('.', 1)[0] if '.' in entity_id else None
        if domain != 'light':
            continue
        attrs = ent.get('attributes', {}) or {}
        entity_meta = entity_registry.get(entity_id) or {}
        labels = _collect_labels(attrs.get('labels'), entity_meta.get('labels'))
        if _should_hide_entity(attrs, entity_meta, labels):
            continue
        dev_id = entity_meta.get('device_id') or attrs.get('device_id') or ent.get('context', {}).get('device_id')
        area_id = entity_meta.get('area_id') or attrs.get('area_id') or attrs.get('room')
        if not area_id and dev_id:
            area_id = (device_map.get(dev_id) or {}).get('area_id')

        room_key = area_id or 'ungrouped'
        room_name = area_map.get(area_id) if area_id else 'Ungrouped'
        device_name = attrs.get('friendly_name') or (device_map.get(dev_id) or {}).get('name') or entity_id
        device_attrs = {
            'brightness': attrs.get('brightness', 0),
            'rgb_color': attrs.get('rgb_color'),
            'hs_color': attrs.get('hs_color'),
            'color_temp': attrs.get('color_temp'),
            'color_mode': attrs.get('color_mode'),
            'supported_color_modes': attrs.get('supported_color_modes'),
        }

        device = {
            'id': entity_id,
            'type': 'light',
            'name': device_name,
            'state': ent.get('state'),
            'brightness': attrs.get('brightness', 0),
            'rgb_color': attrs.get('rgb_color'),
            'color_temp': attrs.get('color_temp'),
            'color_mode': attrs.get('color_mode'),
            'attributes': device_attrs,
            'labels': labels
        }
        if room_key not in rooms:
            rooms[room_key] = {
                'id': room_key,
                'name': room_name or 'Default',
                'background': backgrounds.get(room_key, ''),
                'devices': []
            }
        # allow stored background overrides even if room was already created
        if room_key in backgrounds:
            rooms[room_key]['background'] = backgrounds.get(room_key, '')
        rooms[room_key]['devices'].append(device)

    room_list = list(rooms.values())
    scenes_by_room, fallback_scenes = _gather_light_scenes(state_map, entity_registry, device_map)
    for room in room_list:
        room_id = room.get('id')
        scene_list = list(scenes_by_room.get(room_id) or [])
        if fallback_scenes:
            scene_list.extend(fallback_scenes)
        room['scenes'] = scene_list
    return room_list


def refresh_room_snapshot(integration: dict, existing_rooms: list | None = None) -> dict:
    """Build a synced snapshot of HA rooms and tracked entities."""
    import requests
    if not integration:
        raise Exception("integration not configured")
    host = integration.get('host')
    token = integration.get('token')
    if not host or not token:
        raise Exception("integration missing host or token")

    headers = {'Authorization': f"Bearer {token}", 'Accept': 'application/json'}
    states_url = host.rstrip('/') + '/api/states'

    try:
        registry = load_registry_snapshot(integration)
    except Exception:
        registry = {'areas': {}, 'devices': {}, 'entities': {}}

    try:
        sresp = requests.get(states_url, headers=headers, timeout=10)
        sresp.raise_for_status()
        states = sresp.json() or []
    except Exception as e:
        raise Exception(f"failed to fetch states: {e}")

    extra_entities = _normalize_entity_list((integration or {}).get('extra_entities'))
    area_map = registry.get('areas') or {}
    entity_registry = registry.get('entities') or {}
    device_map = registry.get('devices') or {}
    registry_table = registry.get('table') or []
    table_lookup = {}
    for row in registry_table:
        ent_id = row.get('entity_id')
        if ent_id and ent_id not in table_lookup:
            table_lookup[ent_id] = row
    existing_rooms = existing_rooms or []
    existing_backgrounds = {r.get('id'): r.get('background', '') for r in existing_rooms}
    existing_names = {r.get('id'): r.get('name') for r in existing_rooms if r.get('id')}
    entity_room_map = {}
    for room in existing_rooms:
        room_id = room.get('id')
        if not room_id:
            continue
        for light in room.get('luci') or []:
            entity_id = light.get('entity_id')
            if entity_id:
                entity_room_map[entity_id] = room_id

    rooms_map = {}
    tracked = []
    
    # Process lights
    for ent in states:
        entity_id = ent.get('entity_id')
        if not entity_id:
            continue
        domain = entity_id.split('.', 1)[0] if '.' in entity_id else None
        if domain != 'light':
            continue
        attrs = ent.get('attributes', {}) or {}
        meta = entity_registry.get(entity_id) or {}
        labels = _collect_labels(attrs.get('labels'), meta.get('labels'))
        if _should_hide_entity(attrs, meta, labels):
            continue
        dev_id = meta.get('device_id') or attrs.get('device_id')
        dev = device_map.get(dev_id) if dev_id else None
        table_entry = table_lookup.get(entity_id) or {}
        area_id = (
            meta.get('area_id')
            or (dev or {}).get('area_id')
            or attrs.get('area_id')
            or table_entry.get('area_id')
        )
        if not area_id:
            area_id = entity_room_map.get(entity_id)
        # Skip lights without an assigned area
        if not area_id:
            continue
        room_key = area_id
        area_label = area_map.get(area_id)
        if not area_label and table_entry.get('area_name'):
            area_label = table_entry.get('area_name')
        room_name = existing_names.get(room_key) or area_label
        if not room_name:
            room_name = room_key

        if room_key not in rooms_map:
            rooms_map[room_key] = {
                'id': room_key,
                'name': room_name or room_key,
                'background': existing_backgrounds.get(room_key, ''),
                'luci': [],
                'media': [],
                'covers': [],
                'climate': []
            }

        rooms_map[room_key]['luci'].append({
            'entity_id': entity_id,
            'name': attrs.get('friendly_name') or (dev or {}).get('name') or entity_id,
            'state': ent.get('state'),
            'brightness': attrs.get('brightness'),
            'rgb_color': attrs.get('rgb_color'),
            'hs_color': attrs.get('hs_color'),
            'color_temp': attrs.get('color_temp'),
            'color_mode': attrs.get('color_mode'),
            'supported_color_modes': attrs.get('supported_color_modes'),
            'device_id': dev_id,
            'area_id': area_id,
            'updated_at': ent.get('last_changed') or ent.get('last_updated'),
            'labels': labels
        })
        tracked.append(entity_id)

    # Process covers (shutters, blinds)
    for ent in states:
        entity_id = ent.get('entity_id')
        if not entity_id or not entity_id.startswith('cover.'):
            continue
        attrs = ent.get('attributes', {}) or {}
        meta = entity_registry.get(entity_id) or {}
        labels = _collect_labels(attrs.get('labels'), meta.get('labels'))
        if _should_hide_entity(attrs, meta, labels):
            continue
        dev_id = meta.get('device_id') or attrs.get('device_id')
        dev = device_map.get(dev_id) if dev_id else None
        table_entry = table_lookup.get(entity_id) or {}
        area_id = (
            meta.get('area_id')
            or (dev or {}).get('area_id')
            or attrs.get('area_id')
            or table_entry.get('area_id')
        )
        if not area_id:
            continue
        room_key = area_id
        if room_key not in rooms_map:
            area_label = area_map.get(area_id)
            if not area_label and table_entry.get('area_name'):
                area_label = table_entry.get('area_name')
            room_name = existing_names.get(room_key) or area_label or room_key
            rooms_map[room_key] = {
                'id': room_key,
                'name': room_name,
                'background': existing_backgrounds.get(room_key, ''),
                'luci': [],
                'media': [],
                'covers': [],
                'climate': []
            }
        rooms_map[room_key]['covers'].append({
            'entity_id': entity_id,
            'name': attrs.get('friendly_name') or (dev or {}).get('name') or entity_id,
            'state': ent.get('state'),
            'current_position': attrs.get('current_position'),
            'current_tilt_position': attrs.get('current_tilt_position'),
            'device_class': attrs.get('device_class'),
            'supported_features': attrs.get('supported_features'),
            'device_id': dev_id,
            'area_id': area_id,
            'updated_at': ent.get('last_changed') or ent.get('last_updated'),
            'labels': labels
        })
        tracked.append(entity_id)

    # Process climate (thermostats, HVAC)
    for ent in states:
        entity_id = ent.get('entity_id')
        if not entity_id or not entity_id.startswith('climate.'):
            continue
        attrs = ent.get('attributes', {}) or {}
        meta = entity_registry.get(entity_id) or {}
        labels = _collect_labels(attrs.get('labels'), meta.get('labels'))
        if _should_hide_entity(attrs, meta, labels):
            continue
        dev_id = meta.get('device_id') or attrs.get('device_id')
        dev = device_map.get(dev_id) if dev_id else None
        table_entry = table_lookup.get(entity_id) or {}
        area_id = (
            meta.get('area_id')
            or (dev or {}).get('area_id')
            or attrs.get('area_id')
            or table_entry.get('area_id')
        )
        if not area_id:
            continue
        room_key = area_id
        if room_key not in rooms_map:
            area_label = area_map.get(area_id)
            if not area_label and table_entry.get('area_name'):
                area_label = table_entry.get('area_name')
            room_name = existing_names.get(room_key) or area_label or room_key
            rooms_map[room_key] = {
                'id': room_key,
                'name': room_name,
                'background': existing_backgrounds.get(room_key, ''),
                'luci': [],
                'media': [],
                'covers': [],
                'climate': []
            }
        rooms_map[room_key]['climate'].append({
            'entity_id': entity_id,
            'name': attrs.get('friendly_name') or (dev or {}).get('name') or entity_id,
            'state': ent.get('state'),
            'current_temperature': attrs.get('current_temperature'),
            'target_temperature': attrs.get('temperature'),
            'target_temp_high': attrs.get('target_temp_high'),
            'target_temp_low': attrs.get('target_temp_low'),
            'hvac_mode': attrs.get('hvac_mode') or ent.get('state'),
            'hvac_modes': attrs.get('hvac_modes') or [],
            'preset_mode': attrs.get('preset_mode'),
            'preset_modes': attrs.get('preset_modes') or [],
            'fan_mode': attrs.get('fan_mode'),
            'fan_modes': attrs.get('fan_modes') or [],
            'min_temp': attrs.get('min_temp'),
            'max_temp': attrs.get('max_temp'),
            'target_temp_step': attrs.get('target_temp_step'),
            'supported_features': attrs.get('supported_features'),
            'device_id': dev_id,
            'area_id': area_id,
            'updated_at': ent.get('last_changed') or ent.get('last_updated'),
            'labels': labels
        })
        tracked.append(entity_id)

    synced_at = datetime.utcnow().isoformat()
    return {
        'rooms': list(rooms_map.values()),
        'tracked_entities': sorted(set(tracked)),
        'synced_at': synced_at,
        'extra_entities': extra_entities
    }


def _normalize_entity_list(raw) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, str):
        tokens = raw.replace('\n', ',').split(',')
    elif isinstance(raw, list):
        tokens = raw
    else:
        tokens = []
    cleaned = []
    for item in tokens:
        if not isinstance(item, str):
            continue
        val = item.strip()
        if val:
            cleaned.append(val)
    return sorted(set(cleaned))
