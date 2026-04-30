"""FastAPI backend for Jarvis v2."""
import datetime
import psutil
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.models import ChatRequest, ChatResponse, SystemStats, SettingsUpdate
from jarvis.brain import BrainManager
from jarvis.commands import system, web, media
from jarvis.settings_manager import settings_manager
from jarvis.logger import logger


app = FastAPI(title="Jarvis AI API", version="2.0.0")

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this to your Vercel domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize global managers
brain = BrainManager()
camera = media.CameraManager()

@app.get("/")
async def root():
    """Root health check."""
    return {"status": "online", "assistant": "Jarvis", "version": "2.0.0"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint.
    Processes commands or passes to LLM.
    """
    cmd = request.message.lower()
    logger.info(f"[API_CHAT] Message: {cmd}")
    
    # Very basic command routing for the API
    # In a full version, we'd use the dispatcher from main.py
    if "time" in cmd:
        resp = f"The time is {datetime.datetime.now().strftime('%H:%M')}."
    elif "test internet speed" in cmd:
        resp = web.test_internet_speed()
    else:
        # Switch provider if requested
        if request.provider:
            global brain
            brain = BrainManager(request.provider)
        resp = brain.generate_response(cmd)
        
    return ChatResponse(response=resp, history=brain.history)

@app.get("/system/stats", response_model=SystemStats)
async def get_stats():
    """Get real-time system statistics."""
    import datetime
    return {
        "cpu_percent": psutil.cpu_percent(),
        "ram_percent": psutil.virtual_memory().percent,
        "disk_usage": psutil.disk_usage('/').percent,
        "boot_time": datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
    }

@app.post("/commands/volume/{direction}")
async def control_volume(direction: str):
    """Control system volume."""
    if direction == "up":
        system.volume_up()
    elif direction == "down":
        system.volume_down()
    else:
        raise HTTPException(status_code=400, detail="Invalid direction")
    return {"status": "success", "action": f"volume {direction}"}

@app.post("/commands/camera/{action}")
async def control_camera(action: str):
    """Control camera operations."""
    if action == "click":
        path = camera.take_photo()
        return {"status": "success", "file": path}
    raise HTTPException(status_code=400, detail="Invalid action")

@app.get("/settings")
async def get_settings():
    """Get all current system settings."""
    return settings_manager.settings

@app.post("/settings")
async def update_settings(update: SettingsUpdate):
    """Update system settings."""
    settings_manager.update(update.dict(exclude_unset=True))
    return {"status": "success", "settings": settings_manager.settings}

