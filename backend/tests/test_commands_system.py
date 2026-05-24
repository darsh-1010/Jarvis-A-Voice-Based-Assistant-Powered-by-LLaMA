"""
Tests for jarvis/commands/system.py — system commands.

All OS-level side effects (subprocess, psutil, pynput, pyautogui) are mocked.
"""
import pytest
from unittest.mock import MagicMock, patch, call


class TestOpenApp:
    """Tests for the open_app command."""

    def test_open_known_app_returns_true(self, mocker):
        """open_app should return True for a known app."""
        mocker.patch("jarvis.commands.system.subprocess.Popen")
        from jarvis.commands.system import open_app
        result = open_app("notepad")
        assert result is True

    def test_open_app_case_insensitive(self, mocker):
        """open_app should match app names case-insensitively."""
        mocker.patch("jarvis.commands.system.subprocess.Popen")
        from jarvis.commands.system import open_app
        result = open_app("Notepad")
        assert result is True

    def test_open_unknown_app_returns_false(self, mocker):
        """open_app should return False for an unknown app."""
        from jarvis.commands.system import open_app
        result = open_app("photoshop")
        assert result is False

    def test_open_app_calculator(self, mocker):
        """open_app should handle 'calculator'."""
        mock_popen = mocker.patch("jarvis.commands.system.subprocess.Popen")
        from jarvis.commands.system import open_app
        result = open_app("calculator")
        assert result is True
        mock_popen.assert_called_once()

    def test_open_app_cmd(self, mocker):
        """open_app should handle 'cmd'."""
        mock_popen = mocker.patch("jarvis.commands.system.subprocess.Popen")
        from jarvis.commands.system import open_app
        result = open_app("cmd")
        assert result is True


class TestGetSystemHealth:
    """Tests for get_system_health command."""

    def test_returns_string(self, mocker):
        """get_system_health should return a string."""
        mock_battery = MagicMock()
        mock_battery.percent = 80
        mock_battery.power_plugged = True

        mocker.patch("jarvis.commands.system.psutil.cpu_percent", return_value=30.0)
        mocker.patch("jarvis.commands.system.psutil.virtual_memory",
                     return_value=MagicMock(percent=50.0, available=4 * 1024 ** 2))
        mocker.patch("jarvis.commands.system.psutil.disk_usage",
                     return_value=MagicMock(percent=70.0))
        mocker.patch("jarvis.commands.system.psutil.sensors_battery",
                     return_value=mock_battery)

        from jarvis.commands.system import get_system_health
        result = get_system_health()
        assert isinstance(result, str)

    def test_includes_cpu_info(self, mocker):
        """Health report should include CPU percentage."""
        mocker.patch("jarvis.commands.system.psutil.cpu_percent", return_value=42.0)
        mocker.patch("jarvis.commands.system.psutil.virtual_memory",
                     return_value=MagicMock(percent=50.0, available=0))
        mocker.patch("jarvis.commands.system.psutil.disk_usage",
                     return_value=MagicMock(percent=60.0))
        mocker.patch("jarvis.commands.system.psutil.sensors_battery", return_value=None)

        from jarvis.commands.system import get_system_health
        result = get_system_health()
        assert "42.0%" in result

    def test_handles_no_battery(self, mocker):
        """Health report should handle no battery gracefully."""
        mocker.patch("jarvis.commands.system.psutil.cpu_percent", return_value=10.0)
        mocker.patch("jarvis.commands.system.psutil.virtual_memory",
                     return_value=MagicMock(percent=40.0, available=0))
        mocker.patch("jarvis.commands.system.psutil.disk_usage",
                     return_value=MagicMock(percent=50.0))
        mocker.patch("jarvis.commands.system.psutil.sensors_battery", return_value=None)

        from jarvis.commands.system import get_system_health
        result = get_system_health()
        assert "no battery detected" in result

    def test_includes_charging_status(self, mocker):
        """Battery status should mention 'charging' when plugged in."""
        mock_battery = MagicMock(percent=90, power_plugged=True)
        mocker.patch("jarvis.commands.system.psutil.cpu_percent", return_value=5.0)
        mocker.patch("jarvis.commands.system.psutil.virtual_memory",
                     return_value=MagicMock(percent=30.0, available=0))
        mocker.patch("jarvis.commands.system.psutil.disk_usage",
                     return_value=MagicMock(percent=40.0))
        mocker.patch("jarvis.commands.system.psutil.sensors_battery",
                     return_value=mock_battery)

        from jarvis.commands.system import get_system_health
        result = get_system_health()
        assert "charging" in result


