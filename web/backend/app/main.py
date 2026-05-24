"""Punokawan V2 — Signal Sharing API.

FastAPI backend providing:
- JWT authentication (register, login, profile)
- Signal endpoints (latest, history, public)
- Performance metrics
- WebSocket real-time signal push
- System health monitoring
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .routers import admin_router, auth_router, signal_router
from .services.websocket_manager import ws_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    # Initialize database on startup
    from .core.database import init_db
    init_db()
    print(f"[API] {settings.APP_NAME} v{settings.VERSION} starting...")
    yield
    print("[API] Shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router.router)
app.include_router(signal_router.router)
app.include_router(admin_router.router)


# WebSocket endpoint
@app.websocket("/ws/signals")
async def ws_signals(ws: WebSocket):
    """Real-time signal push via WebSocket."""
    await ws_manager.connect(ws)
    try:
        while True:
            # Keep connection alive, receive pings
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        ws_manager.disconnect(ws)


@app.get("/")
def root():
    return {
        "name": settings.APP_NAME,
        "version": settings.VERSION,
        "status": "running",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
