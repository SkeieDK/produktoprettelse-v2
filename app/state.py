"""
Centralized Streamlit Session State Management

This module provides a clean interface for managing session state in the
Produktoprettelse-v2 Streamlit app, following the principle of single
source of truth for state.

Benefits:
- Centralized initialization
- Type hints for state keys
- Clear documentation of state structure
- Easier testing and debugging

Usage:
    from app.state import init_session_state, get_state, set_state

    # In app startup
    init_session_state()

    # Access state
    products = get_state("products", default=[])
    set_state("current_step", 3)
"""

import streamlit as st
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class PipelineStep(Enum):
    """Pipeline step identifiers."""
    UPLOAD = "upload"
    SANITIZE = "sanitize"
    SCRAPE = "scrape"
    IMAGES = "images"
    CATEGORIZE = "categorize"
    AI_GENERATE = "ai_generate"
    UPLOAD_CMS = "upload_cms"


class PriceAction(Enum):
    """Price management actions."""
    CREATE_OFFER = "create"
    REMOVE_OFFER = "remove"
    BULK_UPDATE = "bulk_update"


@dataclass
class StateDefaults:
    """Default values for session state keys."""

    # Authentication
    password_correct: bool = False

    # Pipeline state
    current_step: int = 0
    pipeline_running: bool = False
    pipeline_results: Dict[str, Any] = field(default_factory=dict)

    # Product data
    products: List[Dict[str, Any]] = field(default_factory=list)
    selected_products: List[str] = field(default_factory=list)
    products_cache_timestamp: Optional[float] = None

    # Categories
    categories: List[Dict[str, Any]] = field(default_factory=list)
    categories_cache_timestamp: Optional[float] = None

    # UI state
    search_query: str = ""
    filter_category: str = ""
    filter_supplier: str = ""
    sort_by: str = "name"
    page_number: int = 1
    items_per_page: int = 20

    # Price management
    price_active_action: Optional[str] = None
    price_selected_products: List[str] = field(default_factory=list)

    # Edit card visibility (dynamic keys)
    # Pattern: show_edit_card_{product_index} -> bool


# Default state configuration
_DEFAULTS = StateDefaults()


def init_session_state() -> None:
    """
    Initialize all session state keys with default values.

    Call this at the start of the app to ensure all state keys exist.
    Only sets values that don't already exist (preserves existing state).
    """
    defaults = {
        # Authentication
        "password_correct": _DEFAULTS.password_correct,

        # Pipeline
        "current_step": _DEFAULTS.current_step,
        "pipeline_running": _DEFAULTS.pipeline_running,
        "pipeline_results": _DEFAULTS.pipeline_results,

        # Products
        "products": _DEFAULTS.products,
        "selected_products": _DEFAULTS.selected_products,
        "products_cache_timestamp": _DEFAULTS.products_cache_timestamp,

        # Categories
        "categories": _DEFAULTS.categories,
        "categories_cache_timestamp": _DEFAULTS.categories_cache_timestamp,

        # UI
        "search_query": _DEFAULTS.search_query,
        "filter_category": _DEFAULTS.filter_category,
        "filter_supplier": _DEFAULTS.filter_supplier,
        "sort_by": _DEFAULTS.sort_by,
        "page_number": _DEFAULTS.page_number,
        "items_per_page": _DEFAULTS.items_per_page,

        # Price management
        "price_active_action": _DEFAULTS.price_active_action,
        "price_selected_products": _DEFAULTS.price_selected_products,
    }

    for key, default_value in defaults.items():
        if key not in st.session_state:
            # Handle mutable defaults properly
            if isinstance(default_value, (list, dict)):
                st.session_state[key] = type(default_value)(default_value)
            else:
                st.session_state[key] = default_value


def get_state(key: str, default: Any = None) -> Any:
    """
    Get a value from session state.

    Args:
        key: State key to retrieve
        default: Default value if key doesn't exist

    Returns:
        State value or default
    """
    return st.session_state.get(key, default)


