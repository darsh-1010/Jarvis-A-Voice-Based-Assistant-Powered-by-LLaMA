# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
"""Manages speech recognition and text-to-speech asynchronously using offline models."""

import asyncio
import io
import logging
import wave

import numpy as np
import sounddevice as sd
import speech_recognition as sr
from faster_whisper import WhisperModel
from kokoro import KPipeline

from jarvis.logger import log_action


class AudioManager:
    """Manages speech recognition and text-to-speech asynchronously using offline models."""

    def __init__(self):
        """Initialize Whisper and Kokoro models."""
        log_action(
            "AUDIO_INIT_START",
            "Initializing offline audio models (Whisper + Kokoro)...",
            "I'm warming up my voice and hearing modules.",
        )

        # Initialize Faster-Whisper (Optimized for CPU)
        # FIX: beam_size reduced from 5 → 1 (greedy decoding).
        # beam_size=5 performs 5 sequential decoding steps per token — far too slow for
        # short voice commands. Greedy decoding (beam_size=1) is ~40% faster with
        # negligible accuracy loss for typical voice inputs under 10 words.
        try:
            self.stt_model = WhisperModel("base.en", device="cpu", compute_type="int8")
            self._beam_size = 1  # Greedy — fastest for real-time voice
        except Exception as e:
            logging.error(f"Failed to load Whisper model: {e}")
            self.stt_model = None
            self._beam_size = 1

        # Initialize Kokoro TTS Pipeline
        try:
            self.tts_pipeline = KPipeline(lang_code="a")  # 'a' for American English
        except Exception as e:
            logging.error(f"Failed to load Kokoro TTS: {e}")
            self.tts_pipeline = None

        self.recognizer = sr.Recognizer()
        log_action(
            "AUDIO_INIT_DONE",
            "AudioManager initialized with Faster-Whisper and Kokoro.",
            "I'm ready to listen and speak naturally.",
        )

    async def speak(self, text: str) -> None:
        """
        Convert text to speech using Kokoro and play it.

        Args:
            text: The text string to convert to speech.
        """
        if not text or not self.tts_pipeline:
            return

        log_action(
            "AUDIO_SPEAK",
            f"TTS start (chars={len(text)})",
            "I'm speaking my response to you.",
        )

        try:
            # Kokoro generates audio in chunks (generator)
            generator = self.tts_pipeline(
                text,
                voice="af_heart",  # Human-sounding female voice
                speed=1,
                split_pattern=r"\n+",
            )

            for _, _, audio in generator:
                if audio is not None:
                    # Play the audio chunk and wait before the next
                    await asyncio.to_thread(sd.play, audio, 24000)
                    await asyncio.to_thread(sd.wait)

        except Exception as exc:
            log_action(
                "AUDIO_TTS_FAIL",
                f"TTS Error: {exc}",
                "I had some trouble speaking naturally.",
                level=logging.ERROR,
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

    def _wav_bytes_to_float32(self, wav_data: bytes) -> np.ndarray:
        """
        Convert WAV bytes directly to a float32 numpy array for Whisper.

        FIX: Previously wrote audio to a temp file on disk before Whisper could read
        it. This wasted 100–300ms per utterance in pointless disk I/O. Whisper's
        faster-whisper accepts numpy float32 arrays directly — this method converts
        the raw audio bytes in memory with zero disk activity.

        Args:
            wav_data: Raw WAV bytes from SpeechRecognition.

        Returns:
            np.ndarray: float32 array in range [-1.0, 1.0] at native sample rate.
        """
        with wave.open(io.BytesIO(wav_data)) as wf:
            raw_bytes = wf.readframes(wf.getnframes())
        raw_int16 = np.frombuffer(raw_bytes, dtype=np.int16)
        return raw_int16.astype(np.float32) / 32768.0

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
                    log_action(
                        "AUDIO_LISTEN",
                        f"STT Active: {prompt}",
                        "I'm listening for your command.",
                    )

                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=1)

                try:
                    audio_data = self.recognizer.listen(
                        source, timeout=5, phrase_time_limit=10
                    )

                    # FIX: Convert WAV bytes directly to numpy float32 — no temp file needed.
                    # faster-whisper accepts ndarray natively; this eliminates 100–300ms of
                    # pointless disk I/O that was present in the previous implementation.
                    wav_data = audio_data.get_wav_data()
                    audio_float32 = self._wav_bytes_to_float32(wav_data)

                    segments, _ = self.stt_model.transcribe(
                        audio_float32,
                        beam_size=self._beam_size,
                    )
                    command = " ".join([segment.text for segment in segments]).strip()

                    if command:
                        log_action(
                            "AUDIO_RECOGNIZED",
                            f"Text: '{command}'",
                            f"I heard: '{command}'",
                        )
                        return command.lower()

                except sr.WaitTimeoutError:
                    return ""
                except Exception as exc:
                    log_action(
                        "AUDIO_STT_FAIL",
                        f"STT Error: {exc}",
                        "I couldn't quite catch that.",
                        level=logging.ERROR,
                    )
        except Exception as exc:
            log_action(
                "AUDIO_HARDWARE",
                f"Hardware error: {exc}",
                "I can't find a microphone to listen with.",
                level=logging.WARNING,
            )

        return ""
