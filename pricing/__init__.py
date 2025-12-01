"""
Pricing Package

This package handles all price and offer management functionality:
- offer_service: Core logic for creating/removing offers
- utils: Price building helpers (build_price_update, build_price_delete, etc.)
- cli/: Command-line tools for batch operations

The API Manager (api_manager/) handles the actual API calls,
while this package handles the business logic for price operations.

Usage:
    from pricing import prepare_offer_operations, execute_offer_action
    from pricing.utils import build_price_update, extract_price_items

    # Prepare operations without calling API
    ops, ctx, error = prepare_offer_operations(product, "create", 99.95)

    # Execute operations via API
    success, message, result = execute_offer_action(api, product, "create", 99.95)
"""

from .offer_service import (
    prepare_offer_operations,
    execute_offer_action,
    OFFER_CATEGORY_NUMBER,
)

from .utils import (
    build_price_update,
    build_price_delete,
    extract_price_items,
    extract_category_numbers,
    extract_language_id,
)

__all__ = [
    # offer_service
    "prepare_offer_operations",
    "execute_offer_action",
    "OFFER_CATEGORY_NUMBER",
    # utils
    "build_price_update",
    "build_price_delete",
    "extract_price_items",
    "extract_category_numbers",
    "extract_language_id",
]
