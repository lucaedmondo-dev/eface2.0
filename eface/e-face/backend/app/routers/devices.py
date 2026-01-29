import asyncio
import json
import secrets
import threading
import re
import time
import posixpath
import logging

from fastapi import APIRouter, Depends, HTTPException, Header, Query, Request
from pydantic import BaseModel
from typing import List, Optional
from urllib.parse import quote, urlparse, urlunparse, urljoin, parse_qsl

import httpx
import requests
from requests.exceptions import ChunkedEncodingError
from fastapi.responses import Response, StreamingResponse
import websockets

from ..core import read_config, require_token, fetch_ha_rooms

router = APIRouter()
logger = logging.getLogger(__name__)

STREAM_SESSION_TTL = 90
_stream_sessions: dict[str, dict[str, str | float]] = {}
_stream_sessions_lock = threading.Lock()
STREAM_SESSION_TIMEOUTS = {
    'auto': 6.0,
    'doorbell': 9.0,
    'manual': 12.0
}

# How many times to retry fetching HLS stream segments (init/ts) before failing
CAMERA_HLS_PROXY_MAX_RETRIES = 5
# Base backoff in seconds (exponential backoff multiplier)
# Bumped to reduce aggressive retrying when upstream is temporarily failing
CAMERA_HLS_PROXY_BACKOFF_BASE = 1.0


def _resolve_stream_session_timeout(mode: str | None) -> float:
    if not mode:
        return STREAM_SESSION_TIMEOUTS['auto']
    normalized = mode.strip().lower()
    return STREAM_SESSION_TIMEOUTS.get(normalized, STREAM_SESSION_TIMEOUTS['auto'])


def _require_token_flexible(authorization: str = Header(None), token: str | None = Query(None)):
    if (not authorization or authorization.lower() == 'null') and token:
        authorization = f"Bearer {token}"
    return require_token(authorization)


@router.get("")
def list_devices(token_payload=Depends(require_token)):
    data = read_config()
    adv = data.get('advanced', {}) or {}
    integration = adv.get('integration')
    if not integration or not integration.get('enabled'):
        raise HTTPException(status_code=503, detail='integration_missing')
    try:
        rooms = fetch_ha_rooms(integration)
        devices = []
        for r in rooms:
            for d in r.get('devices', []):
                devices.append(d)
        return {"devices": devices}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"integration_failed:{e}")


@router.get("/{device_id}")
def get_device(device_id: str, token_payload=Depends(require_token)):
    data = read_config()
    adv = data.get('advanced', {}) or {}
    integration = adv.get('integration')
    if not integration or not integration.get('enabled'):
        raise HTTPException(status_code=503, detail='integration_missing')
    try:
        rooms = fetch_ha_rooms(integration)
        for r in rooms:
            for d in r.get('devices', []):
                if d.get('id') == device_id:
                    return d
        raise HTTPException(status_code=404, detail='Not found')
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"integration_failed:{e}")


class BrightnessPayload(BaseModel):
    brightness: int


class TurnOnPayload(BaseModel):
    brightness: Optional[int] = None


class ColorPayload(BaseModel):
    rgb_color: Optional[List[int]] = None
    brightness: Optional[int] = None


class TriggerPayload(BaseModel):
    service: str
    domain: Optional[str] = None
    data: Optional[dict] = None


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


