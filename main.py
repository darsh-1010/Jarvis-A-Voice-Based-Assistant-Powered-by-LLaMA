"""Main entry point for Jarvis AI Assistant."""
import datetime
import sys
from jarvis.audio import AudioManager
from jarvis.brain import BrainManager
from jarvis.config import WAKE_WORD
from jarvis.logger import logger
from jarvis.commands import system, media, web

class Jarvis:
    """The Jarvis AI Assistant controller."""

    def __init__(self):
        """Initialize all managers."""
        self.audio = AudioManager()
        self.brain = BrainManager()
        self.camera = media.CameraManager()
        self.is_running = True

    def greet(self) -> None:
        """Greet the user based on the time of day."""
        hour = datetime.datetime.now().hour
        if 0 <= hour < 12:
            greeting = "Good Morning, sir."
        elif 12 <= hour < 18:
            greeting = "Good Afternoon, sir."
        else:
            greeting = "Good Evening, sir."
        self.audio.speak(greeting)
        self.audio.speak("I am Jarvis. How can I help you today?")

    def _handle_social_commands(self, command: str) -> bool:
        """Handle conversational and social commands."""
        handled = True
        if "how are you" in command:
            self.audio.speak("I'm fine, thank you for asking!")
        elif "thank you" in command:
            self.audio.speak("You're very welcome, sir.")
        elif "time" in command:
            now = datetime.datetime.now().strftime("%H:%M")
            self.audio.speak(f"The time is {now}.")
        else:
            handled = False
        return handled

    def _handle_system_commands(self, command: str) -> tuple[bool, bool]:
        """
        Handle system-related commands.
        Returns: (handled, continue_listening)
        """
        handled, cont = True, True
        if any(app in command for app in ["notepad", "calculator", "command prompt", "cmd"]):
            for app in ["notepad", "calculator", "command prompt", "cmd"]:
                if app in command:
                    if system.open_app(app):
                        self.audio.speak(f"Opening {app}.")
                    break
        elif "open source file" in command:
            system.open_source_file()
            self.audio.speak("Opening source file.")
        elif "take screenshot" in command:
            self.audio.speak("Taking screenshot in three seconds.")
            system.take_screenshot()
            self.audio.speak("Screenshot taken and saved.")
        elif "volume up" in command:
            self.audio.speak("Turning volume up.")
            system.volume_up()
        elif "volume down" in command:
            self.audio.speak("Turning volume down.")
            system.volume_down()
        elif "shutdown the system" in command:
            self.audio.speak("Shutting down the system. Goodbye, sir.")
            system.shutdown_system()
            cont = False
        else:
            handled = False
        return handled, cont

    def _handle_media_commands(self, command: str) -> bool:
        """Handle media-related commands."""
        handled = True
        if "open camera" in command:
            self.audio.speak("Opening camera feed. Press Q to close.")
            self.camera.open()
        elif "click photo" in command:
            self.audio.speak("Taking a photo in five seconds.")
            self.camera.take_photo()
            self.audio.speak("Photo captured.")
        elif "play song" in command:
            song = command.replace("play song", "").replace("play", "").strip()
            self.audio.speak(f"Searching for {song} on Spotify.")
            media.open_spotify(song)
        elif "tired" in command:
            self.audio.speak("Playing some music to lighten the mood.")
            media.play_random_music()
        else:
            handled = False
        return handled

    def _handle_web_commands(self, command: str) -> bool:
        """Handle web-related commands."""
        handled = True
        if "search google" in command or "search for" in command:
            query = command.replace("search google", "").replace("search for", "").replace("on google", "").strip()
            self.audio.speak(f"Searching Google for {query}.")
            web.search_google(query)
        elif "search youtube" in command:
            query = command.replace("search youtube", "").strip()
            self.audio.speak(f"Searching YouTube for {query}.")
            web.search_youtube(query)
        elif "test internet speed" in command:
            self.audio.speak("Testing your internet speed. Please wait.")
            result = web.test_internet_speed()
            self.audio.speak(result)
        elif "news" in command:
            self.audio.speak("Fetching the latest news headlines.")
            headlines = web.fetch_latest_news()
            if headlines:
                for idx, title in enumerate(headlines, 1):
                    self.audio.speak(f"News {idx}: {title}")
            else:
                self.audio.speak("I couldn't fetch the news right now.")
        else:
            handled = False
        return handled

    def handle_command(self, command: str) -> bool:
        """Process a single voice command with self-correction logic."""
        cont = True
        if not command:
            return True

        # Small Change: Command Aliases
        aliases = {
            "ss": "take screenshot",
            "calc": "open calculator",
            "notes": "open notepad",
            "speed": "test internet speed"
        }
        for alias, target in aliases.items():
            if command.lower() == alias:
                command = target
                logger.info(f"[COMMAND_ALIAS] Resolved '{alias}' to '{target}'")

        try:
            if self._handle_social_commands(command):
                pass
            elif "sleep" in command:
                self.audio.speak("Going to sleep. Say my name to wake me up.")
                cont = False
            elif "terminate" in command:
                self.audio.speak("Shutting down. Have a great day!")
                self.is_running = False
                cont = False
            else:
                handled_sys, cont_sys = self._handle_system_commands(command)
                if handled_sys:
                    cont = cont_sys
                elif not (self._handle_media_commands(command) or self._handle_web_commands(command)):
                    response = self.brain.generate_response(command)
                    self.audio.speak(response)
        except Exception as e:
            # Pillar 5.1: Self-Correcting Code Agent Logic
            logger.error(f"[COMMAND_FAILURE] Error: {e}")
            self.audio.speak("Something went wrong, sir. Let me analyze the issue.")
            analysis = self.brain.analyze_error(command, str(e))
            self.audio.speak(analysis)
            
        return cont

    def run(self) -> None:
        """Main loop of the assistant."""
        logger.info("[STARTUP] Jarvis is now active.")
        while self.is_running:
            text = self.audio.listen("Waiting for wake word...")
            if WAKE_WORD in text:
                self.greet()
                while True:
                    cmd = self.audio.listen("Listening for command...")
                    if not cmd:
                        continue
                    if not self.handle_command(cmd):
                        break
        logger.info("[SHUTDOWN] Jarvis has exited.")

if __name__ == "__main__":
    assistant = Jarvis()
    try:
        assistant.run()
    except KeyboardInterrupt:
        logger.info("[EXIT] Manual interruption detected.")
        sys.exit(0)
