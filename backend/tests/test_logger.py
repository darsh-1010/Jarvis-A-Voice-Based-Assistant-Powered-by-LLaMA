"""
Tests for jarvis/logger.py — setup_logger, log_action, time_function decorator.
"""
import logging
import time
import pytest
from unittest.mock import MagicMock, patch

from jarvis.logger import setup_logger, log_action, time_function, logger


class TestSetupLogger:
    """Tests for the setup_logger factory function."""

    def test_returns_logger_instance(self):
        """setup_logger should return a logging.Logger."""
        result = setup_logger("test_logger")
        assert isinstance(result, logging.Logger)

    def test_logger_has_handlers(self):
        """Logger should have at least one handler."""
        instance = setup_logger("test_with_handler")
        assert len(instance.handlers) > 0

    def test_no_duplicate_handlers(self):
        """Calling setup_logger twice with the same name should not add duplicate handlers."""
        setup_logger("unique_logger")
        first_count = len(logging.getLogger("unique_logger").handlers)
        setup_logger("unique_logger")
        second_count = len(logging.getLogger("unique_logger").handlers)
        assert first_count == second_count

    def test_logger_level_is_info(self):
        """Logger level should be set to INFO."""
        instance = setup_logger("info_level_test")
        assert instance.level == logging.INFO

    def test_default_logger_name(self):
        """Default logger name should be 'jarvis'."""
        instance = setup_logger()
        assert instance.name == "jarvis"


class TestLogAction:
    """Tests for the log_action helper function."""

    def test_log_action_info_level(self, caplog):
        """log_action should emit an INFO-level log by default."""
        with caplog.at_level(logging.INFO, logger="jarvis"):
            log_action("TEST_ACTION", "technical details", "simple explanation")
        assert "TEST_ACTION" in caplog.text
        assert "technical details" in caplog.text
        assert "simple explanation" in caplog.text

    def test_log_action_warning_level(self, caplog):
        """log_action should emit at the specified level."""
        with caplog.at_level(logging.WARNING, logger="jarvis"):
            log_action("WARN_ACTION", "tech", "simple", level=logging.WARNING)
        assert "WARN_ACTION" in caplog.text

    def test_log_action_error_level(self, caplog):
        """log_action at ERROR level should appear in caplog."""
        with caplog.at_level(logging.ERROR, logger="jarvis"):
            log_action("ERR_ACTION", "tech", "simple", level=logging.ERROR)
        assert "ERR_ACTION" in caplog.text

    def test_log_action_formats_message_correctly(self, caplog):
        """log_action message should include 'Tech:' and 'Simple:' labels."""
        with caplog.at_level(logging.INFO, logger="jarvis"):
            log_action("FORMAT_TEST", "tech info", "plain info")
        assert "Tech: tech info" in caplog.text
        assert "Simple: plain info" in caplog.text


class TestTimeFunctionDecorator:
    """Tests for the @time_function decorator."""

    def test_decorated_function_returns_correct_value(self):
        """Decorator should not alter the return value."""
        @time_function
        def add(a, b):
            return a + b

        result = add(2, 3)
        assert result == 5

    def test_decorated_function_preserves_name(self):
        """Decorator should preserve the original function's __name__."""
        @time_function
        def my_function():
            pass

        assert my_function.__name__ == "my_function"

    def test_decorator_logs_performance(self, caplog):
        """Decorator should log at DEBUG level after execution."""
        @time_function
        def quick_task():
            return "done"

        with caplog.at_level(logging.DEBUG, logger="jarvis"):
            quick_task()
        # PERFORMANCE should be logged at DEBUG level
        assert "quick_task" in caplog.text

    def test_decorated_function_passes_args(self):
        """Decorator should correctly forward positional and keyword args."""
        @time_function
        def greet(name, greeting="Hello"):
            return f"{greeting}, {name}!"

        result = greet("Jarvis", greeting="Welcome")
        assert result == "Welcome, Jarvis!"
