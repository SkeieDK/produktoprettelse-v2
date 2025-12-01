"""
Unified logging utilities for produktoprettelse-v2.

Consolidates logging setup from:
- api_manager/logger.py (create_logger)
- scripts/utils.py (setup_logging, SafeStreamHandler)

Provides:
- get_logger: Get or create a named logger with file + console handlers
- setup_logging: Configure root logger for scripts
- SafeStreamHandler: Console handler that handles encoding errors gracefully
"""

import sys
import logging
from pathlib import Path
from typing import Optional


class SafeStream:
    """
    Safe stream wrapper that handles encoding errors gracefully.

    Prevents UnicodeEncodeError when printing non-ASCII characters
    to terminals that don't support them (e.g., Windows cmd.exe).
    """

    def __init__(self):
        self.encoding = "utf-8"

    def write(self, msg: str) -> None:
        if not msg or sys.__stdout__ is None:
            return
        try:
            sys.__stdout__.write(msg)
        except UnicodeEncodeError:
            try:
                safe_msg = msg.encode("utf-8", errors="replace").decode(
                    sys.__stdout__.encoding or "utf-8", errors="replace"
                )
                sys.__stdout__.write(safe_msg)
            except Exception:
                try:
                    safe_msg = msg.encode("ascii", errors="replace").decode("ascii")
                    sys.__stdout__.write(safe_msg)
                except Exception:
                    pass

    def flush(self) -> None:
        if sys.__stdout__ is None:
            return
        try:
            sys.__stdout__.flush()
        except Exception:
            pass

    def isatty(self) -> bool:
        if sys.__stdout__ is None:
            return False
        return sys.__stdout__.isatty() if hasattr(sys.__stdout__, "isatty") else False


class SafeStreamHandler(logging.StreamHandler):
    """
    Custom logging handler that prevents encoding errors on console output.

    Uses SafeStream to handle non-ASCII characters gracefully.
    """

    def __init__(self):
        super().__init__(SafeStream())

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self.stream.write(msg)
            self.stream.write("\n")
            self.stream.flush()
        except Exception:
            self.handleError(record)


# Cache for loggers to avoid duplicate handlers
_logger_cache: dict = {}


def get_logger(
    name: str,
    log_dir: Optional[Path] = None,
    level: int = logging.INFO,
    log_to_file: bool = True,
    log_to_console: bool = True,
    use_safe_console: bool = True,
) -> logging.Logger:
    """
    Get or create a named logger with file and/or console handlers.

    This is the primary logging function for the codebase. It consolidates
    the functionality from api_manager/logger.py and scripts/utils.py.

    Args:
        name: Logger name (typically module or script name)
        log_dir: Directory for log files. If None, file logging is disabled.
        level: Logging level (default: INFO)
        log_to_file: Whether to log to file (default: True)
        log_to_console: Whether to log to console (default: True)
        use_safe_console: Use SafeStreamHandler for console (handles encoding)

    Returns:
        Configured logger instance

    Example:
        logger = get_logger("step_1_sanitize", log_dir=Path("logs"))
        logger.info("Processing started")
    """
    # Return cached logger if already configured
    cache_key = f"{name}_{log_dir}_{level}_{log_to_file}_{log_to_console}"
    if cache_key in _logger_cache:
        return _logger_cache[cache_key]

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Clear existing handlers to avoid duplicates
    if logger.handlers:
        logger.handlers.clear()

    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler
    if log_to_file and log_dir:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"{name.lower().replace('.', '_')}.log"

        file_handler = logging.FileHandler(log_file, encoding="utf-8", mode="a")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        logger.addHandler(file_handler)

    # Console handler
    if log_to_console:
        if use_safe_console:
            console_handler = SafeStreamHandler()
        else:
            console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)
        logger.addHandler(console_handler)

    # Prevent propagation to root logger
    logger.propagate = False

    _logger_cache[cache_key] = logger
    return logger


def setup_logging(
    log_dir: Path,
    script_name: str,
    level: int = logging.INFO,
) -> logging.Logger:
    """
    Configure the root logger for a script.

    This is a convenience function for scripts that want simple logging setup.
    It configures both file and console output.

    Args:
        log_dir: Directory for log files
        script_name: Name of the script (used for log filename)
        level: Logging level (default: INFO)

    Returns:
        Configured root logger

    Example:
        logger = setup_logging(Path("logs"), "sanitize")
        logger.info("Script started")
    """
    return get_logger(
        name=script_name,
        log_dir=log_dir,
        level=level,
        log_to_file=True,
        log_to_console=True,
        use_safe_console=True,
    )


def clear_logger_cache() -> None:
    """Clear the logger cache. Useful for testing."""
    global _logger_cache
    _logger_cache = {}
