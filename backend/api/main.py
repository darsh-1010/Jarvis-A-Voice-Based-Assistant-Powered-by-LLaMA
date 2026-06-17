# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
"""FastAPI backend for Jarvis v3 (Async Zenith)."""

import asyncio
import datetime
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

import psutil
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

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

from api.models import (
    ChatRequest,
    ChatResponse,
    PersonaPreset,
    StreamChatRequest,
    SystemStats,
    SettingsUpdate,
)
from jarvis.brain import BrainManager
from jarvis.commands import media, system, vision, web  # noqa: F401 — registers tools
from jarvis.commands.registry import registry
from jarvis.config import config
from jarvis.intent import IntentRouter
from jarvis.logger import log_action
from jarvis.memory.reflection import ReflectionEngine
from jarvis.memory.telemetry import TelemetryStore
from jarvis.security.guardrails import GuardrailEngine
from jarvis.settings_manager import settings_manager


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
    log_action(
        "API_STARTUP",
        "Initializing BrainManager and IntentRouter.",
        "Jarvis API starting up.",
    )
    app.state.brain = BrainManager()
    app.state.intent_router = IntentRouter(app.state.brain)

    # Wire the self-improvement loop into the API runtime.
    app.state.telemetry = TelemetryStore(config.telemetry_db_path)
    app.state.guardrail = GuardrailEngine(app.state.telemetry)
    app.state.reflection = ReflectionEngine(
        guardrail_engine=app.state.guardrail,
        telemetry_store=app.state.telemetry,
        backup_dir=config.optimizer_backup_dir,
    )
    app.state.reflection.set_brain(app.state.brain)
    app.state.brain.set_telemetry_store(app.state.telemetry)
    registry.set_telemetry(app.state.telemetry)
    registry.set_reflection_engine(app.state.reflection)

    # Apply any persisted settings from settings.json to the live config
    settings_manager.apply_to_config(config)

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
    docs_url="/docs"
    if os.getenv("JARVIS_ENV", "development") == "development"
    else None,
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
        f"I'm processing your chat request: '{cmd}'",
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
                f"I'm using the {intent.tool_name} module to fulfill your request.",
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
            level=logging.ERROR,
        )
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/system/stats", response_model=SystemStats)
async def get_stats() -> SystemStats:
    """
    Get real-time system statistics.

    Returns:
        SystemStats: Current CPU, RAM, and Disk usage.
    """
    log_action(
        "API_STATS", "GET /system/stats", "I'm checking my system performance metrics."
    )
    return SystemStats(
        cpu_percent=psutil.cpu_percent(),
        ram_percent=psutil.virtual_memory().percent,
        disk_usage=psutil.disk_usage("/").percent,
        boot_time=datetime.datetime.fromtimestamp(psutil.boot_time()).strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
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
    log_action(
        "API_VOLUME",
        f"POST /volume/{direction}",
        f"Adjusting system volume {direction}.",
    )
    if direction == "up":
        await registry.invoke("volume_up")
    elif direction == "down":
        await registry.invoke("volume_down")
    else:
        raise HTTPException(
            status_code=400, detail="Invalid direction. Use 'up' or 'down'."
        )
    return {"status": "success", "action": f"volume {direction}"}


@app.get("/settings")
async def get_settings() -> dict:
    """
    Get current configuration.

    Returns:
        dict: The global configuration settings.
    """
    log_action(
        "API_SETTINGS", "GET /settings", "I'm retrieving my configuration profile."
    )
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
        "I'm updating my assistant settings.",
    )
    update_data = update.model_dump(exclude_none=True)
    settings_manager.update(update_data)
    settings_manager.apply_to_config(config)
    return {"status": "success", "message": "Settings applied.", "applied": update_data}


# ──────────────────────────────────────────────
# Self-Improvement Memory Endpoints
# ──────────────────────────────────────────────


@app.get("/memory/stats")
async def get_memory_stats(request: Request) -> dict:
    """
    Return per-tool execution stats: total calls, failure count, avg latency.

    Returns:
        dict: Tool performance summary from the telemetry store.
    """
    log_action(
        "API_MEMORY_STATS", "GET /memory/stats", "Fetching tool performance stats."
    )
    brain: BrainManager = request.app.state.brain
    stats = await brain.get_performance_summary()
    return {"status": "ok", "data": stats}


@app.get("/memory/reflections")
async def get_reflections(request: Request) -> dict:
    """
    Return past self-reflection reports stored in ChromaDB.

    Returns:
        dict: List of reflection documents, most recent first.
    """
    log_action(
        "API_MEMORY_REFLECTIONS",
        "GET /memory/reflections",
        "Fetching self-reflection history.",
    )
    try:
        from jarvis.memory.knowledge import kb

        results = await asyncio.to_thread(
            kb.query,
            "self_reflection optimization improvement",
            5,
        )
        return {"status": "ok", "data": results}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/memory/patches")
