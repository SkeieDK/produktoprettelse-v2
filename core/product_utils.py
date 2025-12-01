"""
Common product and category utility functions for produktoprettelse-v2.

Consolidates duplicated logic from:
- api_manager/category.py (extract category name)
- scripts/3.5_categorize.py (extract category name, multiple patterns)
- scripts/categorize_helpers.py (extract category name)
- csv_data_transformation/sanitering.py (round_price_to_nearest)
- scripts/4_generate_ai.py (extract product number)
- app/app.py (extract price items, product number parsing)

Provides single-source-of-truth implementations for these common operations.
"""

from typing import Any, Dict, List, Optional, Union
import re


def extract_category_name(category: Dict[str, Any]) -> str:
    """
    Extract the display name from a category dictionary.

    The Dandomain API returns category data with nested structure:
    category.texts.items[0].name

    This function handles various formats gracefully.

    Args:
        category: Raw category dictionary from API

    Returns:
        Category name string, or 'Unknown' if not found

    Example:
        name = extract_category_name(api_category)
        # Returns "Rengøringsmidler" or "Unknown"
    """
    if not category or not isinstance(category, dict):
        return "Unknown"

    # Try the standard API structure: texts.items[0].name
    texts = category.get("texts", {})
    if isinstance(texts, dict):
        items = texts.get("items", [])
        if items and len(items) > 0:
            name = items[0].get("name")
            if name:
                return str(name)

    # Fallback: try direct 'name' field
    if "name" in category:
        return str(category["name"])

    # Fallback: try 'nederste_kategori' (processed format)
    if "nederste_kategori" in category:
        return str(category["nederste_kategori"])

    return "Unknown"


def extract_product_number(
    product: Dict[str, Any],
    strip_deactivated: bool = True,
    fallback_fields: Optional[List[str]] = None,
) -> str:
    """
    Extract product number from a product dictionary.

    Handles various field names and formats used across the codebase:
    - PROD_NUM, product_number, number, PROD_NUM_old
    - Strips " - DEAKTIVERET" suffix if present and strip_deactivated=True
    - Handles "12345 - Product Name" format (extracts number part)

    Args:
        product: Product dictionary
        strip_deactivated: Remove " - DEAKTIVERET" suffix (default: True)
        fallback_fields: Additional fields to check for product number

    Returns:
        Product number string, or 'UNKNOWN' if not found

    Example:
        num = extract_product_number(product)
        # "E138450 - DEAKTIVERET" -> "E138450"
        # "12345 - Moppe" -> "12345"
    """
    if not product or not isinstance(product, dict):
        return "UNKNOWN"

    # Fields to check in priority order
    fields = ["PROD_NUM", "product_number", "number", "PROD_NUM_old"]
    if fallback_fields:
        fields.extend(fallback_fields)

    product_number = None

    for field in fields:
        value = product.get(field)
        if value and str(value).strip():
            product_number = str(value).strip()
            break

    if not product_number:
        return "UNKNOWN"

    # Strip " - DEAKTIVERET" suffix
    if strip_deactivated and " - DEAKTIVERET" in product_number:
        product_number = product_number.replace(" - DEAKTIVERET", "").strip()

    # Handle "12345 - Product Name" format - extract just the number
    if " - " in product_number:
        parts = product_number.split(" - ", 1)
        # Only use first part if it looks like a product number (alphanumeric)
        first_part = parts[0].strip()
        if re.match(r"^[A-Za-z0-9\-_]+$", first_part):
            product_number = first_part

    return product_number


def round_price_to_nearest(
    value: float,
    threshold: float = 1000.0,
    small_step: float = 0.25,
    large_step: float = 1.0,
) -> float:
    """
    Round a price value according to Danish pricing conventions.

    For prices below threshold: round to nearest small_step (e.g., 0.25)
    For prices at or above threshold: round to nearest large_step (e.g., 1.0)

    Args:
        value: Price value to round
        threshold: Price threshold for switching rounding rules (default: 1000)
        small_step: Rounding step for prices below threshold (default: 0.25)
        large_step: Rounding step for prices at/above threshold (default: 1.0)

    Returns:
        Rounded price value

    Example:
        round_price_to_nearest(12.37)  # -> 12.25
        round_price_to_nearest(1234.5)  # -> 1235.0
    """
    if value < threshold:
        return round(value / small_step) * small_step
    else:
        return round(value / large_step) * large_step


