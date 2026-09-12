"""Signup/login/me. Additive -- doesn't gate the existing course routes,
since the React frontend has no auth wiring and gating them would break
it. The Flutter app under ../../mobile/ is the first client that uses
this.
"""
import jwt as pyjwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from . import store
from .models import LoginRequest, SignupRequest, TokenResponse, UserOut
from .security import create_access_token, decode_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])
_bearer = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(_bearer)) -> dict:
    if not credentials:
        raise HTTPException(401, "Not authenticated")
    try:
        user_id = decode_access_token(credentials.credentials)
    except pyjwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token")
    user = store.find_by_id(user_id)
    if not user:
        raise HTTPException(401, "User not found")
    return user


def _to_out(user: dict) -> UserOut:
    return UserOut(id=user["id"], email=user["email"], name=user["name"], role=user["role"])


@router.post("/signup", response_model=TokenResponse, status_code=201)
def signup(body: SignupRequest):
    try:
        user = store.create_user(body.email, body.name, hash_password(body.password), body.role)
    except ValueError as e:
        raise HTTPException(409, str(e))
    return TokenResponse(access_token=create_access_token(user["id"]), user=_to_out(user))


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    user = store.find_by_email(body.email)
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    return TokenResponse(access_token=create_access_token(user["id"]), user=_to_out(user))


@router.get("/me", response_model=UserOut)
def me(user: dict = Depends(get_current_user)):
    return _to_out(user)
