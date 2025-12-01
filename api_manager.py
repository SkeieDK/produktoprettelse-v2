"""
Compatibility wrapper for the modular `api_manager` package.

This file provides a thin compatibility layer to preserve the original top-level
imports (for example: `from api_manager import APIManager`) while encouraging
imports from the new package structure (e.g. `from api_manager.manager import APIManager`).

All heavy logic now lives under the `api_manager` package. Keep this wrapper
light-weight and avoid duplicating any implementation here.
"""
import warnings

from api_manager.manager import (
	APIManager,
	get_api_manager,
	get_products,
	get_categories,
	refresh_products,
	refresh_categories,
	get_cache_status,
)

warnings.warn(
	"The top-level `api_manager.py` is a compatibility wrapper. Prefer importing from the `api_manager` package and its submodules.",
	DeprecationWarning,
	stacklevel=2,
)

__all__ = [
	'APIManager',
	'get_api_manager',
	'get_products',
	'get_categories',
	'refresh_products',
	'refresh_categories',
	'get_cache_status',
]

 