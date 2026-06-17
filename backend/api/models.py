# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
"""Pydantic models for the Jarvis API."""

from typing import List, Optional

from pydantic import BaseModel, field_validator

from jarvis.persona import TONE_PRESETS


class ChatRequest(BaseModel):
    """Request model for the standard (blocking) chat endpoint."""

    message: str
    provider: Optional[str] = None


class StreamChatRequest(BaseModel):
    """Request model for the SSE streaming chat endpoint."""

    message: str


class ChatResponse(BaseModel):
    """Response model for the standard chat endpoint."""

    response: str
    history: List[str]


class SystemStats(BaseModel):
    """Model for real-time system statistics."""

    cpu_percent: float
    ram_percent: float
    disk_usage: float
    boot_time: str


class SettingsUpdate(BaseModel):
    """Model for updating system settings via POST /settings.

    'persona_custom' is the full system-prompt override (empty = use tone preset).
    'tone' must be one of the recognised preset IDs.
    """

    persona_custom: Optional[str] = None
    tone: Optional[str] = None
    voice_id: Optional[int] = None
    speech_rate: Optional[int] = None
    sensitivity: Optional[str] = None
    language: Optional[str] = None
    dark_mode: Optional[bool] = None

    @field_validator("tone")
    @classmethod
    def validate_tone(cls, value: Optional[str]) -> Optional[str]:
        """Reject unknown tone values early."""
        if value is not None and value not in TONE_PRESETS:
            raise ValueError(f"tone must be one of {TONE_PRESETS}")
        return value

    @field_validator("speech_rate")
    @classmethod
    def validate_speech_rate(cls, value: Optional[int]) -> Optional[int]:
        """Clamp speech rate to a safe range for pyttsx3 / Kokoro."""
        if value is not None and (value < 100 or value > 250):
            raise ValueError("speech_rate must be between 100 and 250")
        return value


class PersonaPreset(BaseModel):
    """A tone preset descriptor returned by GET /settings/personas."""

    id: str
    label: str
    description: str