def _normalize_base_url(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if '://' not in normalized:
        normalized = f"http://{normalized}"
    return normalized.rstrip('/')


def _integration_stream_targets(integration: dict) -> list[dict[str, str]]:
    prefer_remote = bool(integration.get('prefer_remote_streams'))
    local_host = _normalize_base_url(integration.get('host'))
    remote_host = _normalize_base_url(integration.get('remote_host'))
    local_token = integration.get('token')
    remote_token = integration.get('remote_token') or local_token
    if not local_token:
        raise HTTPException(status_code=503, detail='integration_missing')
    ws_path = integration.get('ws_path') or '/api/websocket'
    remote_ws_path = integration.get('remote_ws_path') or integration.get('remote_path') or ws_path

    def _append(targets: list[dict[str, str]], host_value: str | None, token_value: str | None, ws_value: str, label: str):
        if not host_value or not token_value:
            return
        normalized_ws = ws_value if ws_value.startswith('/') else f"/{ws_value}"
        entry = {'host': host_value, 'token': token_value, 'ws_path': normalized_ws, 'label': label}
        if entry not in targets:
            targets.append(entry)

    targets: list[dict[str, str]] = []
    if prefer_remote:
        _append(targets, remote_host, remote_token, remote_ws_path, 'remote')
        _append(targets, local_host, local_token, ws_path, 'local')
    else:
        _append(targets, local_host, local_token, ws_path, 'local')
        _append(targets, remote_host, remote_token, remote_ws_path, 'remote')

    if not targets:
        raise HTTPException(status_code=503, detail='integration_missing')
    return targets


def _call_ha_service(domain: str, service: str, payload: dict | None = None):
    integration = _require_integration()
    host = integration.get('host')
    token = integration.get('token')
    body = payload or {}
    try:
        r = requests.post(
            host.rstrip('/') + f"/api/services/{domain}/{service}",
            headers={'Authorization': f"Bearer {token}", 'Content-Type': 'application/json'},
            json=body,
            timeout=8
        )
        r.raise_for_status()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"service_failed:{e}")


def _call_light_service(device_id: str, service: str, extra: dict | None = None):
    payload = {"entity_id": device_id}
    if extra:
        payload.update(extra)
    return _call_ha_service('light', service, payload)


def _purge_stream_sessions_locked(now: float | None = None):
    now = now or time.time()
    expired = [key for key, entry in _stream_sessions.items() if entry.get('expires_at', 0) <= now]
    for key in expired:
        _stream_sessions.pop(key, None)


def _register_stream_session(stream_url: str, entity_id: str, auth_token: str):
    if not stream_url:
        raise HTTPException(status_code=502, detail='camera_stream_url_unavailable')
    parsed = urlparse(stream_url)
    if not parsed.scheme or not parsed.netloc or not parsed.path:
        raise HTTPException(status_code=502, detail='camera_stream_url_invalid')
    path_parts = parsed.path.rsplit('/', 1)
    if len(path_parts) != 2:
        raise HTTPException(status_code=502, detail='camera_stream_path_invalid')
    base_path, resource = path_parts
    base_url = urlunparse((parsed.scheme, parsed.netloc, base_path.rstrip('/'), '', '', ''))
    session_id = secrets.token_urlsafe(16)
    expires_at = time.time() + STREAM_SESSION_TTL
    with _stream_sessions_lock:
        _purge_stream_sessions_locked(expires_at)
        _stream_sessions[session_id] = {
            'base_url': base_url.rstrip('/'),
            'query': parsed.query,
            'entity_id': entity_id,
            'expires_at': expires_at,
            'resource': resource,
            'token': auth_token
        }
    return session_id, expires_at, resource


def _get_stream_session(session_id: str):
    with _stream_sessions_lock:
        entry = _stream_sessions.get(session_id)
        if not entry:
            return None
        if entry.get('expires_at', 0) <= time.time():
            _stream_sessions.pop(session_id, None)
            return None
        return entry


def _build_ws_url(host: str, ws_path: str) -> str:
    if not host:
        return ''
    normalized = host.strip()
    if not normalized:
        return ''
    if '://' not in normalized:
        normalized = f"http://{normalized}"
    parsed = urlparse(normalized)
    netloc = parsed.netloc or parsed.path
    if not netloc:
        return ''
    base_path = parsed.path if parsed.netloc else ''
    ws_scheme = 'wss' if parsed.scheme == 'https' else 'ws'
    target_path = ws_path if ws_path.startswith('/') else f"/{ws_path}"
    ws_path_full = (base_path.rstrip('/') + target_path).replace('//', '/')
    return urlunparse((ws_scheme, netloc, ws_path_full, '', '', ''))


