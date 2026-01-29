from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from ..core import read_config, write_config, require_token, get_user, create_user, verify_user_password, set_user_password

router = APIRouter()


class CreateUserPayload(BaseModel):
    username: str
    temp_password: str
    must_change: bool = True
    is_admin: bool = False


def _is_admin(token_payload, x_admin_pass: str | None):
    from ..core import verify_admin_password
    if isinstance(token_payload, dict) and token_payload.get('is_admin'):
        return True
    if x_admin_pass and verify_admin_password(x_admin_pass):
        return True
    return False


@router.post("")
def create_user_admin(payload: CreateUserPayload, token_payload=Depends(require_token), x_admin_pass: str | None = Header(None)):
    # admin-only
    if not _is_admin(token_payload, x_admin_pass):
        raise HTTPException(status_code=403, detail="Admin required")
    ok = create_user(payload.username, payload.temp_password, payload.must_change, payload.is_admin)
    if not ok:
        raise HTTPException(status_code=409, detail="User exists")
    return {"ok": True}


@router.get("")
def list_users(token_payload=Depends(require_token), x_admin_pass: str | None = Header(None)):
    if not _is_admin(token_payload, x_admin_pass):
        raise HTTPException(status_code=403, detail="Admin required")
    data = read_config()
    users = data.get('users', [])
    # don't expose password hashes
    return [{"username": u.get('username'), "is_admin": bool(u.get('is_admin')), "must_change": bool(u.get('must_change'))} for u in users]


class ResetPayload(BaseModel):
    username: str
    new_temp_password: str | None = None


@router.post("/reset")
def reset_user_password(payload: ResetPayload, token_payload=Depends(require_token), x_admin_pass: str | None = Header(None)):
    if not _is_admin(token_payload, x_admin_pass):
        raise HTTPException(status_code=403, detail="Admin required")
    # if not provided, generate a simple temp password (caller can provide their own)
    newpw = payload.new_temp_password or (payload.username + "-temp")
    ok = set_user_password(payload.username, newpw, must_change=True)
    if not ok:
        raise HTTPException(status_code=404, detail="User not found")
    return {"ok": True, "temp_password": newpw}


class ChangePasswordPayload(BaseModel):
    old_password: str | None = None
    new_password: str


@router.post("/change-password")
def change_password(payload: ChangePasswordPayload, token_payload=Depends(require_token)):
    # user changes their own password. token_payload must include 'sub' username
    if not isinstance(token_payload, dict):
        raise HTTPException(status_code=401, detail="Invalid authorization")
    username = token_payload.get('sub')
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token subject")

    # verify old password if provided or allow password change if must_change is True
    user = get_user(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.get('must_change'):
        # require the client to provide old_password (temp password)
        if not payload.old_password or not verify_user_password(username, payload.old_password):
            raise HTTPException(status_code=403, detail="Old password required or incorrect")
    else:
        # if not must_change, require old_password verification for safety
        if not payload.old_password or not verify_user_password(username, payload.old_password):
            raise HTTPException(status_code=403, detail="Old password required or incorrect")

    ok = set_user_password(username, payload.new_password, must_change=False)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to set password")
    # issue a fresh token with must_change cleared
    from ..core import create_access_token
    user = get_user(username)
    token = create_access_token(username, is_admin=bool(user.get('is_admin')), must_change=False)
    return {"ok": True, "access_token": token}