async def get_patch_log(request: Request) -> dict:
    """
    Return the full autonomous code-patch audit log.

    Returns:
        dict: List of patch records with guardrail results and backup paths.
    """
    log_action("API_MEMORY_PATCHES", "GET /memory/patches", "Fetching patch audit log.")
    telemetry: TelemetryStore = request.app.state.telemetry
    patches = await telemetry.get_all_patches()
    return {"status": "ok", "data": patches}


@app.post("/memory/patches/{patch_id}/rollback")
async def rollback_patch(patch_id: int, request: Request) -> dict:
    """
    Restore the pre-patch backup for the given patch ID.

    Args:
        patch_id: The integer ID from the patch_log table.

    Returns:
        dict: Success status and the restored file path.
    """
    log_action(
        "API_MEMORY_ROLLBACK",
        f"POST /memory/patches/{patch_id}/rollback",
        f"Rolling back patch ID {patch_id}.",
    )
    telemetry: TelemetryStore = request.app.state.telemetry
    backup_path = await telemetry.get_patch_backup_path(patch_id)
    if not backup_path:
        raise HTTPException(
            status_code=404, detail=f"No backup found for patch ID {patch_id}."
        )

    import shutil
    from pathlib import Path

    src = Path(backup_path)
    if not src.exists():
        raise HTTPException(
            status_code=404, detail=f"Backup file missing on disk: {backup_path}"
        )

    # Derive original target path from patch_log
    patches = await telemetry.get_all_patches()
    target_path: Optional[str] = None
    for entry in patches:
        if entry.get("id") == patch_id:
            target_path = entry.get("target_file")
            break

    if not target_path:
        raise HTTPException(
            status_code=404, detail="Original target file record not found."
        )

    try:
        await asyncio.to_thread(shutil.copy2, str(src), target_path)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Rollback failed: {exc}") from exc

    log_action(
        "API_ROLLBACK_DONE",
        f"Restored: {target_path} from {backup_path}",
        f"Rollback complete for patch {patch_id}.",
    )
    return {"status": "ok", "restored": target_path, "from_backup": backup_path}


# ──────────────────────────────────────────────
# Persona & Streaming Endpoints
# ──────────────────────────────────────────────


@app.get("/settings/personas", response_model=list[PersonaPreset])
async def get_persona_presets() -> list[PersonaPreset]:
    """
    Return the list of built-in tone presets for the Persona Studio UI.

    Returns:
        list[PersonaPreset]: Each preset's id, label, and description.
    """
    log_action("API_PERSONAS", "GET /settings/personas", "Returning tone preset list.")
    return [PersonaPreset(**p) for p in settings_manager.list_tone_presets()]


@app.post("/chat/stream")
async def chat_stream(request: Request, body: StreamChatRequest) -> StreamingResponse:
    """
    Streaming chat endpoint — yields LLM tokens via Server-Sent Events.

    The frontend opens this with ``fetch() + ReadableStream``.
    Each chunk is JSON-encoded and formatted as ``data: <json>\\n\\n``.
    A terminal ``data: [DONE]\\n\\n`` signals end of stream.

    Args:
        request: FastAPI request object.
        body:    The user's message.

    Returns:
        StreamingResponse: An SSE text/event-stream response.
    """
    cmd = body.message.strip()
    log_action(
        "API_STREAM", f"POST /chat/stream | Input: '{cmd}'", "Starting token stream."
    )

    brain: BrainManager = request.app.state.brain
    intent_router: IntentRouter = request.app.state.intent_router

    async def _event_generator() -> AsyncGenerator[str, None]:
        """Yield SSE-formatted token chunks from the LLM stream."""
        try:
            tools = registry.list_tools()
            intent = await intent_router.classify(cmd, tools)

            if intent.tool_name:
                # Tool matched — invoke it and yield the full result as one chunk
                result = await registry.invoke(intent.tool_name, **intent.params)
                yield f"data: {json.dumps(str(result))}\n\n"
            else:
                # No tool — stream from brain token by token
                async for token in brain.generate_response_stream(cmd):
                    yield f"data: {json.dumps(token)}\n\n"

        except Exception as exc:
            log_action(
                "API_STREAM_ERROR",
                f"Stream error: {exc}",
                "Streaming encountered an error.",
                level=logging.ERROR,
            )
            yield f"data: {json.dumps('[ERROR] ' + str(exc))}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering if behind a proxy
            "Connection": "keep-alive",
        },
    )