async def _fetch_stream_via_target(entity_id: str, target: dict[str, str]) -> str:
    host = target['host']
    token = target['token']
    ws_path = target['ws_path']
    label = target['label']
    http_error: Exception | None = None

    async def _http_attempt() -> str | None:
        logger.debug('camera %s: requesting HTTP stream via %s (%s)', entity_id, label, host)
        url = host + '/api/stream'
        headers = {'Authorization': f"Bearer {token}", 'Content-Type': 'application/json'}
        payload = {'entity_id': entity_id, 'camera_entity_id': entity_id}
        quick_timeout = httpx.Timeout(connect=3.0, read=3.0, write=3.0, pool=3.0)
        async with httpx.AsyncClient(timeout=quick_timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json() or {}
            stream_url = data.get('url')
            if not stream_url:
                return None
            if stream_url.startswith('http'):
                logger.info('camera %s: received HTTP stream url via %s', entity_id, label)
                return stream_url
            resolved = urljoin(host, stream_url)
            logger.info('camera %s: resolved relative HTTP stream url via %s', entity_id, label)
            return resolved

    try:
        http_url = await _http_attempt()
        if http_url:
            return http_url
    except Exception as exc:
        http_error = exc
        logger.warning('camera %s: HTTP stream attempt via %s failed: %s', entity_id, label, exc)

    ws_url = _build_ws_url(host, ws_path)
    if not ws_url:
        detail = f'{label}:ws_endpoint_missing'
        if http_error:
            detail += f';http={http_error}'
        raise HTTPException(status_code=502, detail=detail)
    logger.debug('camera %s: falling back to websocket stream via %s (%s)', entity_id, label, ws_url)
    try:
        async with websockets.connect(ws_url, ping_interval=None, ping_timeout=None, close_timeout=1) as ws:
            greeting_raw = await asyncio.wait_for(ws.recv(), timeout=5)
            greeting = json.loads(greeting_raw)
            if greeting.get('type') != 'auth_required':
                raise HTTPException(status_code=502, detail='ha_ws_protocol_error')
            await ws.send(json.dumps({'type': 'auth', 'access_token': token}))
            while True:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
                if msg.get('type') == 'auth_ok':
                    break
                if msg.get('type') == 'auth_invalid':
                    raise HTTPException(status_code=401, detail='ha_ws_auth_failed')
            request_id = secrets.randbits(24)
            await ws.send(json.dumps({'id': request_id, 'type': 'camera/stream', 'entity_id': entity_id}))
            while True:
                payload = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
                if payload.get('id') != request_id:
                    continue
                if not payload.get('success'):
                    message = payload.get('error', {}).get('message', 'camera_stream_request_failed')
                    raise HTTPException(status_code=502, detail=f'camera_stream_request_failed:{message}')
                result = payload.get('result') or {}
                url = result.get('url')
                if not url:
                    raise HTTPException(status_code=502, detail='camera_stream_url_unavailable')
                if url.startswith('http'):
                    logger.info('camera %s: received websocket stream url via %s', entity_id, label)
                    return url
                resolved = urljoin(host, url)
                logger.info('camera %s: resolved relative websocket URL via %s', entity_id, label)
                return resolved
    except HTTPException as exc:
        detail = f"{label}:{exc.detail}"
        if http_error:
            detail += f";http={http_error}"
        raise HTTPException(status_code=exc.status_code, detail=detail) from exc
    except asyncio.TimeoutError as exc:
        logger.warning('camera %s: websocket stream timeout via %s: %s', entity_id, label, exc)
        detail = f'{label}:camera_stream_timeout:{exc}'
        if http_error:
            detail += f';http={http_error}'
        raise HTTPException(status_code=504, detail=detail) from exc
    except Exception as exc:
        if http_error:
            logger.error('camera %s: websocket stream failed via %s after HTTP error: %s', entity_id, label, exc)
        else:
            logger.error('camera %s: websocket stream failed via %s: %s', entity_id, label, exc)
        detail = f'{label}:camera_stream_ws_failed:{exc}'
        if http_error:
            detail += f';http={http_error}'
        raise HTTPException(status_code=502, detail=detail) from exc


async def _fetch_hls_stream_url(entity_id: str) -> tuple[str, str]:
    integration = _require_integration()
    targets = _integration_stream_targets(integration)
    errors: list[str] = []
    for target in targets:
        try:
            stream_url = await _fetch_stream_via_target(entity_id, target)
            logger.info('camera %s: stream URL acquired via %s host %s', entity_id, target['label'], target['host'])
            return stream_url, target['token']
        except HTTPException as exc:
            logger.warning('camera %s: %s stream attempt failed: %s', entity_id, target['label'], exc.detail)
            errors.append(f"{target['label']}:{exc.detail}")
        except Exception as exc:
            logger.warning('camera %s: %s stream attempt failed: %s', entity_id, target['label'], exc)
            errors.append(f"{target['label']}:{exc}")
    detail = ' | '.join(errors) if errors else 'camera_stream_unavailable'
    raise HTTPException(status_code=502, detail=detail)


def _merge_query_params(base_query: str | None, client_params) -> dict[str, str]:
    merged: dict[str, str] = {}
    if base_query:
        for key, value in parse_qsl(base_query, keep_blank_values=True):
            merged[key] = value
    if client_params is not None:
        try:
            iterator = client_params.multi_items()
        except AttributeError:
            iterator = client_params.items() if hasattr(client_params, 'items') else []
        for key, value in iterator:
            merged[key] = value
    return merged


def _rewrite_hls_playlist(body: bytes, session_id: str, resource: str) -> bytes:
    """Rewrite relative URIs inside an HLS playlist so they keep using the proxy."""
    if not body:
        return body
    try:
        text = body.decode('utf-8')
    except UnicodeDecodeError:
        return body

    if '.ts' not in text and '.m3u8' not in text:
        return body

    base_dir = resource.rsplit('/', 1)[0] if '/' in resource else ''

    def _proxy_path(target: str) -> str | None:
        stripped = target.strip()
        if not stripped or stripped.startswith('#'):
            return None
        parsed = urlparse(stripped)
        query = parsed.query
        if parsed.scheme in {'http', 'https'}:
            candidate = parsed.path or ''
        elif stripped.startswith('/'):
            candidate = stripped.lstrip('/')
        else:
            candidate = f"{base_dir}/{stripped}" if base_dir else stripped
        candidate = candidate.strip()
        if not candidate:
            return None
        normalized = posixpath.normpath(candidate)
        if normalized.startswith('..'):
            return None
        proxied = f"/api/devices/cameras/streams/{session_id}/{normalized.lstrip('./')}"
        if query:
            proxied = f"{proxied}?{query}"
        return proxied

    rewritten_lines = []
    for line in text.splitlines():
        proxy_candidate = _proxy_path(line)
        rewritten_lines.append(proxy_candidate if proxy_candidate else line)
    return '\n'.join(rewritten_lines).encode('utf-8')


@router.post("/{device_id}/brightness")
def set_brightness(device_id: str, payload: BrightnessPayload, token_payload=Depends(require_token)):
    return _call_light_service(device_id, 'turn_on', {"brightness": int(payload.brightness)})


@router.post("/{device_id}/toggle")
def toggle_device(device_id: str, token_payload=Depends(require_token)):
    return _call_light_service(device_id, 'toggle')


@router.post("/{device_id}/turn_on")
def turn_on_device(device_id: str, payload: TurnOnPayload | None = None, token_payload=Depends(require_token)):
    extra = {}
    if payload and payload.brightness is not None:
        extra['brightness'] = int(payload.brightness)
    return _call_light_service(device_id, 'turn_on', extra)


@router.post("/{device_id}/turn_off")
def turn_off_device(device_id: str, token_payload=Depends(require_token)):
    return _call_light_service(device_id, 'turn_off')


@router.post("/{device_id}/color")
def set_color(device_id: str, payload: ColorPayload, token_payload=Depends(require_token)):
    extra = {}
    if payload.rgb_color:
        rgb = list(payload.rgb_color)
        if len(rgb) != 3:
            raise HTTPException(status_code=400, detail='invalid_rgb_color')
        try:
            rgb = [max(0, min(255, int(c))) for c in rgb]
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail='invalid_rgb_color')
        extra['rgb_color'] = rgb
    if payload.brightness is not None:
        extra['brightness'] = int(payload.brightness)
    if not extra:
        raise HTTPException(status_code=400, detail='missing_parameters')
    return _call_light_service(device_id, 'turn_on', extra)


