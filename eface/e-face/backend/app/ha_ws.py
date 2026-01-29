import asyncio
import json
import logging
from typing import Set

import websockets
from fastapi import WebSocket

from .core import read_config, load_registry_snapshot
from .registry_cache import set_registry_snapshot

logger = logging.getLogger("e-face.ha_ws")

# connected frontend websockets (starlette WebSocket objects)
clients: Set[WebSocket] = set()
last_event: dict | None = None
last_connect_time: float | None = None
recent_events: list = []
MAX_EVENTS = 200


def _extract_entity_update(event_payload: dict | None):
    if not event_payload:
        return None
    data = event_payload.get('data') if isinstance(event_payload, dict) else {}
    entity_id = event_payload.get('entity_id') or (data or {}).get('entity_id')
    new_state = (
        event_payload.get('new_state')
        or event_payload.get('state')
        or (data or {}).get('new_state')
        or (data or {}).get('state')
    )
    old_state = event_payload.get('old_state') or (data or {}).get('old_state')
    if not entity_id or not isinstance(new_state, dict):
        return None
    return {
        'entity_id': entity_id,
        'state': new_state.get('state'),
        'attributes': new_state.get('attributes') or {},
        'old_state': (old_state or {}).get('state'),
        'last_changed': new_state.get('last_changed') or new_state.get('last_updated'),
        'raw_new_state': new_state,
        'raw_old_state': old_state,
    }


async def broadcast(message: dict):
    """Send a JSON message to all connected frontend websockets."""
    to_remove = []
    for ws in list(clients):
        try:
            await ws.send_json(message)
        except Exception:
            to_remove.append(ws)
    for ws in to_remove:
        try:
            clients.remove(ws)
        except KeyError:
            pass


def get_status():
    """Return diagnostics info for admin UI."""
    return {
        'ws_clients': len(clients),
        'last_event': last_event,
        'last_connect_time': last_connect_time,
        'recent_events_count': len(recent_events),
    }


