"""System-related commands for Jarvis."""
import os
import subprocess
import time
import pyautogui
from pynput.keyboard import Key, Controller
from jarvis.config import SOURCE_FILE_PATH
from jarvis.logger import logger

keyboard = Controller()

def open_app(app_name: str) -> bool:
    """
    Launch a system application.

    Args:
        app_name: Name of the application (notepad, calculator, cmd).

    Returns:
        bool: True if successful, False otherwise.
    """
    apps = {
        "notepad": r"C:\Windows\System32\notepad.exe",
        "calculator": r"C:\Windows\System32\calc.exe",
        "command prompt": r"C:\Windows\System32\cmd.exe",
        "cmd": r"C:\Windows\System32\cmd.exe"
    }

    if app_name.lower() in apps:
        logger.info(f"[SYS_APP] Action: Opening {app_name}")
        subprocess.Popen(apps[app_name.lower()])
        return True
    return False

def open_source_file() -> None:
    """Open the hardcoded source file path."""
    logger.info(f"[SYS_FILE] Action: Opening {SOURCE_FILE_PATH}")
    try:
        subprocess.Popen(f'explorer.exe "{SOURCE_FILE_PATH}"')
    except Exception as exc:
        logger.error(f"[SYS_FILE_ERROR] Message: {exc}")

def take_screenshot() -> str:
    """
    Take a screenshot after a countdown.

    Returns:
        str: Path to the saved screenshot.
    """
    logger.info("[SYS_SCREENSHOT] Action: Taking screenshot in 3s")
    time.sleep(3)
    screenshot = pyautogui.screenshot()
    file_path = "screenshot.png"
    screenshot.save(file_path)
    logger.info(f"[SYS_SCREENSHOT] Status: Saved to {file_path}")
    return file_path

def volume_up() -> None:
    """Increase system volume."""
    logger.info("[SYS_VOLUME] Action: Volume Up")
    for _ in range(5):
        keyboard.press(Key.media_volume_up)
        keyboard.release(Key.media_volume_up)
        time.sleep(0.1)

def volume_down() -> None:
    """Decrease system volume."""
    logger.info("[SYS_VOLUME] Action: Volume Down")
    for _ in range(5):
        keyboard.press(Key.media_volume_down)
        keyboard.release(Key.media_volume_down)
        time.sleep(0.1)

def shutdown_system() -> None:
    """Shutdown the computer."""
    logger.warning("[SYS_SHUTDOWN] Action: Shutting down system")
    os.system("shutdown /s /t 1")