@router.post("/{entity_id}/trigger")
def trigger_entity(entity_id: str, payload: TriggerPayload, token_payload=Depends(require_token)):
    if not payload.service:
        raise HTTPException(status_code=400, detail='missing_service')
    domain = payload.domain
    if not domain:
        if '.' not in entity_id:
            raise HTTPException(status_code=400, detail='invalid_entity_id')
        domain = entity_id.split('.', 1)[0]
    data = {'entity_id': entity_id}
    if isinstance(payload.data, dict):
        data.update(payload.data)
    return _call_ha_service(domain, payload.service, data)


def _camera_proxy_endpoint(entity_id: str, endpoint: str) -> tuple[str, dict[str, str]]:
    integration = _require_integration()
    host = integration.get('host')
    token = integration.get('token')
    encoded = quote(entity_id, safe='')
    url = host.rstrip('/') + f"/api/{endpoint}/{encoded}"
    return url, {'Authorization': f"Bearer {token}"}


def _camera_proxy_request(entity_id: str, endpoint: str, stream: bool = False):
    url, headers = _camera_proxy_endpoint(entity_id, endpoint)
    timeout = (8, None) if stream else 15
    try:
        resp = requests.get(url, headers=headers, stream=stream, timeout=timeout)
        resp.raise_for_status()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"camera_proxy_failed:{exc}") from exc
    return resp