class TestListProcesses:
    """Tests for list_processes command."""

    def _make_proc(self, name, cpu):
        p = MagicMock()
        p.info = {"name": name, "cpu_percent": cpu}
        return p

    def test_returns_string(self, mocker):
        """list_processes should return a string."""
        procs = [self._make_proc("python.exe", 15.0), self._make_proc("chrome.exe", 5.0)]
        mocker.patch("jarvis.commands.system.psutil.process_iter", return_value=procs)
        from jarvis.commands.system import list_processes
        result = list_processes(top_n=2)
        assert isinstance(result, str)

    def test_lists_top_n_processes(self, mocker):
        """list_processes should limit results to top_n."""
        procs = [self._make_proc(f"proc{i}.exe", float(i)) for i in range(10)]
        mocker.patch("jarvis.commands.system.psutil.process_iter", return_value=procs)
        from jarvis.commands.system import list_processes
        result = list_processes(top_n=3)
        # Should only mention top 3
        assert "3" in result

    def test_handles_empty_process_list(self, mocker):
        """list_processes should return fallback when no processes are found."""
        mocker.patch("jarvis.commands.system.psutil.process_iter", return_value=[])
        from jarvis.commands.system import list_processes
        result = list_processes()
        assert "couldn't retrieve" in result.lower()


class TestKillProcess:
    """Tests for kill_process command."""

    def _make_proc(self, name, pid):
        p = MagicMock()
        p.info = {"name": name, "pid": pid}
        p.pid = pid
        p.kill = MagicMock()
        return p

    def test_kills_matching_process(self, mocker):
        """kill_process should call proc.kill() on matching processes."""
        chrome = self._make_proc("chrome.exe", 1234)
        notepad = self._make_proc("notepad.exe", 5678)
        mocker.patch("jarvis.commands.system.psutil.process_iter",
                     return_value=[chrome, notepad])
        from jarvis.commands.system import kill_process
        result = kill_process("chrome")
        chrome.kill.assert_called_once()
        notepad.kill.assert_not_called()
        assert "1" in result or "Terminated" in result

    def test_no_matching_process_returns_not_found(self, mocker):
        """kill_process should return 'not found' when no match exists."""
        notepad = self._make_proc("notepad.exe", 999)
        mocker.patch("jarvis.commands.system.psutil.process_iter", return_value=[notepad])
        from jarvis.commands.system import kill_process
        result = kill_process("photoshop")
        assert "not found" in result.lower() or "No processes" in result

    def test_kills_multiple_matching_processes(self, mocker):
        """kill_process should kill all matching processes."""
        p1 = self._make_proc("chrome.exe", 1)
        p2 = self._make_proc("chrome.exe", 2)
        mocker.patch("jarvis.commands.system.psutil.process_iter", return_value=[p1, p2])
        from jarvis.commands.system import kill_process
        result = kill_process("chrome")
        p1.kill.assert_called_once()
        p2.kill.assert_called_once()
        assert "2" in result


class TestVolumeControls:
    """Tests for volume_up and volume_down commands."""

    def test_volume_up_calls_keyboard(self, mocker):
        """volume_up should press volume up key 5 times."""
        mock_keyboard = mocker.patch("jarvis.commands.system.keyboard")
        from jarvis.commands.system import volume_up
        volume_up()
        assert mock_keyboard.press.call_count == 5
        assert mock_keyboard.release.call_count == 5

    def test_volume_down_calls_keyboard(self, mocker):
        """volume_down should press volume down key 5 times."""
        mock_keyboard = mocker.patch("jarvis.commands.system.keyboard")
        from jarvis.commands.system import volume_down
        volume_down()
        assert mock_keyboard.press.call_count == 5
        assert mock_keyboard.release.call_count == 5


class TestShutdown:
    """Tests for the shutdown command."""

    def test_shutdown_calls_os_system(self, mocker):
        """shutdown should call os.system with a shutdown command."""
        mock_os = mocker.patch("jarvis.commands.system.os.system")
        from jarvis.commands.system import shutdown_system
        shutdown_system()
        mock_os.assert_called_once()
        call_arg = mock_os.call_args[0][0]
        assert "shutdown" in call_arg.lower()


class TestTakeScreenshot:
    """Tests for the take_screenshot async command."""

    @pytest.mark.asyncio
    async def test_take_screenshot_returns_path(self, mocker):
        """take_screenshot should return a file path string."""
        mocker.patch("jarvis.commands.system.asyncio.sleep", return_value=None)
        mock_screenshot = MagicMock()
        mocker.patch("jarvis.commands.system.pyautogui.screenshot",
                     return_value=mock_screenshot)
        from jarvis.commands.system import take_screenshot
        result = await take_screenshot()
        assert isinstance(result, str)
        assert "screenshot" in result.lower()
