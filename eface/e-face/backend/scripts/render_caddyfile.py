import os
from pathlib import Path

RUNTIME_DIR = Path(__file__).resolve().parent.parent / "runtime"
OUTPUT_FILE = RUNTIME_DIR / "Caddyfile"

APP_HOST = os.environ.get("APP_HOST", "127.0.0.1")
APP_PORT = os.environ.get("APP_PORT", "9000")
HTTP_PORT = os.environ.get("PUBLIC_HTTP_PORT", "8000")
ENABLE_HTTPS = os.environ.get("ENABLE_HTTPS", "false").lower() == "true"
DOMAIN = os.environ.get("E_FACE_DOMAIN", "").strip()
TLS_EMAIL = os.environ.get("E_FACE_TLS_EMAIL", "").strip()

RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

lines = []

if not ENABLE_HTTPS or not DOMAIN:
    lines.append("{\n    auto_https off\n}")

lines.append(
    f":{HTTP_PORT} {{\n"
    f"    encode gzip\n"
    f"    reverse_proxy {APP_HOST}:{APP_PORT}\n"
    "}"
)

if ENABLE_HTTPS and DOMAIN:
    tls_line = f"    tls {TLS_EMAIL}" if TLS_EMAIL else "    tls"
    lines.append(
        f"{DOMAIN} {{\n"
        f"{tls_line}\n"
        f"    encode gzip\n"
        f"    reverse_proxy {APP_HOST}:{APP_PORT}\n"
        "}"
    )

OUTPUT_FILE.write_text("\n\n".join(lines), encoding="utf-8")
print(f"[e-face] Caddyfile generated at {OUTPUT_FILE}")