def _camera_stream_iterator(resp, chunk_size: int = 8192):
    try:
        for chunk in resp.iter_content(chunk_size=chunk_size):
            if chunk:
                yield chunk
    except ChunkedEncodingError:
        # Upstream camera closed the stream abruptly; treat as finished.
        return
    finally:
        resp.close()


def _httpx_timeout(stream: bool) -> httpx.Timeout:
    if stream:
        return httpx.Timeout(connect=8.0, read=None, write=8.0, pool=None)
    return httpx.Timeout(15.0)


async def _open_httpx_stream(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, str] | None = None,
    timeout: httpx.Timeout | None = None,
    error_detail: str = 'camera_proxy_failed'
) -> tuple[httpx.AsyncClient, httpx.Response]:
    timeout = timeout or _httpx_timeout(True)
    client = httpx.AsyncClient(timeout=timeout)
    try:
        # NOTE: httpx.AsyncClient.get does not accept a `stream` kwarg.
        # Use a regular .get() and stream the response via `aiter_bytes()` later.
        resp = await client.get(url, headers=headers, params=params)
        try:
            resp.raise_for_status()
        except httpx.HTTPStatusError as http_exc:
            # Capture response details for diagnostics (truncate body)
            resp_body = None
            try:
                resp_body = (await resp.aread()).decode('utf-8', errors='replace')
                if resp_body and len(resp_body) > 1024:
                    resp_body = resp_body[:1024] + '...'
            except Exception:
                resp_body = None
            retry_after = None
            try:
                retry_after = resp.headers.get('Retry-After')
            except Exception:
                retry_after = None
            logger.warning('camera stream proxy: upstream responded with error url=%s status=%s headers=%s retry_after=%s body=%s', url, getattr(resp, 'status_code', None), dict(resp.headers), retry_after, resp_body)
            # Re-raise so the outer handler can include useful diagnostics; include retry-after in the raised error detail
            raise
        return client, resp
    except Exception as exc:
        await client.aclose()
        # If it's an HTTPStatusError include response status and Retry-After for easier debugging and client behavior
        if isinstance(exc, httpx.HTTPStatusError) and getattr(exc, 'response', None) is not None:
            status = exc.response.status_code
            retry_after = None
            try:
                retry_after = exc.response.headers.get('Retry-After')
            except Exception:
                retry_after = None
            if retry_after:
                detail = f"{error_detail}:http_status_{status}:retry_after_{retry_after}:{exc}"
            else:
                detail = f"{error_detail}:http_status_{status}:{exc}"
        else:
            detail = f"{error_detail}:{exc}"
        raise HTTPException(status_code=502, detail=detail) from exc


async def _fetch_httpx_bytes(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, str] | None = None,
    timeout: httpx.Timeout | None = None,
    error_detail: str = 'camera_proxy_failed'
) -> tuple[bytes, httpx.Headers]:
    timeout = timeout or _httpx_timeout(False)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.get(url, headers=headers, params=params)
            resp.raise_for_status()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"{error_detail}:{exc}") from exc
        return resp.content, resp.headers


