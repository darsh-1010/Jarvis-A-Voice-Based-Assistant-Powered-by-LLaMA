"""System-related commands for Jarvis."""
import os
import subprocess
import asyncio
import pyautogui
from pynput.keyboard import Key, Controller
from jarvis.config import config
from jarvis.logger import logger
from jarvis.commands.registry import registry

keyboard = Controller()

@registry.register(name="open_app", description="Launch a system application like notepad, calculator, or cmd.")
def open_app(app_name: str) -> bool:
    """Launch a system application."""
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

@registry.register(name="open_source_file", description="Open the main project source directory.")
def open_source_file() -> None:
    """Open the hardcoded source file path."""
    logger.info(f"[SYS_FILE] Action: Opening {config.source_file_path}")
    try:
        subprocess.Popen(f'explorer.exe "{config.source_file_path}"')
    except Exception as exc:
        logger.error(f"[SYS_FILE_ERROR] Message: {exc}")

@registry.register(name="take_screenshot", description="Take a screenshot of the current screen.")
async def take_screenshot() -> str:
    """Take a screenshot after a short delay."""
    logger.info("[SYS_SCREENSHOT] Action: Taking screenshot in 3s")
    await asyncio.sleep(3)
    screenshot = await asyncio.to_thread(pyautogui.screenshot)
    file_path = "screenshot.png"
    await asyncio.to_thread(screenshot.save, file_path)
    logger.info(f"[SYS_SCREENSHOT] Status: Saved to {file_path}")
    return file_path

@registry.register(name="volume_up", description="Increase the system volume.")
def volume_up() -> None:
    """Increase system volume."""
    logger.info("[SYS_VOLUME] Action: Volume Up")
    for _ in range(5):
        keyboard.press(Key.media_volume_up)
        keyboard.release(Key.media_volume_up)

@registry.register(name="volume_down", description="Decrease the system volume.")
def volume_down() -> None:
    """Decrease system volume."""
    logger.info("[SYS_VOLUME] Action: Volume Down")
    for _ in range(5):
        keyboard.press(Key.media_volume_down)
        keyboard.release(Key.media_volume_down)

@registry.register(name="shutdown", description="Shutdown the computer (requires confirmation).")
def shutdown_system() -> None:
    """Shutdown the computer."""
    logger.warning("[SYS_SHUTDOWN] Action: Shutting down system")
    os.system("shutdown /s /t 60") # 60s delay for safety

