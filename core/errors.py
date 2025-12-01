"""
Centralized error handling for produktoprettelse-v2.

Provides:
- Custom exception hierarchy
- @handle_errors decorator for consistent error handling
- Error logging integration
"""

import functools
import logging
from typing import Callable, TypeVar, Any, Optional

T = TypeVar("T")


class AppError(Exception):
    """Base exception for all application errors."""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class APIError(AppError):
    """Exception for API-related errors (Dandomain, OpenAI, etc.)."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        endpoint: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        super().__init__(message, details)
        self.status_code = status_code
        self.endpoint = endpoint

    def __str__(self) -> str:
        parts = [self.message]
        if self.status_code:
            parts.append(f"Status: {self.status_code}")
        if self.endpoint:
            parts.append(f"Endpoint: {self.endpoint}")
        if self.details:
            parts.append(f"Details: {self.details}")
        return " | ".join(parts)


class ValidationError(AppError):
    """Exception for data validation errors (Pydantic, schema mismatches)."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Any = None,
        details: Optional[dict] = None,
    ):
        super().__init__(message, details)
        self.field = field
        self.value = value

    def __str__(self) -> str:
        parts = [self.message]
        if self.field:
            parts.append(f"Field: {self.field}")
        if self.value is not None:
            parts.append(f"Value: {repr(self.value)[:100]}")
        if self.details:
            parts.append(f"Details: {self.details}")
        return " | ".join(parts)


class ConfigurationError(AppError):
    """Exception for configuration errors (missing keys, invalid values)."""

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        super().__init__(message, details)
        self.config_key = config_key

    def __str__(self) -> str:
        parts = [self.message]
        if self.config_key:
            parts.append(f"Config key: {self.config_key}")
        if self.details:
            parts.append(f"Details: {self.details}")
        return " | ".join(parts)


class FileOperationError(AppError):
    """Exception for file I/O errors."""

    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        operation: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        super().__init__(message, details)
        self.file_path = file_path
        self.operation = operation

    def __str__(self) -> str:
        parts = [self.message]
        if self.file_path:
            parts.append(f"File: {self.file_path}")
        if self.operation:
            parts.append(f"Operation: {self.operation}")
        if self.details:
            parts.append(f"Details: {self.details}")
        return " | ".join(parts)


def handle_errors(
    logger: Optional[logging.Logger] = None,
    reraise: bool = True,
    default_return: Any = None,
    error_message: Optional[str] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for consistent error handling across the codebase.

    Args:
        logger: Logger instance for error logging. If None, uses module logger.
        reraise: If True, re-raises AppError exceptions. If False, returns default_return.
        default_return: Value to return if reraise=False and an error occurs.
        error_message: Custom error message prefix.

    Usage:
        @handle_errors(logger=my_logger)
        def my_function():
            ...

        @handle_errors(reraise=False, default_return=[])
        def my_function_with_fallback():
            ...
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            _logger = logger or logging.getLogger(func.__module__)
            try:
                return func(*args, **kwargs)
            except AppError:
                # Already an application error, just log and optionally reraise
                _logger.error(f"{error_message or func.__name__} failed: {str(args[0]) if args else 'Unknown error'}")
                if reraise:
                    raise
                return default_return
            except Exception as e:
                # Unexpected error - wrap in AppError
                msg = f"{error_message or func.__name__} encountered unexpected error: {e}"
                _logger.exception(msg)
                if reraise:
                    raise AppError(msg, details={"original_error": str(e)}) from e
                return default_return

        return wrapper

    return decorator