def _streaming_response_from_httpx(
    client: httpx.AsyncClient,
    resp: httpx.Response,
    default_media_type: str,
    extra_headers: dict[str, str] | None = None
) -> StreamingResponse:
    async def iterator():
        try:
            async for chunk in resp.aiter_bytes():
                if chunk:
                    yield chunk
        except asyncio.CancelledError:
            raise
        except Exception:
            return
        finally:
            try:
                await resp.aclose()
            finally:
                await client.aclose()

    media_type = resp.headers.get('Content-Type') or default_media_type
    streaming = StreamingResponse(iterator(), media_type=media_type)
    if extra_headers:
        for key, value in extra_headers.items():
            streaming.headers[key] = value
    return streaming


@router.get("/cameras/{entity_id:path}/stream")
def camera_stream(entity_id: str, token_payload=Depends(_require_token_flexible)):
    resp = _camera_proxy_request(entity_id, 'camera_proxy_stream', stream=True)
    media_type = resp.headers.get('Content-Type') or 'multipart/x-mixed-replace; boundary=frame'
    return StreamingResponse(
        _camera_stream_iterator(resp),
        media_type=media_type,
        headers={'Cache-Control': 'no-store'}
    )


@router.get("/cameras/{entity_id:path}/snapshot")
def camera_snapshot(entity_id: str, token_payload=Depends(_require_token_flexible)):
    resp = _camera_proxy_request(entity_id, 'camera_proxy', stream=False)
    media_type = resp.headers.get('Content-Type') or 'image/jpeg'
    return Response(content=resp.content, media_type=media_type)


@router.post("/cameras/{entity_id:path}/stream_session")
async def camera_stream_session(
    entity_id: str,
    mode: str | None = Query(None),
    token_payload=Depends(_require_token_flexible)
):
    timeout_seconds = _resolve_stream_session_timeout(mode)
    logger.info('camera %s: creating stream session (mode=%s, timeout=%ss)', entity_id, mode or 'auto', timeout_seconds)
    try:
        stream_url, stream_token = await asyncio.wait_for(_fetch_hls_stream_url(entity_id), timeout=timeout_seconds)
    except HTTPException:
        logger.warning('camera %s: stream session failed with HTTPException', entity_id)
        raise
    except asyncio.TimeoutError as exc:
        logger.warning('camera %s: stream session timed out after %ss', entity_id, timeout_seconds)
        raise HTTPException(status_code=504, detail='camera_stream_timeout') from exc
    session_id, expires_at, resource = _register_stream_session(stream_url, entity_id, stream_token)
    logger.info('camera %s: stream session %s created (ttl=%ss)', entity_id, session_id, int(expires_at - time.time()))
    ttl = max(1, int(expires_at - time.time()))
    playlist = f"/api/devices/cameras/streams/{session_id}/{resource}"
    return {"session": session_id, "playlist": playlist, "format": "hls", "expires_in": ttl}