def set_state(key: str, value: Any) -> None:
    """
    Set a value in session state.

    Args:
        key: State key to set
        value: Value to store
    """
    st.session_state[key] = value


def update_state(key: str, **updates) -> None:
    """
    Update a dict value in session state.

    Args:
        key: State key (must be a dict)
        **updates: Key-value pairs to update

    Example:
        update_state("pipeline_results", step_1="success", step_2="running")
    """
    if key not in st.session_state:
        st.session_state[key] = {}
    st.session_state[key].update(updates)


def clear_state(key: str) -> None:
    """
    Clear a state key (set to default or delete).

    Args:
        key: State key to clear
    """
    if hasattr(_DEFAULTS, key):
        default = getattr(_DEFAULTS, key)
        if isinstance(default, (list, dict)):
            st.session_state[key] = type(default)()
        else:
            st.session_state[key] = default
    elif key in st.session_state:
        del st.session_state[key]


def is_authenticated() -> bool:
    """Check if user is authenticated."""
    return get_state("password_correct", False)


def set_authenticated(value: bool) -> None:
    """Set authentication state."""
    set_state("password_correct", value)


# =============================================================================
# Pipeline State Helpers
# =============================================================================


def start_pipeline() -> None:
    """Mark pipeline as running."""
    set_state("pipeline_running", True)
    set_state("current_step", 1)
    set_state("pipeline_results", {})


def stop_pipeline() -> None:
    """Mark pipeline as stopped."""
    set_state("pipeline_running", False)


def set_step_result(step: int, status: str, message: str = "") -> None:
    """
    Record result for a pipeline step.

    Args:
        step: Step number (1-5)
        status: "success", "error", "skipped"
        message: Optional status message
    """
    update_state(
        "pipeline_results",
        **{f"step_{step}": {"status": status, "message": message}}
    )


def get_step_result(step: int) -> Optional[Dict[str, str]]:
    """Get result for a pipeline step."""
    results = get_state("pipeline_results", {})
    return results.get(f"step_{step}")


# =============================================================================
# Product State Helpers
# =============================================================================


def set_products(products: List[Dict[str, Any]]) -> None:
    """Store products in state."""
    import time
    set_state("products", products)
    set_state("products_cache_timestamp", time.time())


def get_products() -> List[Dict[str, Any]]:
    """Get products from state."""
    return get_state("products", [])


def select_product(product_id: str) -> None:
    """Add product to selection."""
    selected = get_state("selected_products", [])
    if product_id not in selected:
        selected.append(product_id)
        set_state("selected_products", selected)


def deselect_product(product_id: str) -> None:
    """Remove product from selection."""
    selected = get_state("selected_products", [])
    if product_id in selected:
        selected.remove(product_id)
        set_state("selected_products", selected)


def clear_product_selection() -> None:
    """Clear all selected products."""
    set_state("selected_products", [])


def get_selected_products() -> List[str]:
    """Get list of selected product IDs."""
    return get_state("selected_products", [])


# =============================================================================
# Edit Card State Helpers
# =============================================================================


def show_edit_card(product_index: int) -> None:
    """Show edit card for a product."""
    set_state(f"show_edit_card_{product_index}", True)


def hide_edit_card(product_index: int) -> None:
    """Hide edit card for a product."""
    set_state(f"show_edit_card_{product_index}", False)


def is_edit_card_visible(product_index: int) -> bool:
    """Check if edit card is visible for a product."""
    return get_state(f"show_edit_card_{product_index}", False)


# =============================================================================
# Price Management State Helpers
# =============================================================================


def set_price_action(action: str) -> None:
    """Set active price management action."""
    set_state("price_active_action", action)


def get_price_action() -> Optional[str]:
    """Get active price management action."""
    return get_state("price_active_action")


def clear_price_action() -> None:
    """Clear active price management action."""
    set_state("price_active_action", None)
