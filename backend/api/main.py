# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
"""FastAPI backend for Jarvis v3 (Async Zenith)."""
import datetime
import logging
import os
import sys

import psutil
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Ensure the 'backend' directory is in the path so we can import 'jarvis' and 'api'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.models import ChatRequest, ChatResponse, SystemStats, SettingsUpdate
from jarvis.brain import BrainManager
from jarvis.commands import media, system, vision, web
from jarvis.commands.registry import registry
from jarvis.config import config
from jarvis.logger import log_action

app = FastAPI(title="Jarvis AI API", version="3.0.0")

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize global brain
brain = BrainManager()


@app.get("/")
async def root() -> dict:
    """
    Root health check.

    Returns:
        dict: Basic API status.
    """
    return {"status": "online", "assistant": "Jarvis", "version": "3.0.0"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Main chat endpoint.
    Uses the ToolRegistry for command matching and falling back to the Brain.

    Args:
        request: The user's chat message and preferences.

    Returns:
        ChatResponse: The assistant's response.
    """
    cmd = request.message.lower()
    log_action(
        "API_CHAT",
        f"POST /chat | Input: '{cmd}'",
        f"I'm processing your chat request: '{cmd}'"
    )

    try:
        # Check registry for direct tool matches
        tools = registry.list_tools()
        for tool in tools:
            if tool["name"].replace("_", " ") in cmd:
                log_action(
                    "API_TOOL",
                    f"Matched Tool: {tool['name']}",
                    f"I'm using the {tool['name']} module to fulfill your request."
                )
                result = await registry.invoke(tool["name"])
                return ChatResponse(response=str(result), history=[])

        # Fallback to Brain
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
        raise HTTPException(status_code=400, detail="Invalid direction")
    return {"status": "success", "action": f"volume {direction}"}


@app.get("/settings")
async def get_settings() -> dict:
    """
    Get current configuration.

    Returns:
        dict: The global configuration settings.
    """
    log_action("API_SETTINGS", "GET /settings", "I'm retrieving my configuration profile.")
    return config.dict()


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
    # Note: In V3.0, we use Pydantic Settings which are typically loaded from env.
    # For dynamic updates, we'd need a more complex state manager.
    return {"status": "success", "message": "Settings updated locally (simulated)"}


