"""
Price Utility Functions

Extracted from app/app.py - these functions build payloads for
Dandomain price API operations.

Functions:
- extract_price_items: Get price entries from product
- extract_category_numbers: Get category numbers from product
- extract_language_id: Get language ID from product settings
- build_price_update: Build payload for PUT/POST price operations
- build_price_delete: Build payload for DELETE price operations
"""

from typing import Any, Dict, List, Optional


# Sentinel value for retaining existing special offer price
_RETAIN_SPECIAL = object()


def extract_price_items(product: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract price entries from a product dictionary.

    Handles Dandomain API format where prices can be:
    - A dict with 'items' key
    - A direct list of price entries

    Args:
        product: Product dictionary from API

    Returns:
        List of price entry dictionaries
    """
    prices_raw = product.get("prices")
    if isinstance(prices_raw, dict):
        return list(prices_raw.get("items", []) or [])
    if isinstance(prices_raw, list):
        return list(prices_raw)
    return []


def extract_category_numbers(product: Dict[str, Any]) -> List[str]:
    """
    Extract category numbers from a product dictionary.

    Args:
        product: Product dictionary from API

    Returns:
        List of category number strings
    """
    categories_raw = product.get("categories")
    if isinstance(categories_raw, dict):
        items = categories_raw.get("items", []) or []
    elif isinstance(categories_raw, list):
        items = categories_raw
    else:
        items = []
    return [str(cat.get("number")) for cat in items if cat.get("number")]


def extract_language_id(product: Dict[str, Any], default: int = 26) -> int:
    """
    Extract language ID from product settings.

    Args:
        product: Product dictionary from API
        default: Default language ID (26 = Danish)

    Returns:
        Language ID integer
    """
    settings_raw = product.get("settings")
    if isinstance(settings_raw, dict):
        items = settings_raw.get("items", []) or []
    elif isinstance(settings_raw, list):
        items = settings_raw
    else:
        items = []
    if items:
        try:
            return int(items[0].get("languageId", default) or default)
        except (TypeError, ValueError):
            return default
    return default


def build_price_update(
    entry: Dict[str, Any],
    *,
    b2b_override: Optional[str] = None,
    special_offer: Any = _RETAIN_SPECIAL,
    include_identity: bool = True,
    special_offer_period: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Build a price update payload for PUT/POST operations.

    Args:
        entry: Original price entry from API
        b2b_override: Override b2bGroupId value (e.g., "-2" for standard, "1" for B2B)
        special_offer: Special offer price (None to clear, _RETAIN_SPECIAL to keep existing)
        include_identity: Include id/priceId for updates (True for PUT, False for POST)
        special_offer_period: Special offer period ID

    Returns:
        Payload dict ready for API request
    """
    payload: Dict[str, Any] = {}

    # Required fields
    payload["unitPrice"] = float(entry.get("unitPrice", 0.0) or 0.0)
    payload["currencyCode"] = entry.get("currencyCode", "DKK")

    # Quantity (minimum 1)
    quantity_raw = entry.get("quantity", 1)
    try:
        quantity_val = int(quantity_raw)
    except (TypeError, ValueError):
        quantity_val = 1
    payload["quantity"] = max(quantity_val, 1)

    # B2B group ID
    group_value = b2b_override if b2b_override is not None else entry.get("b2bGroupId")
    if group_value is not None:
        payload["b2bGroupId"] = str(group_value)

    # Special offer handling
    if special_offer is _RETAIN_SPECIAL:
        # Keep existing special offer if present
        existing_offer = entry.get("specialOfferPrice")
        existing_offer_val = float(existing_offer) if existing_offer is not None else 0.0
        if existing_offer_val > 0:
            payload["specialOfferPrice"] = existing_offer_val
            special_period_val = entry.get("specialOfferPeriodId")
            if special_period_val is not None:
                payload["specialOfferPeriodId"] = str(special_period_val)
    else:
        if special_offer is None:
            # Clear special offer
            payload["specialOfferPrice"] = None
            payload["specialOfferPeriodId"] = None
        else:
            # Set new special offer
            try:
                payload["specialOfferPrice"] = float(special_offer)
            except (TypeError, ValueError):
                payload["specialOfferPrice"] = special_offer
            special_period_val = special_offer_period
            if special_period_val is None:
                special_period_val = entry.get("specialOfferPeriodId")
            if special_period_val is not None:
                payload["specialOfferPeriodId"] = str(special_period_val)

    # Identity fields for updates
    if include_identity:
        price_id = entry.get("id") or entry.get("priceId")
        if price_id is not None:
            payload["id"] = str(price_id)

    # Period info
    period_info = entry.get("period")
    if isinstance(period_info, dict):
        period_id = period_info.get("id")
        if period_id is not None:
            payload["periodId"] = str(period_id)
    elif entry.get("periodId") is not None:
        payload["periodId"] = str(entry.get("periodId"))

    # Extra fields
    for extra_key in ("advance", "amount", "isoCode"):
        extra_value = entry.get(extra_key)
        if extra_value is not None:
            payload[extra_key] = extra_value

    return payload


def build_price_delete(entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a price delete payload for DELETE operations.

    Args:
        entry: Price entry to delete

    Returns:
        Payload dict ready for API DELETE request
    """
    payload: Dict[str, Any] = {
        "currencyCode": entry.get("currencyCode", "DKK"),
        "quantity": int(entry.get("quantity", 1) or 1),
    }

    # Unit price
    unit_price_raw = entry.get("unitPrice")
    if unit_price_raw is not None:
        try:
            payload["unitPrice"] = float(unit_price_raw)
        except (TypeError, ValueError):
            payload["unitPrice"] = unit_price_raw

    # B2B group
    group_val = entry.get("b2bGroupId")
    if group_val is not None:
        payload["b2bGroupId"] = str(group_val)

    # Price ID
    price_id = entry.get("id") or entry.get("priceId")
    if price_id is not None:
        payload["id"] = str(price_id)

    # Period info
    period_info = entry.get("period")
    if isinstance(period_info, dict):
        period_id = period_info.get("id")
        if period_id is not None:
            payload["periodId"] = str(period_id)
    elif entry.get("periodId") is not None:
        payload["periodId"] = str(entry.get("periodId"))

    # Special offer period
    special_period = entry.get("specialOfferPeriodId")
    if special_period is not None:
        payload["specialOfferPeriodId"] = str(special_period)

    # Special offer price
    special_price = entry.get("specialOfferPrice")
    if special_price is not None:
        try:
            payload["specialOfferPrice"] = float(special_price)
        except (TypeError, ValueError):
            payload["specialOfferPrice"] = special_price

    # Extra fields
    for extra_key in ("advance", "amount", "isoCode"):
        extra_value = entry.get(extra_key)
        if extra_value is not None:
            payload[extra_key] = extra_value

    return payload


# Re-export sentinel for external use
RETAIN_SPECIAL = _RETAIN_SPECIAL
