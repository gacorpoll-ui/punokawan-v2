"""Admin endpoints — user management, subscriptions, system monitoring."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from ..core.auth import hash_password
from ..core.database import get_connection
from ..routers.auth_router import get_current_user
from ..services.signal_bridge import get_performance_from_db, get_system_status

router = APIRouter(prefix="/api/admin", tags=["admin"])


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Dependency: require admin role."""
    conn = get_connection()
    row = conn.execute("SELECT role FROM users WHERE id=?", (user["id"],)).fetchone()
    conn.close()
    if not row or row["role"] != "admin":
        raise HTTPException(403, "Admin access required")
    return user


@router.get("/users")
def list_users(admin: dict = Depends(require_admin)):
    """List all registered users."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, email, name, subscription_tier, trial_ends_at, subscription_ends_at, role, created_at FROM users ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return {"users": [dict(r) for r in rows], "total": len(rows)}


@router.post("/users")
def create_user(data: dict, admin: dict = Depends(require_admin)):
    """Admin: create a new user manually."""
    email = data.get("email", "")
    password = data.get("password", "changeme123")
    name = data.get("name", "")
    tier = data.get("tier", "pro")
    role = data.get("role", "user")

    if not email:
        raise HTTPException(400, "Email required")

    conn = get_connection()
    existing = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(409, "Email already exists")

    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    conn.execute(
        "INSERT INTO users (id, email, password_hash, name, created_at, trial_ends_at, subscription_tier, role) VALUES (?,?,?,?,?,?,?,?)",
        (user_id, email, hash_password(password), name, now.isoformat(), None, tier, role),
    )
    conn.commit()
    conn.close()
    return {"id": user_id, "email": email, "tier": tier, "role": role, "status": "created"}


@router.put("/users/{user_id}/subscription")
def update_subscription(user_id: str, data: dict, admin: dict = Depends(require_admin)):
    """Update user subscription tier."""
    tier = data.get("tier", "trial")
    ends_at = data.get("ends_at")  # ISO date string, or None

    if tier not in ("trial", "pro", "enterprise", "expired"):
        raise HTTPException(400, "Invalid tier")

    conn = get_connection()
    conn.execute(
        "UPDATE users SET subscription_tier=?, subscription_ends_at=? WHERE id=?",
        (tier, ends_at, user_id),
    )

    # Also log subscription change
    conn.execute(
        "INSERT INTO subscriptions (user_id, tier, status, started_at, expires_at) VALUES (?,?,?,?,?)",
        (user_id, tier, "active", datetime.now(timezone.utc).isoformat(), ends_at),
    )
    conn.commit()
    conn.close()
    return {"user_id": user_id, "tier": tier, "status": "updated"}


@router.delete("/users/{user_id}")
def delete_user(user_id: str, admin: dict = Depends(require_admin)):
    """Delete a user."""
    conn = get_connection()
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return {"user_id": user_id, "status": "deleted"}


@router.get("/system")
def system_info(admin: dict = Depends(require_admin)):
    """Get detailed system status."""
    status = get_system_status()
    conn = get_connection()
    users = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
    signals = conn.execute("SELECT COUNT(*) as c FROM signals").fetchone()["c"]
    conn.close()
    status["stats"] = {"total_users": users, "total_signals": signals}
    return status


@router.get("/performance")
def admin_performance(admin: dict = Depends(require_admin)):
    """Get full performance metrics (admin)."""
    return get_performance_from_db()


@router.get("/signals")
def admin_signals(limit: int = 50, admin: dict = Depends(require_admin)):
    """Get all signals (admin view)."""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM signals ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return {"signals": [dict(r) for r in rows], "total": len(rows)}


@router.put("/config/trading-style")
def update_global_config(data: dict, admin: dict = Depends(require_admin)):
    """Update global trading style configuration."""
    # Write to .env or a config JSON
    import json
    import os

    config_path = r"D:\Punokawan V2\web\data\admin_config.json"
    os.makedirs(os.path.dirname(config_path), exist_ok=True)

    with open(config_path, "w") as f:
        json.dump(data, f, indent=2)

    return {"status": "saved", "config": data}


@router.get("/config/trading-style")
def get_global_config(admin: dict = Depends(require_admin)):
    """Get current global trading style configuration."""
    import json
    import os

    config_path = r"D:\Punokawan V2\web\data\admin_config.json"
    if os.path.exists(config_path):
        with open(config_path) as f:
            return json.load(f)
    return {"style": "SCALPING", "note": "Using .env defaults"}
