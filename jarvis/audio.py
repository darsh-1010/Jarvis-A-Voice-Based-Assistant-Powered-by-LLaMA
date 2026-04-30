"""Audio management for Jarvis (STT and TTS)."""
import asyncio
import speech_recognition as sr
import pyttsx3
from jarvis.config import config
from jarvis.logger import logger

class AudioManager:
    """Manages speech recognition and text-to-speech asynchronously."""

    def __init__(self):
        """Initialize the speech engine and recognizer."""
        self.recognizer = sr.Recognizer()
        self._loop = asyncio.get_event_loop()
        logger.info("[AUDIO_INIT] Manager initialized.")

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

        logger.info(f"[SPEAK] Message: {text}")
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
            logger.error(f"[TTS_ERROR] Message: {exc}")

    async def listen(self, prompt: str = "Listening...") -> str:
        """Listen for audio input asynchronously."""
        return await asyncio.to_thread(self._run_stt, prompt)

    def _run_stt(self, prompt: str) -> str:
        """Synchronous STT runner to be executed in a thread."""
        with sr.Microphone() as source:
            if prompt:
                logger.info(f"[LISTEN] Status: {prompt}")

            # Adjust for ambient noise
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                command = self.recognizer.recognize_google(audio)
                logger.info(f"[RECOGNIZED] Text: {command}")
                return command.lower()
            except sr.WaitTimeoutError:
                return ""
            except sr.UnknownValueError:
                logger.debug("[STT_RETRY] Message: Could not understand audio")
            except Exception as exc:
                logger.error(f"[STT_ERROR] Message: {exc}")

        return ""
