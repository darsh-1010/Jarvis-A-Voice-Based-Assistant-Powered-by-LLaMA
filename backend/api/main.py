# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
"""FastAPI backend for Jarvis v3 (Async Zenith)."""
import psutil
import sys
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Ensure the 'backend' directory is in the path so we can import 'jarvis' and 'api'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from api.models import ChatRequest, ChatResponse, SystemStats, SettingsUpdate
from jarvis.brain import BrainManager
from jarvis.commands.registry import registry
from jarvis.config import config
from jarvis.logger import logger, log_action

# Import commands to ensure they are registered
from jarvis.commands import system, web, media, vision

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
async def root():
    """Root health check."""
    return {"status": "online", "assistant": "Jarvis", "version": "3.0.0"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint.
    Uses the ToolRegistry for command matching and falling back to the Brain.
    """
    cmd = request.message.lower()
    log_action("API_CHAT", f"POST /chat | Input: '{cmd}'", f"I'm processing your chat request: '{cmd}'")
    
    try:
        # Check registry for direct tool matches
        tools = registry.list_tools()
        for tool in tools:
            if tool["name"].replace("_", " ") in cmd:
                log_action("API_TOOL", f"Matched Tool: {tool['name']}", f"I'm using the {tool['name']} module to fulfill your request.")
                result = await registry.invoke(tool["name"])
                return ChatResponse(response=str(result), history=[])

        # Fallback to Brain
        resp = await brain.generate_response(cmd)
        return ChatResponse(response=resp, history=[])
    except Exception as e:
        log_action("API_ERROR", f"Chat fail: {e}", "I had some trouble processing that message.", level=logging.ERROR)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/system/stats", response_model=SystemStats)
async def get_stats():
    """Get real-time system statistics."""
    import datetime
    log_action("API_STATS", "GET /system/stats", "I'm checking my system performance metrics.")
    return {
        "cpu_percent": psutil.cpu_percent(),
        "ram_percent": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage('/').percent,
        "boot_time": datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
    }

@app.post("/commands/volume/{direction}")
async def control_volume(direction: str):
    """Control system volume via registry."""
    log_action("API_VOLUME", f"POST /volume/{direction}", f"Adjusting system volume {direction}.")
    if direction == "up":
        await registry.invoke("volume_up")
    elif direction == "down":
        await registry.invoke("volume_down")
    else:
        raise HTTPException(status_code=400, detail="Invalid direction")
    return {"status": "success", "action": f"volume {direction}"}

@app.get("/settings")
async def get_settings():
    """Get current configuration."""
    log_action("API_SETTINGS", "GET /settings", "I'm retrieving my configuration profile.")
    return config.dict()

@app.post("/settings")
async def update_settings(update: SettingsUpdate):
    """Update system settings (Partial implementation)."""
    log_action("API_SETTINGS_UPDATE", f"POST /settings | Data: {update}", "I'm updating my assistant settings.")
    # Note: In V3.0, we use Pydantic Settings which are typically loaded from env.
    # For dynamic updates, we'd need a more complex state manager.
    return {"status": "success", "message": "Settings updated locally (simulated)"}


