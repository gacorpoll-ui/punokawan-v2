"""Authentication endpoints — register, login, profile."""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, EmailStr

from ..core.auth import create_token, decode_token, hash_password, verify_password
from ..core.config import settings
from ..core.database import get_connection

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    user: dict
    trial_days_left: int


def get_current_user(authorization: str = Header(...)) -> dict:
    """Dependency: extract user from JWT token."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "Invalid authorization header")
    try:
        payload = decode_token(authorization[7:])
        return {"id": payload["sub"], "email": payload["email"], "tier": payload["tier"]}
    except Exception:
        raise HTTPException(401, "Invalid or expired token")


@router.post("/register")
def register(req: RegisterRequest):
    if len(req.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")

    conn = get_connection()
    existing = conn.execute("SELECT id FROM users WHERE email=?", (req.email,)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(409, "Email already registered")

    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    trial_end = now + timedelta(days=settings.TRIAL_DAYS)

    conn.execute(
        "INSERT INTO users (id, email, password_hash, name, created_at, trial_ends_at, subscription_tier) VALUES (?,?,?,?,?,?,?)",
        (user_id, req.email, hash_password(req.password), req.name, now.isoformat(), trial_end.isoformat(), "trial"),
    )
    conn.commit()
    conn.close()

    token = create_token(user_id, req.email, "trial")
    return TokenResponse(
        access_token=token,
        user={"id": user_id, "email": req.email, "name": req.name, "tier": "trial"},
        trial_days_left=settings.TRIAL_DAYS,
    )


@router.post("/login")
def login(req: LoginRequest):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE email=?", (req.email,)).fetchone()
    conn.close()

    if not row or not verify_password(req.password, row["password_hash"]):
        raise HTTPException(401, "Invalid email or password")

    user = dict(row)
    trial_end = datetime.fromisoformat(user["trial_ends_at"]) if user.get("trial_ends_at") else None
    trial_days_left = max(0, (trial_end - datetime.now(timezone.utc)).days) if trial_end else 0

    # Check if trial expired and no paid subscription
    tier = user.get("subscription_tier", "trial")
    if tier == "trial" and trial_days_left <= 0:
        tier = "expired"

    token = create_token(user["id"], user["email"], tier)
    return TokenResponse(
        access_token=token,
        user={"id": user["id"], "email": user["email"], "name": user["name"], "tier": tier},
        trial_days_left=trial_days_left,
    )


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE id=?", (user["id"],)).fetchone()
    conn.close()

    if not row:
        raise HTTPException(404, "User not found")

    u = dict(row)
    return {
        "id": u["id"],
        "email": u["email"],
        "name": u["name"],
        "tier": u.get("subscription_tier", "trial"),
        "created_at": u["created_at"],
        "trial_ends_at": u.get("trial_ends_at"),
    }