@router.get("/cameras/streams/{session_id}/{resource:path}")
async def camera_stream_proxy(
    session_id: str,
    resource: str,
    request: Request,
    authorization: str = Header(None),
    token: str | None = Query(None)
):
    # Allow bearer header or token query param to continue working for other clients.
    if (authorization and authorization.lower() != 'null') or token:
        _require_token_flexible(authorization, token)
    entry = _get_stream_session(session_id)
    if not entry:
        raise HTTPException(status_code=404, detail='stream_session_expired')
    if '..' in resource.split('/'):
        raise HTTPException(status_code=400, detail='invalid_stream_resource')
    upstream = f"{entry['base_url']}/{resource}"
    params = _merge_query_params(entry.get('query'), request.query_params)
    auth_token = entry.get('token')
    if not auth_token:
        integration = _require_integration()
        auth_token = integration.get('token')
        if not auth_token:
            raise HTTPException(status_code=503, detail='integration_missing')
    auth_headers = {'Authorization': f"Bearer {auth_token}"}
    if resource.lower().endswith('.m3u8'):
        start_time = time.time()
        try:
            body, upstream_headers = await _fetch_httpx_bytes(
                upstream,
                headers=auth_headers,
                params=params,
                timeout=_httpx_timeout(False),
                error_detail='camera_hls_proxy_failed'
            )
        except HTTPException as exc:
            duration = time.time() - start_time
            # Surface HLS-specific diagnostics and treat upstream 400 (Bad Request)
            # as a transient "playlist not ready" condition so clients back off.
            detail_text = str(getattr(exc, 'detail', repr(exc)))
            logger.warning('[hls] camera stream proxy: playlist fetch failed session=%s upstream=%s resource=%s duration=%.3fs detail=%s', session_id, upstream, resource, duration, detail_text)
            # If upstream returned a 400/Bad Request for a playlist request (often
            # indicates part/msn not available yet), return 503 with a small
            # Retry-After so clients (hls.js) will back off rather than thrash.
            try:
                lowered = detail_text.lower()
            except Exception:
                lowered = detail_text
            if '400' in lowered or 'bad request' in lowered:
                retry_after = '1'
                logger.info('[hls] camera stream proxy: mapping upstream 400 -> 503 Retry-After=%s session=%s resource=%s', retry_after, session_id, resource)
                return Response(content='warming', status_code=503, media_type='text/plain', headers={'Retry-After': retry_after})
            # Otherwise re-raise the original HTTPException
            raise
        duration = time.time() - start_time
        try:
            logger.debug('camera stream proxy: playlist proxied session=%s upstream=%s resource=%s duration=%.3fs content_type=%s', session_id, upstream, resource, duration, upstream_headers.get('Content-Type'))
        except Exception:
            logger.debug('camera stream proxy: playlist proxied session=%s upstream=%s resource=%s duration=%.3fs', session_id, upstream, resource, duration)
        body = _rewrite_hls_playlist(body, session_id, resource)
        content_type = upstream_headers.get('Content-Type') or 'application/vnd.apple.mpegurl'
        return Response(content=body, media_type=content_type, headers={'Cache-Control': 'no-store'})
    start_time = time.time()
    last_exc: Exception | None = None
    attempt = 0
    while attempt < CAMERA_HLS_PROXY_MAX_RETRIES:
        attempt += 1
        try:
            client, resp = await _open_httpx_stream(
                upstream,
                headers=auth_headers,
                params=params,
                timeout=_httpx_timeout(True),
                error_detail='camera_hls_proxy_failed'
            )
            duration = time.time() - start_time
            try:
                logger.debug('camera stream proxy: stream proxied session=%s upstream=%s resource=%s duration=%.3fs headers=%s attempt=%d', session_id, upstream, resource, duration, dict(resp.headers), attempt)
            except Exception:
                logger.debug('camera stream proxy: stream proxied session=%s upstream=%s resource=%s duration=%.3fs attempt=%d', session_id, upstream, resource, duration, attempt)
            return _streaming_response_from_httpx(
                client,
                resp,
                'video/mp2t',
                extra_headers={'Cache-Control': 'no-store'}
            )
        except HTTPException as exc:
            duration = time.time() - start_time
            last_exc = exc
            logger.warning('camera stream proxy: stream fetch failed session=%s upstream=%s resource=%s duration=%.3fs attempt=%d detail=%s', session_id, upstream, resource, duration, attempt, getattr(exc, 'detail', repr(exc)))
            if attempt < CAMERA_HLS_PROXY_MAX_RETRIES:
                backoff = CAMERA_HLS_PROXY_BACKOFF_BASE * (2 ** (attempt - 1))
                logger.info('camera stream proxy: retrying after %.1fs (attempt %d/%d)', backoff, attempt + 1, CAMERA_HLS_PROXY_MAX_RETRIES)
                await asyncio.sleep(backoff)
            else:
                break

    # All attempts exhausted — return a transient 503 with Retry-After to let clients back off/wait
    logger.warning('camera stream proxy: all attempts failed session=%s upstream=%s resource=%s last_error=%s', session_id, upstream, resource, getattr(last_exc, 'detail', repr(last_exc)))
    # Try to surface upstream Retry-After when available (was attached to error detail earlier)
    retry_after_header = '3'
    try:
        if isinstance(last_exc, HTTPException) and getattr(last_exc, 'detail', None):
            m = re.search(r'retry_after_([0-9]+)', str(last_exc.detail))
            if m:
                retry_after_header = m.group(1)
    except Exception:
        retry_after_header = '3'
    return Response(content='warming', status_code=503, media_type='text/plain', headers={'Retry-After': retry_after_header})
