import sys
import os
import logging
import json
import yaml
import tempfile
import shutil
from pathlib import Path
from typing import Any, Dict, Union

# Safe stream for console output (handles encoding errors)
class SafeStream:
    def __init__(self):
        self.encoding = 'utf-8'
    
    def write(self, msg):
        if not msg or sys.__stdout__ is None:
            return
        try:
            sys.__stdout__.write(msg)
        except UnicodeEncodeError:
            try:
                safe_msg = msg.encode('utf-8', errors='replace').decode(sys.__stdout__.encoding or 'utf-8', errors='replace')
                sys.__stdout__.write(safe_msg)
            except Exception:
                try:
                    safe_msg = msg.encode('ascii', errors='replace').decode('ascii')
                    sys.__stdout__.write(safe_msg)
                except Exception:
                    pass
    
    def flush(self):
        if sys.__stdout__ is None:
            return
        try:
            sys.__stdout__.flush()
        except Exception:
            pass
    
    def isatty(self):
        if sys.__stdout__ is None:
            return False
        return sys.__stdout__.isatty() if hasattr(sys.__stdout__, 'isatty') else False

class SafeStreamHandler(logging.StreamHandler):
    """Custom logging handler that prevents encoding errors"""
    def emit(self, record):
        try:
            msg = self.format(record)
            self.stream.write(msg)
            self.stream.write('\n')
            self.stream.flush()
        except Exception:
            self.handleError(record)

def setup_logging(log_dir: Path, script_name: str) -> logging.Logger:
    """Configure logging to file and console"""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"{script_name}.log"
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler (UTF-8, no rotation for now)
    file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='a')
    file_handler.setFormatter(formatter)
    
    # Console handler with SafeStream
    console_handler = SafeStreamHandler(SafeStream())
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def load_config(config_path: Path) -> Dict[str, Any]:
    """Load config.yaml"""
    if not config_path.exists():
        logging.warning(f"Config file not found: {config_path}, using defaults")
        return {}
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def atomic_write_json(data: Any, output_path: Union[str, Path], indent: int = 2):
    """Write JSON file atomically (write to temp, then rename)"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create temp file in the same directory to ensure atomic move works across filesystems
    with tempfile.NamedTemporaryFile(mode='w', dir=output_path.parent, delete=False, encoding='utf-8') as tf:
        json.dump(data, tf, indent=indent, ensure_ascii=False)
        temp_path = Path(tf.name)
    
    try:
        # Atomic replace
        shutil.move(str(temp_path), str(output_path))
    except Exception as e:
        # Cleanup if move fails
        if temp_path.exists():
            temp_path.unlink()
        raise e
