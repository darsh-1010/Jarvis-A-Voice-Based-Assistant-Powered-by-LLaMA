"""Pydantic models for the Jarvis API."""
from typing import List, Optional
from pydantic import BaseModel

class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str
    provider: Optional[str] = None

class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str
    history: List[str]

class SystemStats(BaseModel):
    """Model for system statistics."""
    cpu_percent: float
    ram_percent: float
    disk_usage: float
    boot_time: str

class SettingsUpdate(BaseModel):
    """Model for updating system settings."""
    persona: Optional[str] = None
    tone: Optional[str] = None
    voice_id: Optional[int] = None
    speech_rate: Optional[int] = None
    sensitivity: Optional[str] = None
    language: Optional[str] = None
    dark_mode: Optional[bool] = None

