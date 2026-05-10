# Copyright (c) 2024-2026 Darsh Shah
# Licensed under the Business Source License 1.1
"""Standardized logging configuration for Jarvis."""
import logging
import sys

def setup_logger(logger_name: str = "jarvis") -> logging.Logger:
    """
    Set up a logger with a specific format.

    Args:
        logger_name: Name of the logger

    Returns:
        logging.Logger: Configured logger instance
    """
    instance = logging.getLogger(logger_name)

    # Avoid duplicate handlers if the logger is already set up
    if not instance.handlers:
        instance.setLevel(logging.INFO)

        # Format: [ACTION] Key: value | Key: value
        formatter = logging.Formatter(
            '[%(levelname)s] Time: %(asctime)s | Module: %(name)s | Message: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Stream handler for console output
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        instance.addHandler(console_handler)

    return instance

# Create a default logger for the package
logger = setup_logger()

def log_action(action: str, tech: str, simple: str, level: int = logging.INFO) -> None:
    """
    Log an action with both technical and simple aspects.

    Args:
        action: The name of the action being performed
        tech: Technical details for developers
        simple: Simplified explanation for users
        level: Logging level (default: INFO)
    """
    message = f"Tech: {tech} | Simple: {simple}"
    logger.log(level, f"[{action}] {message}")

import functools
import time

def time_function(func):
    """Decorator to log the execution time of a function."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        log_action(
            "PERFORMANCE",
            f"Function {func.__name__} executed in {duration:.2f}s",
            f"Finished {func.__name__.replace('_', ' ')} logic.",
            level=logging.DEBUG
        )
        return result
    return wrapper