def extract_price_items(product: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract price entries from a product dictionary.

    Handles various formats:
    - product.prices.items (Dandomain API format)
    - product.prices (list format)
    - product.price_entries (processed format)

    Args:
        product: Product dictionary

    Returns:
        List of price entry dictionaries

    Example:
        prices = extract_price_items(product)
        for p in prices:
            print(p.get("unitPrice"), p.get("b2bGroupId"))
    """
    if not product or not isinstance(product, dict):
        return []

    # Try Dandomain API format: prices.items
    prices = product.get("prices", {})
    if isinstance(prices, dict):
        items = prices.get("items", [])
        if isinstance(items, list):
            return items

    # Try direct list format
    if isinstance(prices, list):
        return prices

    # Try processed format
    price_entries = product.get("price_entries", [])
    if isinstance(price_entries, list):
        return price_entries

    return []


def extract_category_numbers(product: Dict[str, Any]) -> List[str]:
    """
    Extract category numbers from a product dictionary.

    Handles various formats:
    - product.categories (list of category objects or numbers)
    - product.categoryNumbers (list of numbers)
    - product.PROD_CAT_ID (single category)

    Args:
        product: Product dictionary

    Returns:
        List of category number strings

    Example:
        categories = extract_category_numbers(product)
        # ["100", "200", "315"]
    """
    if not product or not isinstance(product, dict):
        return []

    result = []

    # Try categories field
    categories = product.get("categories", [])
    if isinstance(categories, list):
        for cat in categories:
            if isinstance(cat, dict):
                num = cat.get("number") or cat.get("categoryNumber")
                if num:
                    result.append(str(num))
            elif isinstance(cat, (str, int)):
                result.append(str(cat))

    # Try categoryNumbers field
    cat_numbers = product.get("categoryNumbers", [])
    if isinstance(cat_numbers, list):
        for num in cat_numbers:
            if str(num) not in result:
                result.append(str(num))

    # Try single PROD_CAT_ID
    prod_cat_id = product.get("PROD_CAT_ID")
    if prod_cat_id and str(prod_cat_id) not in result:
        result.append(str(prod_cat_id))

    return result


def extract_language_id(product: Dict[str, Any], default: int = 26) -> int:
    """
    Extract the language ID from a product dictionary.

    Args:
        product: Product dictionary
        default: Default language ID if not found (26 = Danish)

    Returns:
        Language ID integer
    """
    if not product or not isinstance(product, dict):
        return default

    # Try direct field
    lang_id = product.get("languageId") or product.get("language_id")
    if lang_id is not None:
        try:
            return int(lang_id)
        except (TypeError, ValueError):
            pass

    # Try texts.items[0].languageId
    texts = product.get("texts", {})
    if isinstance(texts, dict):
        items = texts.get("items", [])
        if items and len(items) > 0:
            lang_id = items[0].get("languageId")
            if lang_id is not None:
                try:
                    return int(lang_id)
                except (TypeError, ValueError):
                    pass

    return default


def build_product_identifier(product: Dict[str, Any]) -> str:
    """
    Build a human-readable identifier for a product (for logging/display).

    Args:
        product: Product dictionary

    Returns:
        String like "E138450 (Moppe)" or just "E138450"
    """
    number = extract_product_number(product)
    name = product.get("ORIGINAL_PROD_NAME") or product.get("name") or product.get("PROD_NAME")

    if name and name != number:
        # Truncate long names
        if len(name) > 40:
            name = name[:37] + "..."
        return f"{number} ({name})"

    return number
