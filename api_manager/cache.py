import json
from pathlib import Path
from typing import Any, Optional
import logging


class CacheManager:
    def __init__(self, cache_dir: Path, logger: logging.Logger):
        self.cache_dir = cache_dir
        self.logger = logger
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def read_json(self, filename: str, default: Any = None) -> Optional[Any]:
        path = self.cache_dir / filename
        if not path.exists():
            return default
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to read cache file {path}: {e}")
            return default

    def write_json(self, filename: str, data: Any) -> bool:
        path = self.cache_dir / filename
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"Failed to write cache file {path}: {e}")
            return False

    def clear(self, filename: str) -> bool:
        path = self.cache_dir / filename
        if path.exists():
            try:
                path.unlink()
                return True
            except Exception as e:
                self.logger.error(f"Failed to clear cache file {path}: {e}")
                return False
        return False

    def exists(self, filename: str) -> bool:
        return (self.cache_dir / filename).exists()

    def file_info(self, filename: str) -> dict:
        """Get information about a cache file.
        
        Returns:
            Dict with exists, age_seconds (actual age), size_bytes, modified_timestamp
        """
        import time
        path = self.cache_dir / filename
        if path.exists():
            st = path.stat()
            return {
                "exists": True,
                "age_seconds": time.time() - st.st_mtime,  # Fixed: actual age, not timestamp
                "size_bytes": st.st_size,
                "modified_timestamp": st.st_mtime,  # Added: raw timestamp if needed
            }
        return {"exists": False}

    def get_file_age(self, filename: str) -> float:
        """Get the age of a cache file in seconds.
        
        Returns:
            Age in seconds, or float('inf') if file doesn't exist
        """
        info = self.file_info(filename)
        if info.get("exists"):
            return info["age_seconds"]
        return float('inf')
