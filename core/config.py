"""
Centralized configuration management for produktoprettelse-v2.

Consolidates configuration loading from:
- scripts/utils.py (load_config)
- scripts/3.5_categorize.py (get_api_key)
- scripts/4_generate_ai.py (get_api_key)
- Various inline config loading patterns

Provides:
- load_config: Load and validate config.yaml
- get_api_key: Get API key from .env, environment, or config
- Dataclass-based configuration with type safety
"""

import os
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv

from .errors import ConfigurationError

logger = logging.getLogger(__name__)

# Project root detection
_PROJECT_ROOT: Optional[Path] = None


def get_project_root() -> Path:
    """
    Get the project root directory.

    The project root is detected by looking for config.yaml or .git folder.
    Result is cached for performance.

    Returns:
        Path to project root

    Raises:
        ConfigurationError: If project root cannot be determined
    """
    global _PROJECT_ROOT

    if _PROJECT_ROOT is not None:
        return _PROJECT_ROOT

    # Start from this file's location and walk up
    current = Path(__file__).resolve().parent

    for _ in range(10):  # Max 10 levels up
        if (current / "config.yaml").exists() or (current / ".git").exists():
            _PROJECT_ROOT = current
            return _PROJECT_ROOT
        parent = current.parent
        if parent == current:
            break
        current = parent

    raise ConfigurationError(
        "Could not determine project root. Ensure config.yaml or .git exists."
    )


@dataclass
class PathsConfig:
    """Configuration for file paths."""

    input_dir: Path = field(default_factory=lambda: Path("data/input"))
    output_dir: Path = field(default_factory=lambda: Path("data/output"))
    cache_dir: Path = field(default_factory=lambda: Path("data/cache"))
    logs_dir: Path = field(default_factory=lambda: Path("logs"))
    images_output: Path = field(default_factory=lambda: Path("data/output/images"))
    thumbnails_output: Path = field(
        default_factory=lambda: Path("data/output/images/thumbnails")
    )
    products_cache: Path = field(
        default_factory=lambda: Path("cache/products_cache.json")
    )
    images_cache: Path = field(
        default_factory=lambda: Path("data/cache/original_images")
    )
    downloads_cache: Path = field(
        default_factory=lambda: Path("data/cache/downloads")
    )
    original_images_dir: Optional[Path] = None
    external_images_dir: Optional[Path] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any], project_root: Path) -> "PathsConfig":
        """Create PathsConfig from dictionary, resolving relative paths."""
        config = cls()

        for key, value in data.items():
            if hasattr(config, key) and value:
                path = Path(value)
                # Make relative paths absolute
                if not path.is_absolute():
                    path = project_root / path
                setattr(config, key, path)

        return config


@dataclass
class AIConfig:
    """Configuration for AI/OpenAI settings."""

    api_key: str = ""
    provider: str = "openai"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AIConfig":
        """Create AIConfig from dictionary."""
        return cls(
            api_key=data.get("api_key", ""),
            provider=data.get("provider", "openai"),
        )


@dataclass
class ChromeConfig:
    """Configuration for Chrome/Selenium settings."""

    binary_path: str = ""
    headless: bool = True
    retry_without_headless: bool = True
    timeout_seconds: int = 30

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChromeConfig":
        """Create ChromeConfig from dictionary."""
        return cls(
            binary_path=data.get("binary_path", ""),
            headless=data.get("headless", True),
            retry_without_headless=data.get("retry_without_headless", True),
            timeout_seconds=data.get("timeout_seconds", 30),
        )


@dataclass
class LoggingConfig:
    """Configuration for logging settings."""

    level: str = "INFO"
    max_bytes: int = 10485760  # 10MB
    backup_count: int = 3

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LoggingConfig":
        """Create LoggingConfig from dictionary."""
        return cls(
            level=data.get("level", "INFO"),
            max_bytes=data.get("max_bytes", 10485760),
            backup_count=data.get("backup_count", 3),
        )


