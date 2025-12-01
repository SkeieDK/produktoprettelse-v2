"""
Core utilities package for produktoprettelse-v2.

This package provides shared functionality used across the entire codebase:
- config: Configuration loading, API keys, path management
- errors: Custom exceptions and error handling decorators
- file_utils: Unified JSON I/O with atomic writes
- logging: Centralized logger factory
- product_utils: Common product/category extraction helpers
- schemas: Pydantic models for data validation (fail-fast)
"""

from .config import (
    load_config,
    get_api_key,
    get_project_root,
    AppConfig,
    PathsConfig,
    AIConfig,
    ChromeConfig,
    LoggingConfig,
)
from .errors import (
    AppError,
    APIError,
    ValidationError,
    ConfigurationError,
    handle_errors,
)
from .file_utils import (
    load_json,
    save_json,
    atomic_write_json,
)
from .logging import (
    get_logger,
    setup_logging,
    SafeStreamHandler,
)
from .product_utils import (
    extract_category_name,
    extract_product_number,
    round_price_to_nearest,
    extract_price_items,
)
from .schemas import (
    BaseProduct,
    ProcessedProduct,
    EnrichedProduct,
    CategorizedProduct,
    FinalProduct,
    PriceEntry,
    CategoryInfo,
    validate_product,
    validate_products,
    products_to_dicts,
)

__all__ = [
    # config
    "load_config",
    "get_api_key",
    "get_project_root",
    "AppConfig",
    "PathsConfig",
    "AIConfig",
    "ChromeConfig",
    "LoggingConfig",
    # errors
    "AppError",
    "APIError",
    "ValidationError",
    "ConfigurationError",
    "handle_errors",
    # file_utils
    "load_json",
    "save_json",
    "atomic_write_json",
    # logging
    "get_logger",
    "setup_logging",
    "SafeStreamHandler",
    # product_utils
    "extract_category_name",
    "extract_product_number",
    "round_price_to_nearest",
    "extract_price_items",
    # schemas
    "BaseProduct",
    "ProcessedProduct",
    "EnrichedProduct",
    "CategorizedProduct",
    "FinalProduct",
    "PriceEntry",
    "CategoryInfo",
    "validate_product",
    "validate_products",
    "products_to_dicts",
]
