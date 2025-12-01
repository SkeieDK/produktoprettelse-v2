"""
Unified file I/O utilities for produktoprettelse-v2.

Consolidates JSON file operations from:
- scripts/utils.py (atomic_write_json)
- api_manager/cache.py (read_json, write_json)
- Multiple inline json.load/dump calls across the codebase

Provides:
- load_json: Safe JSON loading with defaults and error handling
- save_json: JSON saving with optional atomic writes
- atomic_write_json: Write to temp file then rename (prevents corruption)
"""

import json
import tempfile
import shutil
import logging
from pathlib import Path
from typing import Any, Optional, Union

from .errors import FileOperationError

logger = logging.getLogger(__name__)


def load_json(
    path: Union[str, Path],
    default: Any = None,
    encoding: str = "utf-8",
    log_errors: bool = True,
) -> Any:
    """
    Safely load a JSON file with error handling.

    Args:
        path: Path to the JSON file
        default: Value to return if file doesn't exist or can't be parsed
        encoding: File encoding (default: utf-8)
        log_errors: Whether to log errors (default: True)

    Returns:
        Parsed JSON data, or default if loading fails

    Raises:
        FileOperationError: If log_errors=False and an error occurs

    Example:
        data = load_json("data/products.json", default=[])
        config = load_json(Path("config.yaml"), default={})
    """
    path = Path(path)

    if not path.exists():
        if log_errors:
            logger.debug(f"File not found, returning default: {path}")
        return default

    try:
        with open(path, "r", encoding=encoding) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        msg = f"Invalid JSON in file: {path}"
        if log_errors:
            logger.error(f"{msg} - {e}")
            return default
        raise FileOperationError(msg, file_path=str(path), operation="load") from e
    except Exception as e:
        msg = f"Failed to read JSON file: {path}"
        if log_errors:
            logger.error(f"{msg} - {e}")
            return default
        raise FileOperationError(msg, file_path=str(path), operation="load") from e


def save_json(
    path: Union[str, Path],
    data: Any,
    indent: int = 2,
    ensure_ascii: bool = False,
    encoding: str = "utf-8",
    atomic: bool = True,
    create_dirs: bool = True,
) -> bool:
    """
    Save data to a JSON file.

    Args:
        path: Path to the output file
        data: Data to serialize as JSON
        indent: JSON indentation (default: 2)
        ensure_ascii: If True, escape non-ASCII characters (default: False)
        encoding: File encoding (default: utf-8)
        atomic: If True, use atomic write (temp file + rename) to prevent corruption
        create_dirs: If True, create parent directories if they don't exist

    Returns:
        True on success, False on failure

    Example:
        save_json("data/output/products.json", products)
        save_json(output_path, data, atomic=False)  # For less critical files
    """
    path = Path(path)

    try:
        if create_dirs:
            path.parent.mkdir(parents=True, exist_ok=True)

        if atomic:
            atomic_write_json(data, path, indent=indent, ensure_ascii=ensure_ascii, encoding=encoding)
        else:
            with open(path, "w", encoding=encoding) as f:
                json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)

        return True
    except Exception as e:
        logger.error(f"Failed to write JSON file {path}: {e}")
        return False


def atomic_write_json(
    data: Any,
    output_path: Union[str, Path],
    indent: int = 2,
    ensure_ascii: bool = False,
    encoding: str = "utf-8",
) -> None:
    """
    Write JSON file atomically (write to temp, then rename).

    This prevents file corruption if the process is interrupted during write.
    The temp file is created in the same directory to ensure atomic move works.

    Args:
        data: Data to serialize as JSON
        output_path: Final path for the output file
        indent: JSON indentation (default: 2)
        ensure_ascii: If True, escape non-ASCII characters (default: False)
        encoding: File encoding (default: utf-8)

    Raises:
        FileOperationError: If write or move fails

    Example:
        atomic_write_json(products, "data/output/products.json")
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = None
    try:
        # Create temp file in the same directory for atomic move
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=output_path.parent,
            delete=False,
            encoding=encoding,
            suffix=".tmp",
        ) as tf:
            json.dump(data, tf, indent=indent, ensure_ascii=ensure_ascii)
            temp_path = Path(tf.name)

        # Atomic replace
        shutil.move(str(temp_path), str(output_path))

    except Exception as e:
        # Cleanup temp file if move fails
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
        raise FileOperationError(
            f"Failed to write JSON atomically: {e}",
            file_path=str(output_path),
            operation="atomic_write",
        ) from e


def file_exists(path: Union[str, Path]) -> bool:
    """Check if a file exists."""
    return Path(path).exists()


def get_file_age_seconds(path: Union[str, Path]) -> Optional[float]:
    """
    Get the age of a file in seconds.

    Returns:
        Age in seconds, or None if file doesn't exist
    """
    import time

    path = Path(path)
    if not path.exists():
        return None

    return time.time() - path.stat().st_mtime


def get_file_info(path: Union[str, Path]) -> dict:
    """
    Get information about a file.

    Returns:
        Dict with exists, age_seconds, size_bytes, modified_timestamp
    """
    import time

    path = Path(path)
    if not path.exists():
        return {"exists": False}

    st = path.stat()
    return {
        "exists": True,
        "age_seconds": time.time() - st.st_mtime,  # Fixed: actual age, not timestamp
        "size_bytes": st.st_size,
        "modified_timestamp": st.st_mtime,
    }
