from pathlib import Path
import logging
from typing import Optional


class BaseAPI:
    def __init__(self, http_client, logger: logging.Logger, cache_dir: Optional[Path] = None):
        self.http = http_client
        self.logger = logger
        self.cache_dir = Path(cache_dir) if cache_dir else None
