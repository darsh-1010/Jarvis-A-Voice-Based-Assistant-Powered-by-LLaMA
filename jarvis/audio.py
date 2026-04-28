"""Audio management for Jarvis (STT and TTS)."""
import speech_recognition as sr
import pyttsx3
from jarvis.config import SPEECH_RATE, SPEECH_VOLUME
from jarvis.logger import logger

class AudioManager:
    """Manages speech recognition and text-to-speech."""

    def __init__(self):
        """Initialize STT and TTS engines."""
        self.recognizer = sr.Recognizer()
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', SPEECH_RATE)
        self.engine.setProperty('volume', SPEECH_VOLUME)

        # Set default voice (usually index 0)
        voices = self.engine.getProperty('voices')
        if voices:
            self.engine.setProperty('voice', voices[0].id)

    def speak(self, text: str) -> None:
        """
        Convert text to speech.

        Args:
            text: The string to speak aloud.
        """
        if not text:
            return

        logger.info(f"[SPEAK] Message: {text}")
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as exc:
            logger.error(f"[TTS_ERROR] Message: {exc}")

    def listen(self, prompt: str = "Listening...") -> str:
        """
        Listen for audio input and convert to text.

        Args:
            prompt: Text to display/speak before listening.

        Returns:
            str: The recognized text in lowercase, or empty string on failure.
        """
        with sr.Microphone() as source:
            if prompt:
                logger.info(f"[LISTEN] Status: {prompt}")

            # Adjust for ambient noise
            self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            audio = self.recognizer.listen(source)

            try:
                command = self.recognizer.recognize_google(audio)
                logger.info(f"[RECOGNIZED] Text: {command}")
                return command.lower()
            except sr.UnknownValueError:
                logger.debug("[STT_RETRY] Message: Could not understand audio")
            except sr.RequestError as exc:
                logger.error(f"[STT_ERROR] Message: API request failed: {exc}")
            except Exception as exc:
                logger.error(f"[STT_FATAL] Message: {exc}")

        return ""
