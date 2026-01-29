from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel

from ..cloud import get_cloud_settings, sanitize_cloud_settings
from ..core import read_config, require_token, write_config

router = APIRouter()


class ConfigPayload(BaseModel):
    site_name: str | None = None
    advanced: dict | None = {}


@router.get("")
def get_config(authorization: str | None = Header(default=None)):
    """Return site configuration; authentication optional."""
    # if a token is provided validate it, otherwise allow anonymous access
    if authorization:
        require_token(authorization)
    data = read_config()
    return data


@router.post("")
def post_config(cfg: ConfigPayload, _=Depends(require_token)):
    data = read_config()
    if cfg.site_name is not None:
        data["site_name"] = cfg.site_name
    data["advanced"] = cfg.advanced or {}
    write_config(data)
    return {"ok": True}


@router.get("/cloud")
def get_cloud_config():
    return sanitize_cloud_settings(get_cloud_settings())
