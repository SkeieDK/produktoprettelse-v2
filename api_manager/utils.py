from urllib.parse import quote
from pathlib import Path
from typing import Any
import json


def quote_url(url: str) -> str:
    return quote(url, safe=':/')


def safe_json_load(path: Path, default: Any = None) -> Any:
    try:
        if not path.exists():
            return default
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def safe_json_write(path: Path, data: Any) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False