@dataclass
class OfferConfig:
    """Configuration for offer/tilbud settings."""

    category_number: str = "20400000000000"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OfferConfig":
        """Create OfferConfig from dictionary."""
        return cls(
            category_number=data.get("category_number", "20400000000000"),
        )


@dataclass
class AppConfig:
    """Main application configuration container."""

    paths: PathsConfig = field(default_factory=PathsConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    chrome: ChromeConfig = field(default_factory=ChromeConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    offer: OfferConfig = field(default_factory=OfferConfig)
    _raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], project_root: Path) -> "AppConfig":
        """Create AppConfig from dictionary."""
        return cls(
            paths=PathsConfig.from_dict(data.get("paths", {}), project_root),
            ai=AIConfig.from_dict(data.get("ai", {})),
            chrome=ChromeConfig.from_dict(data.get("chrome", {})),
            logging=LoggingConfig.from_dict(data.get("logging", {})),
            offer=OfferConfig.from_dict(data.get("offer", {})),
            _raw=data,
        )

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the raw config dictionary."""
        return self._raw.get(key, default)


# Cached config instance
_config_cache: Dict[str, AppConfig] = {}


def load_config(
    config_path: Optional[Path] = None,
    use_cache: bool = True,
) -> AppConfig:
    """
    Load configuration from config.yaml.

    Args:
        config_path: Path to config file. If None, uses project_root/config.yaml
        use_cache: Whether to cache and reuse config (default: True)

    Returns:
        AppConfig instance with validated configuration

    Example:
        config = load_config()
        print(config.paths.output_dir)
        print(config.ai.provider)
    """
    project_root = get_project_root()

    if config_path is None:
        config_path = project_root / "config.yaml"

    cache_key = str(config_path)
    if use_cache and cache_key in _config_cache:
        return _config_cache[cache_key]

    if not config_path.exists():
        logger.warning(f"Config file not found: {config_path}, using defaults")
        config = AppConfig()
        if use_cache:
            _config_cache[cache_key] = config
        return config

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(f) or {}
    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {e}")
        raise ConfigurationError(
            f"Failed to load configuration: {e}",
            config_key=str(config_path),
        ) from e

    config = AppConfig.from_dict(raw_config, project_root)

    if use_cache:
        _config_cache[cache_key] = config

    return config


def get_api_key(
    key_name: str = "OPENAI_API_KEY",
    config: Optional[AppConfig] = None,
    required: bool = True,
) -> Optional[str]:
    """
    Get an API key from environment variables or config.

    Search order:
    1. .env file (loaded automatically)
    2. Environment variables (OPENAI_API_KEY, AI_API_KEY)
    3. config.yaml ai.api_key

    Args:
        key_name: Primary environment variable name to check
        config: AppConfig instance (loaded if not provided)
        required: If True, raises error when key not found

    Returns:
        API key string, or None if not found and required=False

    Raises:
        ConfigurationError: If required=True and no key found

    Example:
        api_key = get_api_key()  # Gets OPENAI_API_KEY
        api_key = get_api_key("DANDOMAIN_API_KEY", required=False)
    """
    # Load .env file
    project_root = get_project_root()
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logger.debug(f"Loaded .env from {env_path}")

    # Try primary key name
    api_key = os.environ.get(key_name)
    if api_key:
        logger.debug(f"Found API key in environment: {key_name}")
        return api_key

    # Try alternative key names for OpenAI
    if key_name == "OPENAI_API_KEY":
        api_key = os.environ.get("AI_API_KEY")
        if api_key:
            logger.debug("Found API key in environment: AI_API_KEY")
            return api_key

    # Try config file
    if config is None:
        config = load_config()

    if config.ai.api_key:
        logger.debug("Found API key in config.yaml")
        return config.ai.api_key

    # Not found
    if required:
        raise ConfigurationError(
            f"API key not found. Set {key_name} in .env file, environment, or config.yaml",
            config_key=key_name,
        )

    logger.warning(f"API key not found for {key_name}")
    return None


def clear_config_cache() -> None:
    """Clear the configuration cache. Useful for testing."""
    global _config_cache
    _config_cache = {}
