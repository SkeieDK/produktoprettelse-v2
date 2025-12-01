"""
Offer Service Module

Core business logic for creating and removing product offers.
Extracted from app/app.py to enable reuse across UI and CLI.

Functions:
- prepare_offer_operations: Build operation list without calling API
- execute_offer_action: Prepare and execute offer operations via API
"""

from typing import Any, Dict, List, Optional, Tuple

from .utils import (
    build_price_update,
    build_price_delete,
    extract_price_items,
    extract_category_numbers,
    extract_language_id,
)

# Import config to get offer category number
from core.config import load_config


def get_offer_category_number() -> str:
    """Get the offer category number from config.yaml."""
    try:
        config = load_config()
        return config.offer.category_number
    except Exception:
        # Fallback to default if config loading fails
        return "20400000000000"


# Category number for offer/tilbud products - loaded from config
OFFER_CATEGORY_NUMBER = get_offer_category_number()


def prepare_offer_operations(
    product: Dict[str, Any],
    action: str,
    new_offer_price: Optional[float] = None,
) -> Tuple[List[Dict[str, Optional[Dict[str, Any]]]], Dict[str, Any], str]:
    """
    Prepare a list of price operations for create/remove flows without calling APIs.

    This function analyzes the product's current price structure and builds
    the necessary operations to either create or remove an offer.

    Args:
        product: Product dictionary from API (must include prices)
        action: "create" or "remove"
        new_offer_price: Required for "create" action - the special offer price

    Returns:
        Tuple of (operations, context, error_message):
        - operations: List of dicts with "delete", "update", or "create" keys
        - context: Dict with "custom_field3" and other context info
        - error_message: Empty string on success, error description on failure

    Example:
        ops, ctx, err = prepare_offer_operations(product, "create", 79.95)
        if err:
            print(f"Error: {err}")
        else:
            api.update_product_prices(product_number, ops)
    """
    ops: List[Dict[str, Optional[Dict[str, Any]]]] = []
    ctx: Dict[str, Any] = {}

    def q_delete_create(original: Dict[str, Any], replacement: Dict[str, Any]) -> None:
        """Queue a delete followed by create operation."""
        ops.append({"delete": build_price_delete(original), "create": replacement})

    def q_update(payload: Dict[str, Any]) -> None:
        """Queue an update operation."""
        ops.append({"update": payload})

    # Extract current prices
    prices_local = extract_price_items(product)

    # Find primary price entry (b2bGroupId="-2", quantity=1)
    primary_entry = None
    for entry in prices_local:
        group_id = str(entry.get("b2bGroupId", ""))
        try:
            quantity_val = int(entry.get("quantity", 1) or 1)
        except (TypeError, ValueError):
            quantity_val = 1
        if group_id == "-2" and quantity_val == 1:
            primary_entry = entry
            break

    if primary_entry is None:
        return [], {}, "Ingen standardpris fundet"

    if action == "create":
        # Validate offer price
        if new_offer_price is None or new_offer_price <= 0:
            return [], {}, "Mangler gyldig tilbudspris"

        # Handle quantity breaks: move from b2bGroupId=-2 to b2bGroupId=1
        for entry in prices_local:
            group_id = str(entry.get("b2bGroupId", ""))
            quantity_val = int(entry.get("quantity", 1) or 1)
            if group_id == "-2" and quantity_val > 1:
                q_delete_create(
                    entry,
                    build_price_update(
                        entry,
                        b2b_override="1",
                        special_offer=None,
                        include_identity=False,
                    ),
                )

        # Update primary price with special offer
        q_update(
            build_price_update(
                primary_entry,
                b2b_override="-2",
                special_offer=new_offer_price,
                include_identity=True,
                special_offer_period=1,
            )
        )

        ctx["custom_field3"] = "Tilbud"
        ctx["price_entry"] = {**primary_entry, "specialOfferPrice": new_offer_price}

    elif action == "remove":
        # Handle quantity breaks: move from b2bGroupId=1 back to b2bGroupId=-2
        for entry in prices_local:
            group_id = str(entry.get("b2bGroupId", ""))
            quantity_val = int(entry.get("quantity", 1) or 1)
            if group_id == "1" and quantity_val > 1:
                q_delete_create(
                    entry,
                    build_price_update(
                        entry,
                        b2b_override="-2",
                        special_offer=None,
                        include_identity=False,
                    ),
                )

        # Clear special offer from primary price
        cleared_payload = build_price_update(
            primary_entry,
            b2b_override="-2",
            special_offer=None,
            include_identity=True,
        )
        q_update(cleared_payload)

        ctx["custom_field3"] = ""
        ctx["price_entry"] = {**primary_entry, "specialOfferPrice": None}

    else:
        return [], {}, "Ukendt handling"

    return ops, ctx, ""


def execute_offer_action(
    api,  # APIManager instance
    product: Dict[str, Any],
    action: str,
    new_offer_price: Optional[float] = None,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Execute offer creation or removal on a product.

    Combines prepare_offer_operations with API calls to:
    1. Update product prices (specialOfferPrice)
    2. Update customField3 ("Tilbud" or "")
    3. Update categories (add/remove offer category)

    Args:
        api: APIManager instance for API calls
        product: Product dictionary from API
        action: "create" or "remove"
        new_offer_price: Required for "create" action

    Returns:
        Tuple of (success, message, result):
        - success: True if all operations completed
        - message: Status message (error description on failure)
        - result: Updated price entry dict on success, None on failure

    Example:
        api = get_api_manager()
        success, msg, result = execute_offer_action(api, product, "create", 79.95)
        if success:
            st.success(f"Tilbud oprettet: {result['specialOfferPrice']} kr")
    """
    product_number = product.get("number")
    if not product_number:
        return False, "Produktnummer mangler", None

    # Get current prices and find standard entry
    prices = extract_price_items(product)
    standard_entry = None
    for entry in prices:
        group_id = str(entry.get("b2bGroupId", ""))
        quantity_val = int(entry.get("quantity", 1) or 1)
        if group_id == "-2" and quantity_val == 1:
            standard_entry = entry
            break

    if standard_entry is None:
        return False, "Ingen standardpris fundet", None

    # Prepare operations
    prepared_ops, prepared_ctx, prepare_err = prepare_offer_operations(
        product, action, new_offer_price
    )
    if prepare_err:
        return False, prepare_err, None

    price_operations = prepared_ops
    context = prepared_ctx

    # Execute price updates
    if price_operations and not api.update_product_prices(product_number, price_operations):
        return False, "Prisopdatering fejlede", None

    # Update customField3
    language_id = extract_language_id(product)
    if not api.update_product_custom_field3(
        product_number, language_id, context.get("custom_field3", "")
    ):
        return False, "Kunne ikke opdatere CustomField_3", None

    # Update categories
    categories = extract_category_numbers(product)
    category_set = set(categories)

    if action == "create":
        if OFFER_CATEGORY_NUMBER not in category_set:
            category_set.add(OFFER_CATEGORY_NUMBER)
            if not api.update_product_categories(product_number, list(category_set)):
                return False, "Kunne ikke opdatere kategorier", None
    else:  # remove
        if OFFER_CATEGORY_NUMBER in category_set:
            category_set.remove(OFFER_CATEGORY_NUMBER)
            if not api.update_product_categories(product_number, list(category_set)):
                return False, "Kunne ikke rydde kategori", None

    return True, "Success", context.get("price_entry")
