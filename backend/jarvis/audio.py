# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
"""Manages speech recognition and text-to-speech asynchronously using offline models."""
import asyncio
import logging
import os
import tempfile
from typing import Optional

import numpy as np
import sounddevice as sd
import speech_recognition as sr
from faster_whisper import WhisperModel
from kokoro import KPipeline

from jarvis.config import config
from jarvis.logger import log_action


class AudioManager:
    """Manages speech recognition and text-to-speech asynchronously using offline models."""

    def __init__(self):
        """Initialize Whisper and Kokoro models."""
        log_action(
            "AUDIO_INIT_START",
            "Initializing offline audio models (Whisper + Kokoro)...",
            "I'm warming up my voice and hearing modules."
        )

        # Initialize Faster-Whisper (Optimized for CPU)
        # Using 'base.en' for balance between speed and accuracy
        try:
            self.stt_model = WhisperModel(
                "base.en",
                device="cpu",
                compute_type="int8"
            )
        except Exception as e:
            logging.error(f"Failed to load Whisper model: {e}")
            self.stt_model = None

        # Initialize Kokoro TTS Pipeline
        try:
            self.tts_pipeline = KPipeline(lang_code='a')  # 'a' for American English
        except Exception as e:
            logging.error(f"Failed to load Kokoro TTS: {e}")
            self.tts_pipeline = None

        self.recognizer = sr.Recognizer()
        log_action(
            "AUDIO_INIT_DONE",
            "AudioManager initialized with Faster-Whisper and Kokoro.",
            "I'm ready to listen and speak naturally."
        )

    async def speak(self, text: str) -> None:
        """
        Convert text to speech using Kokoro and play it.

        Args:
            text: The text string to convert to speech.
        """
        if not text or not self.tts_pipeline:
            return

        log_action("AUDIO_SPEAK", f"TTS start (chars={len(text)})", "I'm speaking my response to you.")
        
        try:
            # Kokoro generates audio in chunks (generator)
            generator = self.tts_pipeline(
                text, 
                voice='af_heart', # Human-sounding female voice
                speed=1, 
                split_pattern=r'\n+'
            )

            for _, _, audio in generator:
                if audio is not None:
                    # Play the audio chunk
                    sd.play(audio, 24000)
                    sd.wait() # Wait for playback to finish before next chunk
                    
        except Exception as exc:
            log_action(
                "AUDIO_TTS_FAIL",
                f"TTS Error: {exc}",
                "I had some trouble speaking naturally.",
                level=logging.ERROR
            )

    async def listen(self, prompt: str = "Listening...") -> str:
        """
        Listen for audio input asynchronously and transcribe using Whisper.

        Args:
            prompt: Text to display in logs while listening.

        Returns:
            str: The recognized text command.
        """
        return await asyncio.to_thread(self._run_stt, prompt)

    def _run_stt(self, prompt: str) -> str:
        """
        Capture audio from mic and transcribe with Faster-Whisper.

        Returns:
            str: Recognized text.
        """
        if not self.stt_model:
            return ""

        try:
            with sr.Microphone() as source:
                if prompt:
                    log_action("AUDIO_LISTEN", f"STT Active: {prompt}", "I'm listening for your command.")

                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                
                try:
                    audio_data = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                    
                    # Convert audio_data to numpy array for Whisper
                    # SpeechRecognition gives us bytes, Whisper needs float32
                    wav_data = audio_data.get_wav_data()
                    
                    # Save to a temporary file because faster-whisper works best with file paths or buffers
                    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_wav:
                        temp_wav.write(wav_data)
                        temp_path = temp_wav.name

                    try:
                        segments, _ = self.stt_model.transcribe(temp_path, beam_size=5)
                        command = " ".join([segment.text for segment in segments]).strip()
                    finally:
                        if os.path.exists(temp_path):
                            os.remove(temp_path)

                    if command:
                        log_action("AUDIO_RECOGNIZED", f"Text: '{command}'", f"I heard: '{command}'")
                        return command.lower()
                    
                except sr.WaitTimeoutError:
                    return ""
                except Exception as exc:
                    log_action(
                        "AUDIO_STT_FAIL",
                        f"STT Error: {exc}",
                        "I couldn't quite catch that.",
                        level=logging.ERROR
                    )
        except Exception as exc:
            log_action(
                "AUDIO_HARDWARE",
                f"Hardware error: {exc}",
                "I can't find a microphone to listen with.",
                level=logging.WARNING
            )

        return ""
