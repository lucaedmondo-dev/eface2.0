import time
from typing import Any, Dict

_registry_snapshot: Dict[str, Any] | None = None


def set_registry_snapshot(snapshot: Dict[str, Any] | None):
    global _registry_snapshot
    if snapshot is None:
        _registry_snapshot = None
        return
    # ensure we always track timestamp for diagnostics
    snap = dict(snapshot)
    snap.setdefault('ts', time.time())
    _registry_snapshot = snap


def get_registry_snapshot() -> Dict[str, Any] | None:
    return _registry_snapshot
