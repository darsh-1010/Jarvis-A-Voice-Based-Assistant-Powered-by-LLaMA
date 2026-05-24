import asyncio
import logging
import pytest
from unittest.mock import MagicMock, patch
import speech_recognition as sr

from jarvis.audio import AudioManager

@pytest.fixture
def mock_whisper(mocker):
    return mocker.patch("jarvis.audio.WhisperModel")

@pytest.fixture
def mock_kokoro(mocker):
    return mocker.patch("jarvis.audio.KPipeline")

@pytest.fixture
def mock_sd(mocker):
    return mocker.patch("jarvis.audio.sd")

@pytest.fixture
def mock_sr_mic(mocker):
    return mocker.patch("jarvis.audio.sr.Microphone")

@pytest.fixture
def audio_manager(mock_whisper, mock_kokoro):
    return AudioManager()

@pytest.mark.asyncio
async def test_initialization_success(mock_whisper, mock_kokoro):
    manager = AudioManager()
    mock_whisper.assert_called_once_with("base.en", device="cpu", compute_type="int8")
    mock_kokoro.assert_called_once_with(lang_code='a')
    assert manager.stt_model is not None
    assert manager.tts_pipeline is not None
    assert isinstance(manager.recognizer, sr.Recognizer)

@pytest.mark.asyncio
async def test_initialization_whisper_failure(mocker, mock_kokoro):
    mocker.patch("jarvis.audio.WhisperModel", side_effect=Exception("Whisper load failed"))
    manager = AudioManager()
    assert manager.stt_model is None
    # TTS should still initialize
    mock_kokoro.assert_called_once()
    assert manager.tts_pipeline is not None

@pytest.mark.asyncio
async def test_speak_success(audio_manager, mock_sd, mocker):
    text_to_speak = "Hello World"
    
    # Mock the generator returned by Kokoro TTS pipeline
    def mock_generator(*args, **kwargs):
        # yields (graphemes, phonemes, audio)
        yield ("Hello", "h_e_l_o", b"fake_audio_chunk_1")
        yield ("World", "w_o_r_l_d", b"fake_audio_chunk_2")

    # Set the pipeline to return our fake generator
    audio_manager.tts_pipeline.return_value = mock_generator()
    
    await audio_manager.speak(text_to_speak)
    
    audio_manager.tts_pipeline.assert_called_once_with(
        text_to_speak,
        voice='af_heart',
        speed=1,
        split_pattern=r'\n+'
    )
    
    # Check if sounddevice was called to play the chunks
    assert mock_sd.play.call_count == 2
    assert mock_sd.wait.call_count == 2

@pytest.mark.asyncio
async def test_speak_empty_text(audio_manager, mock_sd):
    await audio_manager.speak("")
    audio_manager.tts_pipeline.assert_not_called()
    mock_sd.play.assert_not_called()

@pytest.mark.asyncio
async def test_speak_exception(audio_manager, mock_sd, caplog):
    audio_manager.tts_pipeline.side_effect = Exception("TTS generation failed")
    
    with caplog.at_level(logging.ERROR):
        await audio_manager.speak("Test")
        
    assert "TTS Error: TTS generation failed" in caplog.text
    mock_sd.play.assert_not_called()

@pytest.mark.asyncio
async def test_listen_success(audio_manager, mock_sr_mic, mocker):
    # Mock the microphone context manager
    mock_source = MagicMock()
    mock_sr_mic.return_value.__enter__.return_value = mock_source
    
    # Mock recognizer to return fake audio data
    mock_audio_data = MagicMock()
    mock_audio_data.get_wav_data.return_value = b"fake_wav_data"
    
    # We need to mock the recognizer instance inside the AudioManager
    mocker.patch.object(audio_manager.recognizer, "adjust_for_ambient_noise")
    mocker.patch.object(audio_manager.recognizer, "listen", return_value=mock_audio_data)
    
    # Mock Faster-Whisper transcribe to return fake segments
    mock_segment1 = MagicMock(text="turn on ")
    mock_segment2 = MagicMock(text="the lights")
    audio_manager.stt_model.transcribe.return_value = ([mock_segment1, mock_segment2], None)
    
    # We also need to mock tempfile so it doesn't try to write fake_wav_data to disk
    mock_tempfile = mocker.patch("jarvis.audio.tempfile.NamedTemporaryFile")
    mock_tempfile_instance = mock_tempfile.return_value.__enter__.return_value
    mock_tempfile_instance.name = "/fake/temp/file.wav"
    
    mock_os_remove = mocker.patch("jarvis.audio.os.remove")
    mock_os_path_exists = mocker.patch("jarvis.audio.os.path.exists", return_value=True)
    
    command = await audio_manager.listen("Test prompt")
    
    assert command == "turn on  the lights"
    audio_manager.recognizer.listen.assert_called_once_with(mock_source, timeout=5, phrase_time_limit=10)
    audio_manager.stt_model.transcribe.assert_called_once_with("/fake/temp/file.wav", beam_size=5)
    mock_os_remove.assert_called_once_with("/fake/temp/file.wav")

@pytest.mark.asyncio
async def test_listen_timeout(audio_manager, mock_sr_mic, mocker):
    mock_source = MagicMock()
    mock_sr_mic.return_value.__enter__.return_value = mock_source
    
    mocker.patch.object(audio_manager.recognizer, "adjust_for_ambient_noise")
    mocker.patch.object(audio_manager.recognizer, "listen", side_effect=sr.WaitTimeoutError("Timeout"))
    
    command = await audio_manager.listen("Test prompt")
    assert command == ""

@pytest.mark.asyncio
async def test_listen_hardware_error(audio_manager, mock_sr_mic, caplog):
    # Simulating a microphone not found exception
    mock_sr_mic.side_effect = OSError("No Default Input Device Available")
    
    with caplog.at_level(logging.WARNING):
        command = await audio_manager.listen("Test prompt")
        
    assert command == ""
    assert "Hardware error:" in caplog.text

@pytest.mark.asyncio
async def test_listen_stt_model_none():
    manager = AudioManager()
    manager.stt_model = None
    
    command = await manager.listen("Test")
    assert command == ""