async def ha_ws_task():
    """Background task that connects to Home Assistant websocket and forwards events to clients."""
    while True:
        try:
            cfg = read_config()
            integration = (cfg.get('advanced') or {}).get('integration') or {}
            if not integration.get('enabled'):
                await asyncio.sleep(3)
                continue
            host = (integration.get('host') or '').rstrip('/')
            token = integration.get('token')
            if not host or not token:
                logger.info("HA integration not fully configured, sleeping")
                await asyncio.sleep(3)
                continue

            # build websocket URL
            if host.startswith('https://'):
                ws_url = 'wss://' + host[len('https://'):]
            elif host.startswith('http://'):
                ws_url = 'ws://' + host[len('http://'):]
            else:
                # assume http
                ws_url = 'ws://' + host
            ws_url = ws_url.rstrip('/') + '/api/websocket'

            logger.info(f"Connecting to Home Assistant websocket at {ws_url}")
            async with websockets.connect(ws_url, ping_interval=20, ping_timeout=10) as ws:
                # send auth according to HA WS API
                global last_connect_time
                last_connect_time = asyncio.get_event_loop().time()
                logger.info(f"HA websocket connected at {last_connect_time}")

                # Home Assistant may first send an auth_required message; wait for it
                try:
                    server_msg = json.loads(await ws.recv())
                except websockets.exceptions.ConnectionClosedOK:
                    logger.info("HA websocket closed immediately after connect (1000 OK)")
                    continue
                except Exception as e:
                    # fallback: continue to send auth
                    logger.debug("Error receiving initial server message: %s", e)
                    server_msg = {}

                logger.debug("HA websocket initial server message: %s", server_msg)

                # send auth (handle both auth_required and servers that don't send it)
                await ws.send(json.dumps({"type": "auth", "access_token": token}))
                try:
                    auth_raw = await ws.recv()
                    auth_resp = json.loads(auth_raw)
                except websockets.exceptions.ConnectionClosedOK:
                    logger.info("HA websocket closed during auth (1000 OK)")
                    continue
                except Exception as e:
                    logger.debug("Error receiving auth response: %s", e)
                    continue

                logger.debug("HA websocket auth response raw: %s", auth_resp)
                if auth_resp.get('type') == 'auth_invalid':
                    # log details to help debugging (do not leak token)
                    logger.error("Home Assistant websocket: auth invalid - reason: %s", auth_resp.get('message') or auth_resp)
                    await asyncio.sleep(10)
                    continue
                sync_meta = (cfg.get('synced') or {})
                tracked_entities = [e for e in (sync_meta.get('tracked_entities') or []) if isinstance(e, str)]
                sync_version = sync_meta.get('synced_at')
                tracked_sub_id = 5
                state_event_sub_id = None
                if tracked_entities:
                    entity_sub = {"id": tracked_sub_id, "type": "subscribe_entities", "entity_ids": tracked_entities}
                    await ws.send(json.dumps(entity_sub))
                    logger.info("Subscribed to %d HA entities", len(tracked_entities))
                    state_event_sub_id = tracked_sub_id + 1
                    await ws.send(json.dumps({"id": state_event_sub_id, "type": "subscribe_events", "event_type": "state_changed"}))
                    logger.info("Subscribed to global state_changed events for realtime extras")
                else:
                    tracked_sub_id = 1
                    state_event_sub_id = tracked_sub_id
                    await ws.send(json.dumps({"id": state_event_sub_id, "type": "subscribe_events", "event_type": "state_changed"}))
                    logger.info("Subscribed to fallback state_changed events")

                # request registries (areas, devices, entities) so we can map entity->device->area
                reg_ids = {"areas": 10, "devices": 11, "entities": 12}
                try:
                    await ws.send(json.dumps({"id": reg_ids['areas'], "type": "config/area_registry/list"}))
                    await ws.send(json.dumps({"id": reg_ids['devices'], "type": "config/device_registry/list"}))
                    await ws.send(json.dumps({"id": reg_ids['entities'], "type": "config/entity_registry/list"}))
                    logger.info("Requested HA registries (areas/devices/entities)")
                except Exception:
                    logger.exception("Failed to request HA registries")

                # REST fallback: if websocket registry results aren't delivered promptly,
                # use the config API endpoints to produce a registry snapshot and broadcast it immediately.
                try:
                    snapshot = load_registry_snapshot(integration, allow_ws_fallback=False)
                    if snapshot and (snapshot.get('areas') or snapshot.get('devices') or snapshot.get('entities')):
                        set_registry_snapshot({ **snapshot, 'ts': asyncio.get_event_loop().time(), 'source': 'rest-fallback' })
                        payload = { **snapshot, 'type': 'ha_registry', 'source': 'rest-fallback' }
                        await broadcast(payload)
                        logger.info(
                            "Broadcasted HA registry via REST fallback; areas:%d devices:%d entities:%d",
                            len(snapshot.get('areas') or {}),
                            len(snapshot.get('devices') or {}),
                            len(snapshot.get('entities') or {})
                        )
                except Exception:
                    logger.exception("Error during REST registry fallback")

                # placeholders for registry results
                reg_results = {'areas': None, 'devices': None, 'entities': None}

                last_sync_check = asyncio.get_event_loop().time()

                while True:
                    try:
                        msg = await ws.recv()
                    except websockets.exceptions.ConnectionClosedOK:
                        logger.info("HA websocket closed cleanly (1000 OK); will reconnect")
                        break
                    except websockets.exceptions.ConnectionClosedError as ccerr:
                        # Don't log "message too big" errors as warnings - they're expected with large HA instances
                        if "1009" in str(ccerr) or "message too big" in str(ccerr).lower():
                            logger.debug("HA websocket closed: message too big (expected with 2000+ entities)")
                        else:
                            logger.warning("HA websocket closed with error: %s", ccerr)
                        break
                    except Exception as e:
                        logger.exception("Error reading from HA websocket: %s", e)
                        break

                    try:
                        data = json.loads(msg)
                    except Exception:
                        continue

                    # handle registry result responses (type == 'result')
                    if data.get('type') == 'result' and data.get('id') in reg_ids.values():
                        try:
                            # find which registry matched
                            for k, v in reg_ids.items():
                                if v == data.get('id'):
                                    reg_results[k] = data.get('result')
                                    logger.debug("Received registry %s with %d items", k, len(reg_results[k] or []))
                                    break
                        except Exception:
                            logger.exception("Error processing registry result: %s", data)

                        # when we have all three, build mappings and broadcast to clients
                        if all(reg_results.values()):
                            try:
                                areas = reg_results['areas'] or []
                                devices = reg_results['devices'] or []
                                entities = reg_results['entities'] or []

                                area_map = {}
                                for area in areas:
                                    area_id = area.get('area_id') or area.get('id') or area.get('slug')
                                    if not area_id:
                                        continue
                                    area_map[area_id] = area.get('name') or area_id

                                device_map = {}
                                for dev in devices:
                                    dev_id = dev.get('id') or dev.get('device_id')
                                    if not dev_id:
                                        continue
                                    device_map[dev_id] = {
                                        'name': dev.get('name') or dev.get('name_by_user') or dev.get('original_name') or dev_id,
                                        'area_id': dev.get('area_id') or dev.get('area')
                                    }

                                entity_map = {}
                                for ent in entities:
                                    ent_id = ent.get('entity_id')
                                    if not ent_id:
                                        continue
                                    entity_map[ent_id] = {
                                        'device_id': ent.get('device_id'),
                                        'area_id': ent.get('area_id') or ent.get('area')
                                    }

                                # build a simple table of entity -> device name -> area name
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
                                        'area_name': area_map.get(resolved_area),
                                    })

                                # store snapshot for diagnostics and broadcast
                                snapshot = {'areas': area_map, 'devices': device_map, 'entities': entity_map, 'table': table, 'ts': asyncio.get_event_loop().time(), 'source': 'ws'}
                                set_registry_snapshot(snapshot)
                                await broadcast({**snapshot, 'type': 'ha_registry'})
                                logger.info("Broadcasted HA registry to frontends; areas:%d devices:%d entities:%d", len(area_map), len(device_map), len(entity_map))
                            except Exception:
                                logger.exception("Error building registry broadcast")

                        # continue to next message
                        continue

                    if data.get('type') == 'event':
                        event_payload = data.get('event') or data.get('result') or {}
                        event_type = (event_payload or {}).get('event_type')
                        if event_type in ('area_registry_updated', 'device_registry_updated', 'entity_registry_updated'):
                            try:
                                reg_results = {'areas': None, 'devices': None, 'entities': None}
                                await ws.send(json.dumps({"id": reg_ids['areas'], "type": "config/area_registry/list"}))
                                await ws.send(json.dumps({"id": reg_ids['devices'], "type": "config/device_registry/list"}))
                                await ws.send(json.dumps({"id": reg_ids['entities'], "type": "config/entity_registry/list"}))
                                logger.info("Registry update event received; re-requested registries")
                            except Exception:
                                logger.exception("Failed to re-request registries after update event")
                            continue

                        if data.get('id') in {tracked_sub_id, state_event_sub_id} or event_type == 'state_changed' or not event_type:
                            global last_event, recent_events
                            last_event = event_payload
                            recent_events.append({'ts': asyncio.get_event_loop().time(), 'event': last_event})
                            if len(recent_events) > MAX_EVENTS:
                                recent_events.pop(0)

                            update_payload = _extract_entity_update(event_payload)
                            if update_payload:
                                await broadcast({
                                    'type': 'ha_entity_update',
                                    **update_payload
                                })

                            await broadcast({"type": "ha_event", "event": event_payload})

                    # periodically detect configuration refreshes and restart subscription
                    now = asyncio.get_event_loop().time()
                    if now - last_sync_check > 5:
                        last_sync_check = now
                        try:
                            latest_cfg = read_config()
                            latest_sync_version = (latest_cfg.get('synced') or {}).get('synced_at')
                            if latest_sync_version and latest_sync_version != sync_version:
                                logger.info("Detected new synced configuration (%s -> %s); restarting HA websocket", sync_version, latest_sync_version)
                                break
                        except Exception:
                            logger.exception("Failed to check synced configuration version")
        except Exception as e:
            logger.exception("HA websocket client error: %s", e)
            await asyncio.sleep(5)


async def start_background(app):
    """Start the HA websocket background task (called on app startup)."""
    # store task on app.state so it can be cancelled on shutdown if needed
    app.state.ha_ws_task = asyncio.create_task(ha_ws_task())


def clear_recent_events():
    global recent_events
    recent_events = []


async def stop_background(app):
    task = getattr(app.state, 'ha_ws_task', None)
    if task:
        task.cancel()