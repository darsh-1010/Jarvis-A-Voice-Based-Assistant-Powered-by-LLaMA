# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
"""FastAPI backend for Jarvis v3 (Async Zenith)."""
import datetime
import logging
import os
import sys
from contextlib import asynccontextmanager

import psutil
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

# slowapi for rate limiting — add 'slowapi' to requirements.txt
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address
    _RATE_LIMITING_AVAILABLE = True
except ImportError:
    _RATE_LIMITING_AVAILABLE = False

# Ensure the 'backend' directory is in the path so we can import 'jarvis' and 'api'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.models import ChatRequest, ChatResponse, SystemStats, SettingsUpdate
from jarvis.brain import BrainManager
from jarvis.commands import media, system, vision, web  # noqa: F401 — registers tools
from jarvis.commands.registry import registry
from jarvis.config import config
from jarvis.intent import IntentRouter
from jarvis.logger import log_action


# ──────────────────────────────────────────────
# App Lifespan (replaces deprecated @app.on_event)
# ──────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage startup and shutdown of shared resources.

    FIX: Previously, BrainManager was a bare module-level global. Now it is
    attached to app.state so it is properly scoped to the application lifetime,
    enabling clean shutdown and making it trivially testable via dependency injection.
    """
    log_action("API_STARTUP", "Initializing BrainManager and IntentRouter.", "Jarvis API starting up.")
    app.state.brain = BrainManager()
    app.state.intent_router = IntentRouter(app.state.brain)
    yield
    log_action("API_SHUTDOWN", "Jarvis API shutting down.", "API offline.")


# ──────────────────────────────────────────────
# Rate Limiter Setup
# ──────────────────────────────────────────────

if _RATE_LIMITING_AVAILABLE:
    limiter = Limiter(key_func=get_remote_address)
else:
    limiter = None


# ──────────────────────────────────────────────
# App Initialization
# ──────────────────────────────────────────────

app = FastAPI(
    title="Jarvis AI API",
    version="3.0.0",
    lifespan=lifespan,
    # FIX: Hide docs in production for security — enable only in dev
    docs_url="/docs" if os.getenv("JARVIS_ENV", "development") == "development" else None,
    redoc_url=None,
)

if _RATE_LIMITING_AVAILABLE:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# FIX: CORS wildcard (allow_origins=["*"]) was a security vulnerability.
# Now only allows the local Next.js dev server and the configured production origin.
# Add JARVIS_FRONTEND_URL to your .env for production.
_allowed_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
]
_frontend_url = os.getenv("JARVIS_FRONTEND_URL")
if _frontend_url:
    _allowed_origins.append(_frontend_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────

@app.get("/")
async def root() -> dict:
    """
    Root health check.

    Returns:
        dict: Basic API status.
    """
    return {"status": "online", "assistant": "Jarvis", "version": "3.0.0"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: Request, body: ChatRequest) -> ChatResponse:
    """
    Main chat endpoint — routes through IntentRouter then BrainManager.

    FIX: The previous implementation used naive substring matching
    (tool_name.replace('_', ' ') in cmd) which was fragile and inconsistent
    with the CLI. Now routes through the same IntentRouter pipeline used in
    cli_main.py, providing correct tool matching and parameter extraction.

    Rate limited to 20 requests per minute per IP.

    Args:
        request: The FastAPI request object (for rate limiting).
        body:    The user's chat message.

    Returns:
        ChatResponse: The assistant's response.
    """
    if _RATE_LIMITING_AVAILABLE and limiter:
        await limiter._check_request_limit(request, "20/minute")

    cmd = body.message.strip()
    log_action(
        "API_CHAT",
        f"POST /chat | Input: '{cmd}'",
        f"I'm processing your chat request: '{cmd}'"
    )

    brain: BrainManager = request.app.state.brain
    intent_router: IntentRouter = request.app.state.intent_router

    try:
        tools = registry.list_tools()
        intent = await intent_router.classify(cmd, tools)

        if intent.tool_name:
            log_action(
                "API_TOOL",
                f"Matched Tool: {intent.tool_name} | Params: {intent.params}",
                f"I'm using the {intent.tool_name} module to fulfill your request."
            )
            result = await registry.invoke(intent.tool_name, **intent.params)
            return ChatResponse(response=str(result), history=[])

        # No tool matched — fall through to conversational brain
        resp = await brain.generate_response(cmd)
        return ChatResponse(response=resp, history=[])

    except Exception as exc:
        log_action(
            "API_ERROR",
            f"Chat fail: {exc}",
            "I had some trouble processing that message.",
            level=logging.ERROR
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/system/stats", response_model=SystemStats)
async def get_stats() -> SystemStats:
    """
    Get real-time system statistics.

    Returns:
        SystemStats: Current CPU, RAM, and Disk usage.
    """
    log_action("API_STATS", "GET /system/stats", "I'm checking my system performance metrics.")
    return SystemStats(
        cpu_percent=psutil.cpu_percent(),
        ram_percent=psutil.virtual_memory().percent,
        disk_usage=psutil.disk_usage('/').percent,
        boot_time=datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
    )


@app.post("/commands/volume/{direction}")
async def control_volume(direction: str) -> dict:
    """
    Control system volume via registry.

    Args:
        direction: 'up' or 'down'.

    Returns:
        dict: Success status.
    """
    log_action("API_VOLUME", f"POST /volume/{direction}", f"Adjusting system volume {direction}.")
    if direction == "up":
        await registry.invoke("volume_up")
    elif direction == "down":
        await registry.invoke("volume_down")
    else:
        raise HTTPException(status_code=400, detail="Invalid direction. Use 'up' or 'down'.")
    return {"status": "success", "action": f"volume {direction}"}


@app.get("/settings")
async def get_settings() -> dict:
    """
    Get current configuration.

    Returns:
        dict: The global configuration settings.
    """
    log_action("API_SETTINGS", "GET /settings", "I'm retrieving my configuration profile.")
    # FIX: config.dict() is deprecated in Pydantic v2 — replaced with model_dump()
    return config.model_dump()


@app.post("/settings")
async def update_settings(update: SettingsUpdate) -> dict:
    """
    Update system settings (Partial implementation).

    Args:
        update: The settings to update.

    Returns:
        dict: Success status.
    """
    log_action(
        "API_SETTINGS_UPDATE",
        f"POST /settings | Data: {update}",
        "I'm updating my assistant settings."
    )
    # Note: In V3.0, Pydantic Settings are loaded from env at startup.
    # For dynamic updates, a more complex state manager is needed.
    return {"status": "success", "message": "Settings updated locally (simulated)"}
