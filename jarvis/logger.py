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

import functools
import time

def time_function(func):
    """Decorator to log the execution time of a function."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        logger.info(f"[PERF] {func.__name__} took {duration:.2f}s")
        return result
    return wrapper
