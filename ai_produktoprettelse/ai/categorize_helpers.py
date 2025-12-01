"""
Helper functions for product categorization (shared between embedding and LLM approaches)

Refactored from: scripts/categorize_helpers.py
Now uses core.product_utils for common functions.
"""

from typing import Dict, List

from core.product_utils import extract_category_name


def get_category_system_prompt() -> str:
    """System prompt for category classification."""
    return """You are a product categorization expert for a B2B cleaning and maintenance supplies webshop.

Task: Assign product to the most appropriate category.

Guidelines:
- Match by product type, vendor, use case
- Use example products as reference
- Vendor patterns matter (e.g., Vikan products)
- B2B/professional focus
- Return ONLY valid JSON: {"category_id": "...", "confidence": 0-100, "reasoning": "..."}"""


def get_category_user_prompt(
    product: Dict, category_tree: str, include_details: bool = True
) -> str:
    """
    Build user prompt for categorization (token-optimized).

    Args:
        product: Product details
        category_tree: Category hierarchy string (categories with active products only)
        include_details: If True, include description snippet
    """
    # Extract product details
    prod_name = product.get("ORIGINAL_PROD_NAME", product.get("PROD_NAME", "Unknown"))
    vendor = product.get("PrimaryVendorName", "Unknown")

    # Get supplier info snippet if available
    supplier_info = product.get("supplier_info", {})
    description = ""
    if isinstance(supplier_info, dict):
        description = supplier_info.get("description", "")
    elif supplier_info:
        description = str(supplier_info)

    # Build concise prompt
    prompt = f"""Kategoriser produkt:
Navn: {prod_name}
Leverandør: {vendor}
"""

    if include_details and description:
        prompt += f"Beskrivelse: {description[:250]}\n"

    prompt += f"""
Kategorier (med eksempler):
{category_tree}

Svar med JSON: {{"category_id": "...", "confidence": 0-100, "reasoning": "..."}}
Kun JSON, ingen markdown."""

    return prompt


def build_category_tree(
    categories: List[Dict],
    category_product_map: Dict[str, Dict],
    compact: bool = True,
) -> str:
    """
    Build category tree for AI prompt (token-optimized).

    Args:
        categories: List of category dicts (RAW API format with 'id', 'number', 'texts')
        category_product_map: Map of category_id to products (only includes categories with products)
        compact: Always True - only include categories with example products for token efficiency

    Returns:
        Formatted category list string with multiple product examples
    """
    tree_lines = []

    for cat in categories:
        cat_id = str(cat.get("id", ""))
        if not cat_id:
            continue

        # Only include categories that have mapped products
        if cat_id not in category_product_map:
            continue

        examples = category_product_map[cat_id].get("example_products", [])
        if not examples:  # Skip if no examples
            continue

        # Use centralized category name extraction
        cat_name = extract_category_name(cat)

        # Include full name (no truncation - it's meaningful info)
        tree_lines.append(f"ID {cat_id}: {cat_name}")

        # Add 5-10 example product names (better precision for LLM)
        if examples:
            short_names = [p["name"][:30] for p in examples[:10]]  # Up to 10 examples
            tree_lines.append(f"  Products: {', '.join(short_names)}")

    if not tree_lines:
        return "(No categories with products available)"

    return "\n".join(tree_lines)
