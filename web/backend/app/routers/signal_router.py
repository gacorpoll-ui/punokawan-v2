"""Signal endpoints — latest, history, performance."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse

from ..core.config import settings
from ..routers.auth_router import get_current_user
from ..services.signal_bridge import (
    get_latest_signal_from_orchestrator,
    get_performance_from_db,
    get_system_status,
)
from ..services.websocket_manager import ws_manager

router = APIRouter(prefix="/api", tags=["signals"])


def _delay_signal(signal: dict, delay_seconds: int) -> dict:
    """Apply delay to signal for free users."""
    if delay_seconds > 0 and signal.get("created_at"):
        signal = dict(signal)
        signal["delayed"] = True
        signal["delay_seconds"] = delay_seconds
        # Hide exact entry while delayed
        if delay_seconds >= 60:
            signal["entry"] = round(signal.get("entry", 0) * 0.999, 2)
            signal["sl"] = round(signal.get("sl", 0) * 0.999, 2)
            signal["tp"] = round(signal.get("tp", 0) * 1.001, 2)
    return signal


@router.get("/signals/latest")
def latest_signal(user: dict = Depends(get_current_user)):
    """Get latest trading signal. Delayed for free users."""
    signal = get_latest_signal_from_orchestrator()

    if user["tier"] == "trial" or user["tier"] == "expired":
        signal = _delay_signal(signal, settings.FREE_SIGNAL_DELAY)

    return JSONResponse(signal)


@router.get("/signals/public")
def public_signal():
    """Public signal — always delayed, no auth required."""
    signal = get_latest_signal_from_orchestrator()
    return JSONResponse(_delay_signal(signal, 300))


@router.get("/signals/history")
def signal_history(
    user: dict = Depends(get_current_user),
    limit: int = Query(20, le=100),
    status: str = Query(""),
):
    """Get signal history. Full data for paid users, limited for trial."""
    from ..core.database import get_connection

    conn = get_connection()
    query = "SELECT * FROM signals WHERE 1=1"
    params = []
    if status:
        query += " AND status=?"
        params.append(status)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()

    signals = [dict(r) for r in rows]
    if user["tier"] in ("trial", "expired"):
        signals = signals[:5]  # Trial only sees last 5

    return JSONResponse({"signals": signals, "total": len(signals)})


@router.get("/performance")
def performance(user: dict = Depends(get_current_user)):
    """Get trading performance metrics."""
    perf = get_performance_from_db()
    return JSONResponse(perf)


@router.get("/system/status")
def system_status():
    """Get system health status — public."""
    return JSONResponse(get_system_status())


@router.post("/signals/webhook")
async def signal_webhook(data: dict):
    """Receive signal from orchestrator via webhook, broadcast to WebSocket clients."""
    await ws_manager.broadcast({
        "type": "signal",
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    # Also save to signals database
    from ..core.database import get_connection

    conn = get_connection()
    conn.execute(
        """INSERT INTO signals (direction, entry, sl, tp, lot_size, score, rr_ratio,
           confluence, tp_source, session, status, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            data.get("direction", ""),
            data.get("entry", 0),
            data.get("sl", 0),
            data.get("tp", 0),
            data.get("lot_size", 0.05),
            data.get("score", 0),
            data.get("rr_ratio", 0),
            data.get("confluence", ""),
            data.get("tp_source", ""),
            data.get("session", ""),
            "PENDING",
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    conn.close()

    return {"status": "ok", "broadcast_to": ws_manager.connection_count}
