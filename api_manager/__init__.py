"""
api_manager package - modularized API manager for Dandomain
This package contains HTTP client, ProductAPI, CategoryAPI, PriceAPI and manager composing them.

Public surface:
- APIManager class in manager.py
- create_api_manager(): Factory for testing with custom config
- get_api_manager(): Singleton accessor
- reset_api_manager(): Clear singleton for test isolation
- get_products/get_categories wrappers
"""
from .manager import (
    APIManager,
    create_api_manager,
    get_api_manager,
    reset_api_manager,
    get_products,
    get_categories,
    refresh_products,
    refresh_categories,
    get_cache_status,
)

__all__ = [
    "APIManager",
    "create_api_manager",
    "get_api_manager",
    "reset_api_manager",
    "get_products",
    "get_categories",
    "refresh_products",
    "refresh_categories",
    "get_cache_status",
]
