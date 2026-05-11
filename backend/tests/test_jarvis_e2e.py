import asyncio
import json
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import sys

# Comprehensive Mocks to prevent environment-specific failures
mock_cv2 = MagicMock()
mock_cv2.__version__ = '4.0.0'

mocks = {
    'pyttsx3': MagicMock(),
    'speech_recognition': MagicMock(),
    'cv2': mock_cv2,
    'spotipy': MagicMock(),
    'spotipy.oauth2': MagicMock(),
    'google.oauth2.credentials': MagicMock(),
    'google_auth_oauthlib.flow': MagicMock(),
    'google.auth.transport.requests': MagicMock(),
    'googleapiclient.discovery': MagicMock(),
    'yfinance': MagicMock(),
    'deep_translator': MagicMock(),
    'speedtest': MagicMock(),
    'pyautogui': MagicMock(),
    'psutil': MagicMock(),
    'pynput': MagicMock(),
    'pynput.keyboard': MagicMock(),
    'pynput.mouse': MagicMock(),
    'pywhatkit': MagicMock(),
}

for module_name, mock_obj in mocks.items():
    sys.modules[module_name] = mock_obj

# Import Jarvis components AFTER mocks are set
from jarvis.commands.registry import registry
import jarvis.commands.weather
import jarvis.commands.finance
import jarvis.commands.productivity
import jarvis.commands.calendar_cmd
import jarvis.commands.gmail_cmd
import jarvis.commands.web
import jarvis.commands.system
from jarvis.intent import IntentRouter, IntentResult
from cli_main import Jarvis, _enrich_result

class TestJarvisE2E(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        # Prevent actually loading config from file for tests if possible, 
        # but Jarvis() will load it. We'll mock the config instance if needed.
        self.assistant = Jarvis()
        self.assistant.audio.speak = AsyncMock()
        self.assistant.audio.listen = AsyncMock()
        self.assistant.brain.generate_response = AsyncMock(return_value="Mocked response")
        self.assistant.brain.get_active_provider = AsyncMock()
        
        self.mock_provider = AsyncMock()
        self.assistant.brain.get_active_provider.return_value = self.mock_provider

    async def simulate_command(self, text, mock_intent_json):
        self.mock_provider.generate.return_value = json.dumps(mock_intent_json)
        await self.assistant.handle_command(text)

    @patch('requests.get')
    async def test_weather_flow(self, mock_get):
        mock_get.return_value.json.return_value = {
            "cod": 200,
            "main": {"temp": 25.5, "feels_like": 27.0, "humidity": 60},
            "weather": [{"description": "clear sky"}]
        }
        await self.simulate_command(
            "What is the weather in Mumbai?",
            {"tool": "get_weather", "params": {"city": "Mumbai"}}
        )
        self.assistant.audio.speak.assert_called()
        last_speech = self.assistant.audio.speak.call_args[0][0]
        self.assertIn("Mumbai", last_speech)
        self.assertIn("25.5°C", last_speech)

    @patch('requests.get')
    async def test_finance_crypto_flow(self, mock_get):
        mock_get.return_value.json.return_value = {
            "bitcoin": {"usd": 65000, "inr": 5400000}
        }
        await self.simulate_command(
            "What is the price of Bitcoin?",
            {"tool": "get_crypto_price", "params": {"coin": "bitcoin"}}
        )
        self.assistant.audio.speak.assert_called()
        last_speech = self.assistant.audio.speak.call_args[0][0]
        self.assertIn("Bitcoin", last_speech)
        self.assertIn("$65,000.00", last_speech)

    async def test_pomodoro_flow(self):
        with patch('jarvis.commands.productivity.asyncio.create_task') as mock_task:
            await self.simulate_command(
                "Start a 10 minute pomodoro",
                {"tool": "start_pomodoro", "params": {"minutes": 10}}
            )
            self.assistant.audio.speak.assert_called_with(
                "Your 10-minute Pomodoro timer has started, sir. I'll notify you when it ends."
            )

    @patch('jarvis.commands.calendar_cmd._get_service')
    async def test_calendar_list_flow(self, mock_get_service):
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.events().list().execute.return_value = {
            "items": [
                {"summary": "Test Meeting", "start": {"dateTime": "2024-05-12T10:00:00Z"}}
            ]
        }
        await self.simulate_command(
            "Show my calendar",
            {"tool": "list_calendar_events", "params": {"max_results": 5}}
        )
        last_speech = self.assistant.audio.speak.call_args[0][0]
        self.assertIn("Test Meeting", last_speech)

    @patch('jarvis.commands.gmail_cmd._get_service')
    async def test_gmail_read_flow(self, mock_get_service):
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service
        mock_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "123"}]
        }
        mock_service.users().messages().get().execute.return_value = {
            "payload": {"headers": [{"name": "Subject", "value": "Hello from Jarvis"}]}
        }
        await self.simulate_command(
            "Read my emails",
            {"tool": "read_inbox", "params": {"max_results": 5}}
        )
        last_speech = self.assistant.audio.speak.call_args[0][0]
        self.assertIn("Hello from Jarvis", last_speech)

    async def test_conversational_fallback(self):
        self.mock_provider.generate.return_value = json.dumps({"tool": "null", "params": {}})
        self.assistant.brain.generate_response.return_value = "I am a helpful assistant."
        await self.assistant.handle_command("Who are you?")
        self.assistant.audio.speak.assert_called_with("I am a helpful assistant.")

if __name__ == "__main__":
    unittest.main()
