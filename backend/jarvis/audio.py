# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
import asyncio
import speech_recognition as sr
import pyttsx3
import logging
from jarvis.config import config
from jarvis.logger import logger, log_action

class AudioManager:
    """Manages speech recognition and text-to-speech asynchronously."""

    def __init__(self):
        """Initialize the speech engine and recognizer."""
        self.recognizer = sr.Recognizer()
        self._loop = asyncio.get_event_loop()
        log_action(
            "AUDIO_INIT",
            "AudioManager initialized with Google Speech Recognition.",
            "Starting up my voice and hearing modules."
        )

    def _get_engine(self):
        """Initialize engine in a thread-safe manner if needed."""
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        vid = config.voice_id
        rate = config.speech_rate
        
        if voices:
            target_vid = vid if len(voices) > vid else 0
            engine.setProperty('voice', voices[target_vid].id)
            
        engine.setProperty('rate', rate)
        engine.setProperty('volume', config.speech_volume)
        return engine

    async def speak(self, text: str) -> None:
        """Convert text to speech without blocking the event loop."""
        if not text:
            return

        log_action("AUDIO_SPEAK", f"TTS start (chars={len(text)})", "I'm speaking my response to you.")
        await asyncio.to_thread(self._run_tts, text)

    def _run_tts(self, text: str):
        """Synchronous TTS runner to be executed in a thread."""
        try:
            engine = self._get_engine()
            engine.say(text)
            engine.runAndWait()
            # Clean up engine to prevent COM errors on Windows
            del engine
        except Exception as exc:
            log_action("AUDIO_TTS_FAIL", f"TTS Error: {exc}", "I had some trouble speaking.", level=logging.ERROR)

    async def listen(self, prompt: str = "Listening...") -> str:
        """Listen for audio input asynchronously."""
        return await asyncio.to_thread(self._run_stt, prompt)

    def _run_stt(self, prompt: str) -> str:
        """Synchronous STT runner to be executed in a thread."""
        try:
            with sr.Microphone() as source:
                if prompt:
                    log_action("AUDIO_LISTEN", f"STT Active: {prompt}", "I'm listening for your command.")

                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                try:
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                    command = self.recognizer.recognize_google(audio)
                    log_action("AUDIO_RECOGNIZED", f"Text: '{command}'", f"I heard you say: '{command}'")
                    return command.lower()
                except sr.WaitTimeoutError:
                    return ""
                except sr.UnknownValueError:
                    # Don't log action for unknown value to avoid spamming
                    pass
                except Exception as exc:
                    log_action("AUDIO_STT_FAIL", f"STT Error: {exc}", "I couldn't quite catch that.", level=logging.ERROR)
        except (OSError, Exception) as exc:
            log_action("AUDIO_HARDWARE", f"Hardware error: {exc}", "I can't find a microphone to listen with.", level=logging.WARNING)
            return ""

        return ""
