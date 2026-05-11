import asyncio
import logging
import os
import subprocess

import psutil
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
        with subprocess.Popen(path):
            pass
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
        with subprocess.Popen(f'explorer.exe "{config.source_file_path}"'):
            pass
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


# ──────────────────────────────────────────────
# System Health & Process Management
# ──────────────────────────────────────────────

@registry.register(
    name="get_system_health",
    description="Report current CPU, RAM, disk usage, and battery status.",
)
def get_system_health() -> str:
    """
    Collect key system metrics via psutil and return a spoken summary.

    Returns:
        Spoken-ready string with CPU, RAM, disk, and battery info.
    """
    log_action("SYS_HEALTH", "psutil metrics poll", "Checking system health.")
    cpu_pct = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    battery = psutil.sensors_battery()

    battery_str = "no battery detected"
    if battery:
        status = "charging" if battery.power_plugged else "discharging"
        battery_str = f"{battery.percent:.0f}% and {status}"

    return (
        f"System health report: CPU is at {cpu_pct}%, "
        f"RAM usage is {ram.percent}% with {ram.available // (1024 ** 2)} MB free, "
        f"disk usage is {disk.percent}%, "
        f"and battery is {battery_str}."
    )


@registry.register(
    name="list_processes",
    description="List the top CPU-consuming processes currently running.",
)
def list_processes(top_n: int = 5) -> str:
    """
    Return the top N processes sorted by CPU usage.

    Args:
        top_n: Number of processes to report (default 5).

    Returns:
        Spoken-ready string listing process names and CPU%.
    """
    log_action("SYS_PROCS", f"Top {top_n} processes by CPU", "Listing top processes.")

    proc_list = []
    for proc in psutil.process_iter(["name", "cpu_percent"]):
        try:
            proc_list.append((proc.info["name"], proc.info["cpu_percent"]))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    # Sort descending and take the top N
    proc_list.sort(key=lambda item: item[1], reverse=True)
    top = proc_list[:top_n]

    if not top:
        return "I couldn't retrieve the process list, sir."

    descriptions = [f"{name} at {cpu:.1f}%" for name, cpu in top]
    return f"The top {top_n} processes by CPU are: {', '.join(descriptions)}."


@registry.register(
    name="kill_process",
    description="Terminate a running process by name (e.g. 'kill Chrome').",
)
def kill_process(process_name: str) -> str:
    """
    Find and terminate all processes matching the given name.

    Args:
        process_name: Partial or full process name (case-insensitive).

    Returns:
        Spoken confirmation or error message.
    """
    process_name_lower = process_name.lower()
    log_action("SYS_KILL", f"Target: {process_name}", f"Attempting to kill '{process_name}'.")

    killed_count = 0
    for proc in psutil.process_iter(["name", "pid"]):
        try:
            if process_name_lower in proc.info["name"].lower():
                proc.kill()
                killed_count += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied) as exc:
            log_action(
                "SYS_KILL_SKIP",
                f"PID {proc.pid} inaccessible: {exc}",
                "Skipped inaccessible process.",
                level=logging.WARNING,
            )

    if killed_count == 0:
        return f"No processes matching '{process_name}' were found, sir."
    return f"Terminated {killed_count} process{'es' if killed_count > 1 else ''} matching '{process_name}', sir."
