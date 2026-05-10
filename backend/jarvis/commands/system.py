import asyncio
import logging
import os
import subprocess

import pyautogui
from pynput.keyboard import Key, Controller

from jarvis.commands.registry import registry
from jarvis.config import config
from jarvis.logger import log_action

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
        path = apps[app_name.lower()]
        log_action(
            "SYS_APP",
            f"Opening {app_name} | Path: {path}",
            f"I'm launching {app_name} for you."
        )
        subprocess.Popen(path)
        return True
    return False

@registry.register(name="open_source_file", description="Open the main project source directory.")
def open_source_file() -> None:
    """Open the main project source directory."""
    log_action(
        "SYS_FILE",
        f"Explorer: {config.source_file_path}",
        "I'm opening your project folder."
    )
    try:
        subprocess.Popen(f'explorer.exe "{config.source_file_path}"')
    except Exception as exc:
        log_action(
            "SYS_FILE_ERR",
            f"Error: {exc}",
            "I had trouble opening the folder.",
            level=logging.ERROR
        )

@registry.register(name="take_screenshot", description="Take a screenshot of the current screen.")
async def take_screenshot() -> str:
    """
    Take a screenshot after a short delay.

    Returns:
        str: Path to the saved screenshot file.
    """
    log_action(
        "SYS_SCREENSHOT",
        "PyAutoGUI trigger (3s delay)",
        "I'm taking a screenshot of your screen in 3 seconds."
    )
    await asyncio.sleep(3)
    screenshot = await asyncio.to_thread(pyautogui.screenshot)
    file_path = "screenshot.png"
    await asyncio.to_thread(screenshot.save, file_path)
    log_action(
        "SYS_SCREENSHOT_DONE",
        f"Path: {file_path}",
        "I've saved the screenshot to your project folder."
    )
    return file_path

@registry.register(name="volume_up", description="Increase the system volume.")
def volume_up() -> None:
    """Increase system volume."""
    log_action("SYS_VOLUME", "Vol+ (x5 pynput)", "I'm turning your volume up.")
    for _ in range(5):
        keyboard.press(Key.media_volume_up)
        keyboard.release(Key.media_volume_up)

@registry.register(name="volume_down", description="Decrease the system volume.")
def volume_down() -> None:
    """Decrease system volume."""
    log_action("SYS_VOLUME", "Vol- (x5 pynput)", "I'm turning your volume down.")
    for _ in range(5):
        keyboard.press(Key.media_volume_down)
        keyboard.release(Key.media_volume_down)

@registry.register(name="shutdown", description="Shutdown the computer (requires confirmation).")
def shutdown_system() -> None:
    """Shutdown the computer."""
    log_action(
        "SYS_POWER",
        "Shell: shutdown /s /t 60",
        "I'm shutting down the computer in 60 seconds.",
        level=logging.WARNING
    )
    os.system("shutdown /s /t 60") # 60s delay for safety

