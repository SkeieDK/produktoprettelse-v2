#!/usr/bin/env python3
"""
Produktoprettelse-v2 Streamlit UI
Clean, light-themed interface inspired by client's product page design.

Features:
    - CSV upload and preview
    - Pipeline step execution with progress tracking
    - Live log tailing
    - Results gallery with product cards (light theme)
    - Image preview with max-size constraints
    - Search and filter
    - Export capabilities

Run with: streamlit run app/app.py
"""

import streamlit as st
import json
import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import pandas as pd
from PIL import Image
import time
from typing import Optional, Dict, Any, List, Tuple
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
DATA_INPUT = PROJECT_ROOT / "data" / "input"
DATA_OUTPUT = PROJECT_ROOT / "data" / "output"
LOGS_DIR = PROJECT_ROOT / "logs"
DATA_CACHE = PROJECT_ROOT / "data" / "cache"
CACHE_DIR = PROJECT_ROOT / "cache"
CATEGORIES_WITH_PRODUCTS_FILE = CACHE_DIR / "categories_with_products.json"
IMAGE_BASE_URL = "https://engrosrengoringsmidler.dk"
OFFER_CATEGORY_NUMBER = "20400000000000"

# Add scripts to path for imports
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

from api_manager import get_api_manager

# Create necessary directories
DATA_INPUT.mkdir(parents=True, exist_ok=True)
DATA_OUTPUT.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# PAGE CONFIGURATION & STYLING
# ============================================================================

st.set_page_config(
    page_title="Produktoprettelse-v2",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# AUTHENTICATION
# ============================================================================
def check_password():
    """Returns `True` if the user had the correct password."""
    
    # If no password is set in env, allow access (dev mode)
    # BUT warn the user
    env_password = os.getenv("APP_PASSWORD")
    if not env_password:
        st.sidebar.warning("⚠️ No APP_PASSWORD set in .env - App is unsecured!")
        return True

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == env_password:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password.
        st.text_input(
            "🔐 Indtast Adgangskode", type="password", on_change=password_entered, key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error.
        st.text_input(
            "🔐 Indtast Adgangskode", type="password", on_change=password_entered, key="password"
        )
        st.error("😕 Forkert adgangskode")
        return False
    else:
        # Password correct.
        return True

if not check_password():
    st.stop()

# Initialize session state for tracking pipeline execution
if "pipeline_status" not in st.session_state:
    st.session_state.pipeline_status = {
        "Step 1 (Sanitize)": False,
        "Step 2 (Scrape)": False,
        "Step 3 (Images)": False,
        "Step 3.5 (Kategorisering)": False,
        "Step 4 (AI)": False,
        "Step 5 (Upload)": False,
    }

st.session_state.setdefault("data_refresh_ready", False)
st.session_state.setdefault("data_refresh_summary", None)
st.session_state.setdefault("data_refresh_timestamp", None)

st.markdown(
    """
    <style>
        :root {
            --bg-primary: #f8f9fc;
            --bg-secondary: #ffffff;
            --text-primary: #1f2933;
            --text-secondary: #52606d;
            --text-light: #9aa5b1;
            --accent-color: #1f8ceb;
            --accent-dark: #1666ab;
            --accent-light: #e3f2fd;
            --border-color: #d2d6dc;
        }

        body {
            background: var(--bg-primary);
            color: var(--text-primary);
        }

        .main-header {
            margin-bottom: 25px;
        }

        .main-header h1 {
            font-size: 2.2em;
            color: var(--text-primary);
            font-weight: 700;
        }

        .main-header p {
            margin: 5px 0 0 0;
            color: var(--text-secondary);
            font-size: 0.95em;
        }

        .product-card {
            border: none;
            border-radius: 0;
            padding: 0;
            margin: 0;
            box-shadow: none;
            transition: none;
            border-bottom: 1px solid var(--accent-color);
        }

        .product-card:hover {
            box-shadow: none;
        }

        .stColumn {
            display: flex;
            align-items: center;
        }

        .product-image-container {
            text-align: center;
            margin: 10px 0;
            display: flex;
            align-items: center;
            justify-content: center;
            background: var(--bg-secondary);
            border-radius: 4px;
            padding: 8px;
            width: 100%;
            aspect-ratio: 16 / 9;
            overflow: hidden;
        }

        .product-image-container img {
            max-width: 100%;
            max-height: 100%;
            width: auto;
            height: auto;
            object-fit: contain;
        }

        .product-title {
            color: var(--text-primary);
            font-size: 1.2em;
            font-weight: 600;
            margin: 10px 0;
        }

        .product-id {
            color: var(--text-light);
            font-size: 0.85em;
            margin-bottom: 5px;
            font-family: monospace;
        }

        .product-supplier {
            color: var(--accent-color);
            font-size: 0.9em;
            margin-bottom: 8px;
            text-decoration: none;
        }

        .product-description {
            color: var(--text-primary);
            line-height: 1.6;
            margin: 12px 0;
            font-size: 0.95em;
        }

        .product-keywords {
            color: var(--accent-color);
            font-size: 0.8em;
            margin: 10px 0;
        }

        .keyword-tag {
            display: inline-block;
            background: var(--accent-light);
            color: var(--accent-color);
            padding: 4px 8px;
            border-radius: 3px;
            margin: 2px 2px 2px 0;
            font-size: 0.8em;
        }

        .step-card {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-left: 4px solid var(--accent-color);
            padding: 15px;
            margin: 10px 0;
            border-radius: 4px;
        }

        .step-status {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: 600;
            margin-right: 10px;
        }

        .status-complete {
            background: #e8f5e9;
            color: #2e7d32;
        }

        @media (prefers-color-scheme: dark) {
            .status-complete {
                background: #1b5e20;
                color: #81c784;
            }
        }

        .status-running {
            background: #fff3e0;
            color: #e65100;
        }

        @media (prefers-color-scheme: dark) {
            .status-running {
                background: #e65100;
                color: #ffe0b2;
            }
        }

        .status-pending {
            background: var(--bg-secondary);
            color: var(--text-secondary);
        }

        .stTabs [data-baseweb="tab-list"] {
            background: var(--bg-primary);
            border-bottom: 2px solid var(--border-color);
        }

        .stTabs [data-baseweb="tab-list"] button {
            color: var(--text-secondary);
            background: var(--bg-primary);
        }

        .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
            color: var(--accent-color);
            border-bottom: 2px solid var(--accent-color);
        }

        .stButton > button {
            background: var(--accent-color);
            color: #ffffff;
            border: none;
            border-radius: 4px;
            padding: 10px 20px;
            font-weight: 600;
            transition: background 0.2s;
        }

        .stButton > button:hover {
            background: var(--accent-dark);
        }

        .streamlit-expanderHeader {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
        }

        .metric-container {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            padding: 15px;
            border-radius: 4px;
            text-align: center;
        }

        .metric-value {
            font-size: 2em;
            font-weight: 700;
            color: var(--accent-color);
        }

        .metric-label {
            color: var(--text-secondary);
            font-size: 0.9em;
            margin-top: 5px;
        }

        body, p, span, div {
            color: var(--text-primary);
        }

        .stTextInput input,
        .stSelectbox select,
        .stNumberInput input {
            background: var(--bg-secondary);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def load_json_file(filepath):
    """Load JSON file safely."""
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        st.warning(f"Could not load {filepath}: {e}")
    return None

def save_json_file(filepath, data):
    """Save JSON file safely."""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Could not save {filepath}: {e}")
        return False


def extract_product_name(product: Dict[str, Any]) -> str:
    """Fetch a product display name from raw API payload."""
    if not product:
        return "Ukendt produkt"
    direct_name = product.get('name')
    if direct_name:
        return direct_name
    settings = product.get('settings')
    if isinstance(settings, dict):
        items = settings.get('items') or []
        if items:
            first = items[0] or {}
            name = first.get('name')
            if name:
                return name
    return product.get('number', 'Ukendt produkt')


def calculate_price_from_margin(cost_price: float, margin_percent: float) -> float:
    """Calculate rounded sales price from cost and desired margin."""
    if margin_percent >= 100:
        return float(cost_price)
    if margin_percent < 0:
        margin_percent = 0
    denominator = 1 - (margin_percent / 100.0)
    if denominator <= 0:
        return float(cost_price)
    if cost_price is None:
        return 0.0
    raw_price = 0.0
    try:
        raw_price = float(cost_price) / denominator if denominator else float(cost_price)
    except ZeroDivisionError:
        raw_price = float(cost_price)
    return round_price(raw_price)


def round_price(value: float) -> float:
    """Apply Danish rounding rules for pricing."""
    dec_value = Decimal(str(value))
    if dec_value > Decimal('300'):
        return float(dec_value.to_integral_value(rounding=ROUND_HALF_UP))
    if dec_value > Decimal('200'):
        step = Decimal('0.5')
    else:
        step = Decimal('0.1')
    return float((dec_value / step).to_integral_value(rounding=ROUND_HALF_UP) * step)


def coerce_price_value(value: Any) -> Optional[float]:
    """Convert editor input to float or None."""
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except TypeError:
        pass
    text = str(value).strip()
    if text in ("", "None"):
        return None
    try:
        return float(text.replace(",", "."))
    except (TypeError, ValueError):
        return None


def compute_savings_pct(current_price: float, new_price: float) -> float:
    try:
        current_val = float(current_price or 0.0)
        new_val = float(new_price or 0.0)
    except (TypeError, ValueError):
        return 0.0
    if current_val > 0:
        return round(((current_val - new_val) / current_val) * 100, 1)
    return 0.0


def compute_margin_pct(cost_price: Any, sale_price: Any) -> float:
    """Compute margin percentage based on cost and sale price."""
    try:
        cost_val = float(cost_price or 0.0)
        sale_val = float(sale_price or 0.0)
    except (TypeError, ValueError):
        return 0.0
    if sale_val <= 0:
        return 0.0
    return round(((sale_val - cost_val) / sale_val) * 100, 1)


def find_primary_price_entry(product: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    for entry in extract_price_items(product):
        group_id = str(entry.get("b2bGroupId", ""))
        try:
            quantity_val = int(entry.get("quantity", 1) or 1)
        except (TypeError, ValueError):
            quantity_val = 1
        if group_id == "-2" and quantity_val == 1:
            return entry
    return None


def build_price_row(product: Dict[str, Any], *, mark_for_update: bool = False) -> Optional[Dict[str, Any]]:
    entry = find_primary_price_entry(product)
    if not entry:
        return None

    def to_float(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    cost_price = to_float(product.get("costPrice"))
    current_price = to_float(entry.get("unitPrice"))
    special_offer_raw = entry.get("specialOfferPrice")
    special_offer = to_float(special_offer_raw) if special_offer_raw not in (None, "", 0) else None

    image_link = product.get("pictureLink") or ""
    if image_link and not image_link.startswith("http"):
        image_link = f"{IMAGE_BASE_URL}{image_link}"

    category_numbers = extract_category_numbers(product)
    offer_label = ""
    if special_offer and special_offer > 0:
        offer_label = "Tilbud"
    elif OFFER_CATEGORY_NUMBER in category_numbers:
        offer_label = "Tilbud"

    row: Dict[str, Any] = {
        "Billede": image_link,
        "Varenummer": product.get("number", ""),
        "Produktnavn": extract_product_name(product),
        "Tilbud Label": offer_label,
        "Kostpris": cost_price,
        "Nuværende Pris": current_price,
        "Ny Tilbudspris": special_offer,
        "Ny Margin %": compute_margin_pct(cost_price, special_offer) if special_offer else 0.0,
        "Besparelse %": compute_savings_pct(current_price, special_offer) if special_offer else 0.0,
        "Opdater": bool(mark_for_update),
        "_cost_price": cost_price,
        "_currency": entry.get("currencyCode", "DKK"),
        "_category_numbers": category_numbers,
        "_price_payload": entry,
        "_custom_field3": product.get("customField3", ""),
    }
    return row


PRICE_DATA_COLUMNS = [
    "Billede",
    "Varenummer",
    "Produktnavn",
    "Tilbud Label",
    "Kostpris",
    "Nuværende Pris",
    "Ny Tilbudspris",
    "Ny Margin %",
    "Besparelse %",
    "Opdater",
    "_cost_price",
    "_currency",
    "_category_numbers",
    "_price_payload",
    "_custom_field3",
]

PRICE_DATA_DEFAULTS: Dict[str, Any] = {
    "Billede": "",
    "Varenummer": "",
    "Produktnavn": "",
    "Tilbud Label": "",
    "Kostpris": 0.0,
    "Nuværende Pris": 0.0,
    "Ny Tilbudspris": None,
    "Ny Margin %": 0.0,
    "Besparelse %": 0.0,
    "Opdater": False,
    "_cost_price": 0.0,
    "_currency": "DKK",
    "_category_numbers": [],
    "_price_payload": {},
    "_custom_field3": "",
}


def normalize_price_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=PRICE_DATA_COLUMNS)
    row_count = len(df)
    for column in PRICE_DATA_COLUMNS:
        if column not in df.columns:
            default_value = PRICE_DATA_DEFAULTS.get(column)
            if isinstance(default_value, list):
                df[column] = [list(default_value) for _ in range(row_count)]
            elif isinstance(default_value, dict):
                df[column] = [default_value.copy() for _ in range(row_count)]
            else:
                df[column] = default_value
    return df[PRICE_DATA_COLUMNS]


_RETAIN_SPECIAL = object()


def extract_price_items(product: Dict[str, Any]) -> List[Dict[str, Any]]:
    prices_raw = product.get("prices")
    if isinstance(prices_raw, dict):
        return list(prices_raw.get("items", []) or [])
    if isinstance(prices_raw, list):
        return list(prices_raw)
    return []


def extract_category_numbers(product: Dict[str, Any]) -> List[str]:
    categories_raw = product.get("categories")
    if isinstance(categories_raw, dict):
        items = categories_raw.get("items", []) or []
    elif isinstance(categories_raw, list):
        items = categories_raw
    else:
        items = []
    return [str(cat.get("number")) for cat in items if cat.get("number")]


def extract_language_id(product: Dict[str, Any]) -> int:
    settings_raw = product.get("settings")
    if isinstance(settings_raw, dict):
        items = settings_raw.get("items", []) or []
    elif isinstance(settings_raw, list):
        items = settings_raw
    else:
        items = []
    if items:
        try:
            return int(items[0].get("languageId", 26) or 26)
        except (TypeError, ValueError):
            return 26
    return 26


def build_price_update(
    entry: Dict[str, Any],
    *,
    b2b_override: Optional[str] = None,
    special_offer: Any = _RETAIN_SPECIAL,
    include_identity: bool = True,
    special_offer_period: Optional[Any] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    payload["unitPrice"] = float(entry.get("unitPrice", 0.0) or 0.0)
    payload["currencyCode"] = entry.get("currencyCode", "DKK")
    quantity_raw = entry.get("quantity", 1)
    try:
        quantity_val = int(quantity_raw)
    except (TypeError, ValueError):
        quantity_val = 1
    payload["quantity"] = max(quantity_val, 1)

    group_value = b2b_override if b2b_override is not None else entry.get("b2bGroupId")
    if group_value is not None:
        payload["b2bGroupId"] = str(group_value)

    if special_offer is _RETAIN_SPECIAL:
        existing_offer = entry.get("specialOfferPrice")
        existing_offer_val = float(existing_offer) if existing_offer is not None else 0.0
        if existing_offer_val > 0:
            payload["specialOfferPrice"] = existing_offer_val
            special_period_val = entry.get("specialOfferPeriodId")
            if special_period_val is not None:
                payload["specialOfferPeriodId"] = str(special_period_val)
    else:
        if special_offer is None:
            payload["specialOfferPrice"] = None
            payload["specialOfferPeriodId"] = None
        else:
            try:
                payload["specialOfferPrice"] = float(special_offer)
            except (TypeError, ValueError):
                payload["specialOfferPrice"] = special_offer
            special_period_val = special_offer_period
            if special_period_val is None:
                special_period_val = entry.get("specialOfferPeriodId")
            if special_period_val is not None:
                payload["specialOfferPeriodId"] = str(special_period_val)

    if include_identity:
        price_id = entry.get("id") or entry.get("priceId")
        if price_id is not None:
            payload["id"] = str(price_id)

    period_info = entry.get("period")
    if isinstance(period_info, dict):
        period_id = period_info.get("id")
        if period_id is not None:
            payload["periodId"] = str(period_id)
    elif entry.get("periodId") is not None:
        payload["periodId"] = str(entry.get("periodId"))

    for extra_key in ("advance", "amount", "isoCode"):
        extra_value = entry.get(extra_key)
        if extra_value is not None:
            payload[extra_key] = extra_value

    return payload


def build_price_delete(entry: Dict[str, Any]) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "currencyCode": entry.get("currencyCode", "DKK"),
        "quantity": int(entry.get("quantity", 1) or 1),
    }
    unit_price_raw = entry.get("unitPrice")
    if unit_price_raw is not None:
        try:
            payload["unitPrice"] = float(unit_price_raw)
        except (TypeError, ValueError):
            payload["unitPrice"] = unit_price_raw
    group_val = entry.get("b2bGroupId")
    if group_val is not None:
        payload["b2bGroupId"] = str(group_val)

    price_id = entry.get("id") or entry.get("priceId")
    if price_id is not None:
        payload["id"] = str(price_id)

    period_info = entry.get("period")
    if isinstance(period_info, dict):
        period_id = period_info.get("id")
        if period_id is not None:
            payload["periodId"] = str(period_id)
    elif entry.get("periodId") is not None:
        payload["periodId"] = str(entry.get("periodId"))

    special_period = entry.get("specialOfferPeriodId")
    if special_period is not None:
        payload["specialOfferPeriodId"] = str(special_period)

    special_price = entry.get("specialOfferPrice")
    if special_price is not None:
        try:
            payload["specialOfferPrice"] = float(special_price)
        except (TypeError, ValueError):
            payload["specialOfferPrice"] = special_price

    for extra_key in ("advance", "amount", "isoCode"):
        extra_value = entry.get(extra_key)
        if extra_value is not None:
            payload[extra_key] = extra_value
    return payload


def execute_offer_action(
    api,
    product: Dict[str, Any],
    action: str,
    new_offer_price: Optional[float] = None,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    product_number = product.get("number")
    if not product_number:
        return False, "Produktnummer mangler", None

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

    price_operations: List[Dict[str, Optional[Dict[str, Any]]]] = []
    context: Dict[str, Any] = {}

    def queue_delete_create(original: Dict[str, Any], replacement: Dict[str, Any]) -> None:
        price_operations.append({
            "delete": build_price_delete(original),
            "create": replacement,
        })

    def queue_update(update_payload: Dict[str, Any]) -> None:
        price_operations.append({"update": update_payload})

    if action == "create":
        if new_offer_price is None or new_offer_price <= 0:
            return False, "Mangler gyldig tilbudspris", None
        for entry in prices:
            group_id = str(entry.get("b2bGroupId", ""))
            quantity_val = int(entry.get("quantity", 1) or 1)
            if group_id == "-2" and quantity_val > 1:
                queue_delete_create(
                    entry,
                    build_price_update(
                        entry,
                        b2b_override="1",
                        special_offer=None,
                        include_identity=False,
                    ),
                )
        queue_update(
            build_price_update(
                standard_entry,
                b2b_override="-2",
                special_offer=new_offer_price,
                include_identity=True,
            )
        )
        context["custom_field3"] = "Tilbud"
        context["price_entry"] = {**standard_entry, "specialOfferPrice": new_offer_price}
    elif action == "remove":
        for entry in prices:
            group_id = str(entry.get("b2bGroupId", ""))
            quantity_val = int(entry.get("quantity", 1) or 1)
            if group_id == "1" and quantity_val > 1:
                queue_delete_create(
                    entry,
                    build_price_update(
                        entry,
                        b2b_override="-2",
                        special_offer=None,
                        include_identity=False,
                    ),
                )
        cleared_payload = build_price_update(
            standard_entry,
            b2b_override="-2",
            special_offer=None,
            include_identity=True,
        )
        queue_update(cleared_payload)
        context["custom_field3"] = ""
        context["price_entry"] = {**standard_entry, "specialOfferPrice": None}
    else:
        return False, "Ukendt handling", None

    if price_operations and not api.update_product_prices(product_number, price_operations):
        return False, "Prisopdatering fejlede", None

    language_id = extract_language_id(product)
    if not api.update_product_custom_field3(product_number, language_id, context.get("custom_field3", "")):
        return False, "Kunne ikke opdatere CustomField_3", None

    categories = extract_category_numbers(product)
    category_set = set(categories)

    if action == "create":
        if OFFER_CATEGORY_NUMBER not in category_set:
            category_set.add(OFFER_CATEGORY_NUMBER)
            if not api.update_product_categories(product_number, list(category_set)):
                return False, "Kunne ikke opdatere kategorier", None
    else:
        if OFFER_CATEGORY_NUMBER in category_set:
            category_set.remove(OFFER_CATEGORY_NUMBER)
            if not api.update_product_categories(product_number, list(category_set)):
                return False, "Kunne ikke rydde kategori", None

    if action == "create":
        category_set.add(OFFER_CATEGORY_NUMBER)
    else:
        category_set.discard(OFFER_CATEGORY_NUMBER)

    context["categories"] = list(category_set)
    return True, "", context

def update_product_descriptions(product_number: str, desc_short: str, desc_long: str, searchwords: str, meta_desc: str) -> bool:
    """
    Update product descriptions and save to final_products.json.

    Args:
        product_number: Product number to update
        desc_short: Short description
        desc_long: Long description
        searchwords: Search keywords
        meta_desc: Meta description

    Returns:
        True if successful, False otherwise
    """
    try:
        final_path = DATA_OUTPUT / "final_products.json"
        if not final_path.exists():
            st.error("final_products.json ikke fundet")
            return False
        
        products = load_json_file(final_path)
        if not products:
            st.error("Kunne ikke læse produkter")
            return False
        
        if isinstance(products, dict):
            products = [products]
        
        # Find and update the product
        for idx, prod in enumerate(products):
            if prod.get("product_number", "") == product_number:
                prod["DESC_SHORT"] = desc_short
                prod["DESC_LONG"] = desc_long
                prod["PROD_SEARCHWORD"] = searchwords
                prod["META_DESCRIPTION"] = meta_desc
                prod["manually_edited"] = True
                products[idx] = prod
                
                # Save
                return save_json_file(final_path, products)
        
        st.error(f"Produkt {product_number} ikke fundet")
        return False
        
    except Exception as e:
        st.error(f"Fejl ved opdatering: {str(e)}")
        return False

def get_latest_log_lines(n=20):
    """Get the latest n lines from the main log."""
    log_file = LOGS_DIR / "product_enrichment.log"
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            return ''.join(lines[-n:]) if lines else "No logs available"
    return "Log file not found"

def get_process_status():
    """Check status of each pipeline step based on execution tracking."""
    # Use session state tracking - only show completed if actually run in this session
    return st.session_state.pipeline_status

def display_product_card(product, show_actions=False, product_index=None):
    """Display a single product card in light theme with image and details side-by-side."""
    # Get product number - extract just the number part
    prod_num_raw = product.get('product_number', 'N/A')
    if isinstance(prod_num_raw, str) and ' - ' in prod_num_raw:
        prod_num = prod_num_raw.split(' - ')[0].strip()
    else:
        prod_num = prod_num_raw
    
    # Get product title - DESC_SHORT contains the actual title
    title = product.get('DESC_SHORT') or product.get('PROD_NAME') or product.get('product_name', 'No title')
    
    # Start the product card wrapper
    st.markdown("""<div class="product-card" style="display: flex; gap: 20px; align-items: flex-start; padding: 20px 0; margin: 8px 0;">""", unsafe_allow_html=True)
    
    # LEFT COLUMN: IMAGE (25% width) - with max-height 250px
    col_left, col_right = st.columns([0.8, 1.7])
    
    with col_left:
        # Product images
        images_to_display = []
        if product.get('PROD_IMAGE'):
            images_to_display = [product.get('PROD_IMAGE')]
        elif product.get('images'):
            img_list = product.get('images', [])
            if isinstance(img_list, str):
                images_to_display = [img_list]
            else:
                images_to_display = img_list[:1]
        
        # Display image with max-height 250px
        if images_to_display:
            for image_path in images_to_display:
                if image_path:
                    if isinstance(image_path, str):
                        if '/' in image_path:
                            filename = image_path.split('/')[-1]
                        else:
                            filename = image_path
                        img_full_path = DATA_OUTPUT / "images" / filename
                        
                        if os.path.exists(img_full_path):
                            try:
                                img = Image.open(img_full_path)
                                st.markdown("""
                                <style>
                                .stImage img { max-height: 250px !important; width: auto !important; }
                                </style>
                                """, unsafe_allow_html=True)
                                st.image(img, width='stretch')
                            except Exception as e:
                                pass
    
    # RIGHT COLUMN: DETAILS (75% width)
    with col_right:
        st.markdown(f"""
        <div style="padding: 5px 0;">
            <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px;">
                <div class="product-title" style="text-align: left; margin: 0; flex: 1;">{title}</div>
                <div class="product-id" style="text-align: right;">Varenummer: {prod_num}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Expandable descriptions
        desc_short = product.get('DESC_SHORT') or product.get('short_description')
        desc_long = product.get('DESC_LONG') or product.get('long_description') or product.get('supplier_info')
        
        if desc_short:
            with st.expander("📝 Kort beskrivelse"):
                st.markdown(f'<div class="product-description">{desc_short}</div>', 
                           unsafe_allow_html=True)
        
        if desc_long:
            with st.expander("📖 Fuld beskrivelse"):
                st.markdown(f'<div class="product-description">{desc_long[:800]}...</div>', 
                           unsafe_allow_html=True)
        
        # Keywords
        if product.get('PROD_SEARCHWORD'):
            with st.expander("🔑 Søgeord"):
                keywords = product.get('PROD_SEARCHWORD', '')
                if isinstance(keywords, list):
                    keyword_list = keywords
                else:
                    keyword_list = [k.strip() for k in keywords.split(',')]
                
                keyword_html = ''.join([f'<span class="keyword-tag">{k}</span>' for k in keyword_list])
                st.markdown(f'<div class="product-keywords">{keyword_html}</div>', unsafe_allow_html=True)
        
        # CATEGORY DISPLAY - Always visible, prominent placement
        st.divider()
        
        # Load kategorier – foretræk den filtrerede cache fra dataopdateringen
        categories_cache_file = CACHE_DIR / "categories_cache.json"
        products_cache_file = CACHE_DIR / "products_cache.json"
        filtered_categories_file = CATEGORIES_WITH_PRODUCTS_FILE

        all_categories = []

        if filtered_categories_file.exists():
            all_categories = load_json_file(filtered_categories_file) or []
        elif categories_cache_file.exists():
            all_categories = load_json_file(categories_cache_file) or []
            if all_categories and products_cache_file.exists():
                api_products = load_json_file(products_cache_file) or []
                category_numbers_with_products = set()
                for product_item in api_products:
                    primary_cat_number = product_item.get('primaryCategoryId')
                    default_cat_number = product_item.get('defaultCategoryId')
                    if primary_cat_number:
                        category_numbers_with_products.add(str(primary_cat_number))
                    if default_cat_number:
                        category_numbers_with_products.add(str(default_cat_number))
                    categories_rel = product_item.get('categories')
                    if isinstance(categories_rel, dict):
                        for cat_entry in categories_rel.get('items', []) or []:
                            number = cat_entry.get('number')
                            if number:
                                category_numbers_with_products.add(str(number))
                all_categories = [
                    cat for cat in all_categories
                    if str(cat.get('number')) in category_numbers_with_products
                ]
        else:
            st.warning("Ingen kategori-cache fundet. Kør 'Hent nyeste data' først.")

        if not all_categories:
            st.warning("Ingen kategorier med produkter tilgængelige. Kør 'Hent nyeste data'.")
            
        if all_categories:
            # Build category lookup: id -> name and id -> number
            category_by_id = {}
            category_id_to_number = {}
            category_number_to_id = {}
            category_names = []
            for cat in all_categories:
                cat_id = cat.get('id')
                cat_number = cat.get('number', '')
                cat_name = cat.get('texts', {}).get('items', [{}])[0].get('name', 'Unavngivet')
                if cat_id and cat_name:
                    category_by_id[cat_id] = cat_name
                    category_id_to_number[cat_id] = cat_number
                    category_id_to_number[str(cat_id)] = cat_number  # Handle both int and string
                    if cat_number:
                        category_number_to_id[cat_number] = cat_id
                        category_number_to_id[str(cat_number)] = cat_id
                    category_names.append((cat_id, cat_name, cat_number))
            
            # Sort category names alphabetically
            category_names.sort(key=lambda x: x[1])
            
            # Get current category - check both ai_categorization and primaryCategoryId
            ai_cat = product.get('ai_categorization', {})
            current_cat_id = ai_cat.get('category_id') if ai_cat else None
            
            # If no ai_categorization.category_id, try to get from primaryCategoryId
            if not current_cat_id and product.get('primaryCategoryId'):
                primary_cat_number = product.get('primaryCategoryId')
                current_cat_id = category_number_to_id.get(primary_cat_number) or category_number_to_id.get(str(primary_cat_number))
            
            current_cat_name = ai_cat.get('category_name', 'Ingen kategori') if ai_cat else 'Ingen kategori'
            confidence = ai_cat.get('confidence', 0) if ai_cat else 0
            
            # Find current index in category list and get actual name
            current_index = 0
            found_in_list = False
            if current_cat_id:
                for i, (cat_id, cat_name, cat_number) in enumerate(category_names):
                    # Handle both string and int IDs
                    if str(cat_id) == str(current_cat_id) or cat_id == current_cat_id:
                        current_index = i
                        current_cat_name = cat_name
                        found_in_list = True
                        break
                
                # Debug: Show if we couldn't find the category
                if not found_in_list:
                    st.warning(f"⚠️ Category ID {current_cat_id} not found in categories list (Total categories: {len(category_names)})")
            
            # Display current category (ALWAYS VISIBLE)
            col_cat_label, col_cat_conf = st.columns([3, 1])
            with col_cat_label:
                st.markdown(f"**📁 Kategori:** {current_cat_name}")
            with col_cat_conf:
                if confidence > 0:
                    st.markdown(f"**Tillid:** {confidence}%")
            
            # Category editor dropdown (when actions enabled)
            if show_actions and product_index is not None:
                # Selectbox with just category names
                selected_index = st.selectbox(
                    "Skift kategori:",
                    options=range(len(category_names)),
                    format_func=lambda i: category_names[i][1],
                    index=current_index,
                    key=f"category_select_{product_index}"
                )
                
                new_cat_id, new_cat_name, new_cat_number = category_names[selected_index]
                
                # Only show save button if category changed
                if str(new_cat_id) != str(current_cat_id):
                    if st.button("💾 Gem ændring", key=f"save_category_{product_index}", type="primary"):
                        # Update product with both ai_categorization AND primaryCategoryId
                        product['ai_categorization'] = {
                            'category_id': new_cat_id,
                            'category_name': new_cat_name,
                            'confidence': 100,  # Manual selection = 100% confidence
                            'method': 'manual'
                        }
                        product['primaryCategoryId'] = new_cat_number  # Set the category number for API
                        
                        # Save to file
                        final_products_file = DATA_OUTPUT / "final_products.json"
                        products = load_json_file(final_products_file) or []
                        for p in products:
                            if p.get('product_number') == prod_num_raw:
                                p['ai_categorization'] = product['ai_categorization']
                                p['primaryCategoryId'] = new_cat_number
                                break
                        
                        with open(final_products_file, 'w', encoding='utf-8') as f:
                            json.dump(products, f, ensure_ascii=False, indent=2)
                        
                        st.success(f"✅ Kategori opdateret til: {new_cat_name}")
                        time.sleep(0.8)
                        st.rerun()
        
        # Metadata
        if product.get('META_DESCRIPTION'):
            with st.expander("🎯 SEO Metadata"):
                st.markdown(
                    f'<div class="product-description"><strong>Meta beskrivelse:</strong><br/>{product.get("META_DESCRIPTION", "")}</div>',
                    unsafe_allow_html=True,
                )
        st.divider()
        approved = product.get('approved_example')
        col_status, col_approve, col_regen = st.columns([2, 1, 1])

        with col_status:
            st.caption("Brug som inspiration")
            if approved:
                st.success("Godkendt eksempel")
            else:
                st.info("Afventer godkendelse")

        with col_approve:
            st.caption("Brug som inspiration")
            if st.button("✅ Godkend", key=f"approve_card_{product_index}", width='stretch'):
                product['approved_example'] = True
                final_products_file = DATA_OUTPUT / "final_products.json"
                products = load_json_file(final_products_file) or []
                # Find and update the product - use raw product number
                for p in products:
                    if p.get('product_number') == prod_num_raw:
                        p['approved_example'] = True
                        break
                with open(final_products_file, 'w', encoding='utf-8') as f:
                    json.dump(products, f, ensure_ascii=False, indent=2)
                st.success("Godkendt!")
                time.sleep(0.5)
                st.rerun()

        with col_regen:
            st.caption("Rediger manuelt")
            if st.button("✏️ Rediger", key=f"edit_card_{product_index}", width='stretch'):
                st.session_state[f"show_edit_card_{product_index}"] = True
                st.rerun()
            
            # Edit interface
            if st.session_state.get(f"show_edit_card_{product_index}", False):
                st.markdown("#### ✏️ Rediger Produktbeskrivelser")
                st.caption("Ændringer gemmes automatisk i final_products.json")
                
                # Get current values
                current_short = product.get("DESC_SHORT", "")
                current_long = product.get("DESC_LONG", "")
                current_search = product.get("PROD_SEARCHWORD", "")
                current_meta = product.get("META_DESCRIPTION", "")
                
                # Edit fields
                edited_short = st.text_area(
                    "Kort beskrivelse:",
                    value=current_short,
                    key=f"edit_short_{product_index}",
                    height=80
                )
                
                edited_long = st.text_area(
                    "Fuld beskrivelse:",
                    value=current_long,
                    key=f"edit_long_{product_index}",
                    height=200
                )
                
                edited_search = st.text_input(
                    "Søgeord (kommasepareret):",
                    value=current_search,
                    key=f"edit_search_{product_index}"
                )
                
                edited_meta = st.text_input(
                    "Meta beskrivelse (max 155 tegn):",
                    value=current_meta,
                    key=f"edit_meta_{product_index}",
                    max_chars=155
                )
                
                col_save, col_cancel = st.columns(2)
                with col_save:
                    if st.button("💾 Gem Ændringer", key=f"save_edit_card_{product_index}", width='stretch'):
                        if update_product_descriptions(
                            product_number=prod_num_raw,  # Use raw product number with " - Deaktiveret"
                            desc_short=edited_short or "",
                            desc_long=edited_long or "",
                            searchwords=edited_search or "",
                            meta_desc=edited_meta or ""
                        ):
                            st.success("✅ Ændringer gemt!")
                            st.session_state[f"show_edit_card_{product_index}"] = False
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ Kunne ikke gemme ændringer")
                
                with col_cancel:
                    if st.button("❌ Annuller", key=f"cancel_edit_card_{product_index}", width='stretch'):
                        st.session_state[f"show_edit_card_{product_index}"] = False
                        st.rerun()
    
    # Close the product card
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================================
# MAIN APP
# ============================================================================

# Header
st.markdown("""
<div class="main-header">
    <h1>📊 Produktoprettelse-v2</h1>
    <p>Administration af produktberigelses-pipeline</p>
</div>
""", unsafe_allow_html=True)

# Tabs
tab1, tab2, tab_prices, tab3, tab4 = st.tabs(["📤 Upload & Kør", "📊 Resultater", "💰 Prisstyring", "🤖 AI Management", "📋 Logs"])

# ============================================================================
# TAB 1: UPLOAD & EXECUTE
# ============================================================================

with tab1:
    st.markdown("### 🔄 Hent nyeste data")
    st.caption("Henter produkter og kategorier fra Dandomain. Operationen kan tage et par minutter.")
    if st.button("🔄 Hent nyeste data", key="refresh_data_button", type="primary"):
        api = get_api_manager()
        with st.spinner("Henter data fra Dandomain..."):
            try:
                refresh_stats = api.refresh_all_caches()
            except Exception as e:
                st.session_state.data_refresh_ready = False
                st.session_state.data_refresh_summary = None
                st.session_state.data_refresh_timestamp = None
                st.error(f"❌ Fejl ved opdatering: {e}")
            else:
                st.session_state.data_refresh_ready = True
                st.session_state.data_refresh_summary = refresh_stats
                st.session_state.data_refresh_timestamp = datetime.now()
                st.session_state.pop("price_data", None)
                st.success("✅ Data opdateret!")
        data_ready = st.session_state.get("data_refresh_ready", False)
    
    if st.session_state.data_refresh_ready:
        summary = st.session_state.data_refresh_summary or {}
        timestamp = st.session_state.data_refresh_timestamp
        if timestamp:
            st.caption(f"Seneste opdatering: {timestamp.strftime('%d-%m-%Y %H:%M')}")
        metrics_cols = st.columns(3)
        metrics_cols[0].metric("Kategorier", summary.get("total_categories", 0))
        metrics_cols[1].metric("Kategorier m. produkter", summary.get("categories_with_products", 0))
        metrics_cols[2].metric("Produkter", summary.get("total_products", 0))
        st.caption(f"Pris-cache produkter: {summary.get('total_products_with_prices', 0)}")
    else:
        st.warning("Kør 'Hent nyeste data' før du bruger de øvrige faner.")
    
    data_ready = st.session_state.get("data_refresh_ready", False)
    st.divider()
    st.subheader("Trin 1: Upload CSV-fil")
    
    uploaded_file = st.file_uploader(
        "Vælg en CSV-fil med produkter",
        type=['csv'],
        help="CSV-fil skal have mindst disse kolonner: PROD_NUM, PROD_NAME, PROD_LEVERANDOR"
    )
    
    if uploaded_file:
        # Save uploaded file
        file_path = DATA_INPUT / uploaded_file.name
        with open(file_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())
        
        st.success(f"✅ Fil uploadet: `{uploaded_file.name}`")
        
        # Preview
        try:
            df = pd.read_csv(file_path)
            st.info(f"📊 **{len(df)} produkter** i filen")
            with st.expander("Vis forhåndsvisning"):
                st.dataframe(df, width='stretch')
        except Exception as e:
            st.error(f"Could not read CSV: {e}")
    
    st.divider()
    st.subheader("Trin 2: Vælg Kørselsmodus")
    
    mode = st.radio(
        "Vælg pipeline tilgang:",
        ["🔄 Kør alle trin (fra CSV → AI)", "🎯 Kør individuel trin"],
        horizontal=True
    )
    
    if mode == "🔄 Kør alle trin (fra CSV → AI)":
        # Full pipeline - CSV through all 5 steps
        st.write("**Køres i rækkefølge:** Sanitize → Scrape+Images → Process Images → Kategorisering → AI Enrichment")
        
        if st.button("▶️ Kør Alle Trin", width='stretch', key="run_all_steps"):
            st.info("⏳ Starter pipeline... (dette tager nogle minutter)")
            try:
                result = subprocess.run(
                    [sys.executable, str(SCRIPTS_DIR / "run_all.py"), "--stop-after", "3.5"],
                    cwd=str(PROJECT_ROOT),
                    capture_output=True,
                    text=True,
                    timeout=1800
                )
                if result.returncode == 0:
                    # Mark all steps as completed
                    st.session_state.pipeline_status = {
                        "Step 1 (Sanitize)": True,
                        "Step 2 (Scrape)": True,
                        "Step 3 (Images)": True,
                        "Step 3.5 (Kategorisering)": True,
                        "Step 4 (AI)": True,
                    }
                    st.session_state.last_pipeline_run = datetime.now()
                    st.success("✅ Pipeline fuldført! Alle trin afsluttet.")
                    
                    # Display cost information
                    cost_file = DATA_OUTPUT / "ai_costs.json"
                    if cost_file.exists():
                        try:
                            with open(cost_file, 'r', encoding='utf-8') as f:
                                cost_data = json.load(f)
                            
                            st.divider()
                            st.subheader("💰 AI API Omkostninger")
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.metric(
                                    "Samlet omkostning",
                                    f"${cost_data.get('total_cost_usd', 0.0):.6f}",
                                    help="Samlet AI API omkostning for alle produkter"
                                )
                            
                            with col2:
                                products_processed = cost_data.get('products_processed', 0)
                                if products_processed > 0:
                                    cost_per_product = cost_data.get('total_cost_usd', 0.0) / products_processed
                                    st.metric(
                                        "Omkostning pr. produkt",
                                        f"${cost_per_product:.8f}",
                                        help="Gennemsnitlig omkostning per behandlet produkt"
                                    )
                                else:
                                    st.metric("Omkostning pr. produkt", "$0.00000000")
                            
                            # Show costs by model
                            cost_by_model = cost_data.get('cost_by_model', {})
                            if cost_by_model:
                                st.markdown("#### Omkostning pr. model:")
                                for model, cost in cost_by_model.items():
                                    st.write(f"- **{model}**: ${cost:.6f}")
                        except Exception as e:
                            st.warning(f"Kunne ikke læse omkostningsdata: {e}")
                else:
                    error_msg = result.stderr if result.stderr else result.stdout
                    if not error_msg:
                        error_msg = "Ukendt fejl (ingen output)"
                    
                    st.error(f"❌ Fejl (exit code {result.returncode})")
                    # Show last 2000 chars to ensure we see the actual error
                    display_msg = error_msg[-2000:] if len(error_msg) > 2000 else error_msg
                    st.code(display_msg, language="text")
            except subprocess.TimeoutExpired:
                st.error("❌ Fejl: Pipeline timeout (over 30 minutter)")
            except Exception as e:
                error_safe = str(e).encode('ascii', errors='replace').decode('ascii')
                st.error(f"❌ Fejl: {error_safe}")
    
    else:
        # Individual step mode with file selection
        st.write("**Vælg trin og input fil:**")
        
        col_step, col_input = st.columns([1, 2])
        
        with col_step:
            step_choice = st.radio(
                "Trin:",
                ["Step 1: Sanitize", "Step 2+3: Scrape & Process", "Step 3.5: Kategorisering", "Step 4: AI Enrichment", "Step 5: Upload til Web"],
                key="step_choice"
            )
        
        with col_input:
            st.write("**Vælg input fil:**")
            
            if step_choice == "Step 1: Sanitize":
                st.write("*Input: CSV-fil fra upload ovenfor*")
                input_files = list(DATA_INPUT.glob("*.csv"))
                if input_files:
                    selected_file = st.selectbox(
                        "CSV-fil:",
                        [f.name for f in input_files],
                        key="input_csv"
                    )
                    if st.button("▶️ Kør Step 1 (Sanitize)", width='stretch', key="run_s1"):
                        st.info(f"⏳ Kører Step 1 med `{selected_file}`...")
                        try:
                            full_path = DATA_INPUT / selected_file
                            result = subprocess.run(
                                [sys.executable, str(SCRIPTS_DIR / "1_sanitize.py"), str(full_path)],
                                cwd=str(PROJECT_ROOT),
                                capture_output=True,
                                text=True,
                                timeout=300
                            )
                            if result.returncode == 0:
                                st.session_state.pipeline_status["Step 1 (Sanitize)"] = True
                                st.success("✅ Step 1 fuldført!")
                            else:
                                error_msg = result.stderr if result.stderr else result.stdout
                                if not error_msg:
                                    error_msg = "Ukendt fejl (ingen output)"
                                
                                st.error(f"❌ Fejl (exit code {result.returncode})")
                                display_msg = error_msg[-2000:] if len(error_msg) > 2000 else error_msg
                                st.code(display_msg, language="text")
                        except Exception as e:
                            error_safe = str(e).encode('ascii', errors='replace').decode('ascii')
                            st.error(f"❌ Fejl: {error_safe}")
                else:
                    st.warning("Ingen CSV-fil fundet i upload. Upload en CSV først.")
            
            elif step_choice == "Step 2+3: Scrape & Process":
                st.write("*Input: Saniteret CSV fra Step 1*")
                input_files = list(DATA_OUTPUT.glob("*_sanitized.csv"))
                if input_files:
                    st.info("📝 Vil køre Step 2 (Scraping) og Step 3 (Image Processing)")
                    if st.button("▶️ Kør Step 2+3 (Scrape & Process)", width='stretch', key="run_s23"):
                        st.info(f"⏳ Kører Step 2+3...")
                        try:
                            # Run step 2 and 3 only (not step 1)
                            result = subprocess.run(
                                [sys.executable, str(SCRIPTS_DIR / "run_steps_2_and_3.py")],
                                cwd=str(PROJECT_ROOT),
                                capture_output=True,
                                text=True,
                                timeout=900
                            )
                            if result.returncode == 0:
                                st.session_state.pipeline_status["Step 2 (Scrape)"] = True
                                st.session_state.pipeline_status["Step 3 (Images)"] = True
                                st.success("✅ Step 2+3 fuldført!")
                            else:
                                error_msg = result.stderr if result.stderr else result.stdout
                                if not error_msg:
                                    error_msg = "Ukendt fejl (ingen output)"
                                
                                st.error(f"❌ Fejl (exit code {result.returncode})")
                                display_msg = error_msg[-2000:] if len(error_msg) > 2000 else error_msg
                                st.code(display_msg, language="text")
                        except Exception as e:
                            error_safe = str(e).encode('ascii', errors='replace').decode('ascii')
                            st.error(f"❌ Fejl: {error_safe}")
                else:
                    st.warning("Ingen saniteret CSV fundet. Kør Step 1 først.")
            
            elif step_choice == "Step 3.5: Kategorisering":
                st.write("*Input: JSON-fil med produkter (fra Step 3)*")
                input_files = list(DATA_OUTPUT.glob("enriched_products.json"))
                if input_files:
                    st.info("📝 Anvender AI til at kategorisere produkter ud fra eksisterende kategorier")
                    if st.button("▶️ Kør Step 3.5 (Kategorisering)", width='stretch', key="run_s35"):
                        st.info(f"⏳ Kører Step 3.5 (Kategorisering)...")
                        try:
                            result = subprocess.run(
                                [sys.executable, str(SCRIPTS_DIR / "3.5_categorize.py")],
                                cwd=str(PROJECT_ROOT),
                                capture_output=True,
                                text=True,
                                timeout=600
                            )
                            if result.returncode == 0:
                                st.session_state.pipeline_status["Step 3.5 (Kategorisering)"] = True
                                st.success("✅ Step 3.5 fuldført!")
                                
                                # Display cost information
                                cost_file = DATA_OUTPUT / "ai_costs.json"
                                if cost_file.exists():
                                    try:
                                        with open(cost_file, 'r', encoding='utf-8') as f:
                                            cost_data = json.load(f)
                                        
                                        st.divider()
                                        st.subheader("💰 AI API Omkostninger (Step 3.5)")
                                        
                                        col1, col2 = st.columns(2)
                                        with col1:
                                            st.metric(
                                                "Samlet omkostning",
                                                f"${cost_data.get('total_cost_usd', 0.0):.6f}",
                                                help="Samlet AI API omkostning for alle produkter"
                                            )
                                        
                                        with col2:
                                            products_processed = cost_data.get('products_processed', 0)
                                            if products_processed > 0:
                                                cost_per_product = cost_data.get('total_cost_usd', 0.0) / products_processed
                                                st.metric(
                                                    "Omkostning pr. produkt",
                                                    f"${cost_per_product:.8f}",
                                                    help="Gennemsnitlig omkostning per behandlet produkt"
                                                )
                                            else:
                                                st.metric("Omkostning pr. produkt", "$0.00000000")
                                        
                                        # Show costs by model
                                        cost_by_model = cost_data.get('cost_by_model', {})
                                        if cost_by_model:
                                            st.markdown("#### Omkostning pr. model:")
                                            for model, cost in cost_by_model.items():
                                                st.write(f"- **{model}**: ${cost:.6f}")
                                    except Exception as e:
                                        st.warning(f"Kunne ikke læse omkostningsdata: {e}")
                            else:
                                error_msg = result.stderr if result.stderr else result.stdout
                                if not error_msg:
                                    error_msg = "Ukendt fejl (ingen output)"
                                
                                st.error(f"❌ Fejl (exit code {result.returncode})")
                                display_msg = error_msg[-2000:] if len(error_msg) > 2000 else error_msg
                                st.code(display_msg, language="text")
                        except Exception as e:
                            error_safe = str(e).encode('ascii', errors='replace').decode('ascii')
                            st.error(f"❌ Fejl: {error_safe}")
                else:
                    st.warning("Ingen produkter fundet. Kør Step 2+3 først.")
            
            elif step_choice == "Step 4: AI Enrichment":
                # Always use categorized_products.json
                categorized_file = DATA_OUTPUT / "categorized_products.json"
                if categorized_file.exists():
                    st.info(f"📄 *Input: {categorized_file.name}*")
                    
                    if st.button("▶️ Kør Step 4 (AI Enrichment)", width='stretch', key="run_s4"):
                        st.info(f"⏳ Kører Step 4 med `{categorized_file.name}`...")
                        try:
                            result = subprocess.run(
                                [sys.executable, str(SCRIPTS_DIR / "4_generate_ai.py"), str(categorized_file)],
                                cwd=str(PROJECT_ROOT),
                                capture_output=True,
                                text=True,
                                timeout=600
                            )
                            if result.returncode == 0:
                                st.session_state.pipeline_status["Step 4 (AI)"] = True
                                st.success("✅ Step 4 fuldført!")
                                
                                # Display cost information
                                cost_file = DATA_OUTPUT / "ai_costs.json"
                                if cost_file.exists():
                                    try:
                                        with open(cost_file, 'r', encoding='utf-8') as f:
                                            cost_data = json.load(f)
                                        
                                        st.divider()
                                        st.subheader("💰 AI API Omkostninger (Step 4)")
                                        
                                        col1, col2 = st.columns(2)
                                        with col1:
                                            st.metric(
                                                "Samlet omkostning",
                                                f"${cost_data.get('total_cost_usd', 0.0):.6f}",
                                                help="Samlet AI API omkostning for alle produkter"
                                            )
                                        
                                        with col2:
                                            products_processed = cost_data.get('products_processed', 0)
                                            if products_processed > 0:
                                                cost_per_product = cost_data.get('total_cost_usd', 0.0) / products_processed
                                                st.metric(
                                                    "Omkostning pr. produkt",
                                                    f"${cost_per_product:.8f}",
                                                    help="Gennemsnitlig omkostning per behandlet produkt"
                                                )
                                            else:
                                                st.metric("Omkostning pr. produkt", "$0.00000000")
                                        
                                        # Show costs by model
                                        cost_by_model = cost_data.get('cost_by_model', {})
                                        if cost_by_model:
                                            st.markdown("#### Omkostning pr. model:")
                                            for model, cost in cost_by_model.items():
                                                st.write(f"- **{model}**: ${cost:.6f}")
                                    except Exception as e:
                                        st.warning(f"Kunne ikke læse omkostningsdata: {e}")
                            else:
                                error_msg = result.stderr if result.stderr else result.stdout
                                if not error_msg:
                                    error_msg = "Ukendt fejl (ingen output)"
                                
                                st.error(f"❌ Fejl (exit code {result.returncode})")
                                display_msg = error_msg[-2000:] if len(error_msg) > 2000 else error_msg
                                st.code(display_msg, language="text")
                        except Exception as e:
                            error_safe = str(e).encode('ascii', errors='replace').decode('ascii')
                            st.error(f"❌ Fejl: {error_safe}")
                else:
                    st.warning("⚠️ categorized_products.json ikke fundet. Kør Step 3.5 (Kategorisering) først.")
            
            elif step_choice == "Step 5: Upload til Web":
                st.write("*Input: JSON-fil med færdige produkter (fra Step 4)*")
                input_files = list(DATA_OUTPUT.glob("final_products.json"))
                if input_files:
                    st.info("🌐 Upload produkter til Dandomain webshop")
                    st.warning("⚠️ Vigtigt: Sørg for at FTP_USER og FTP_PASSWORD er sat i .env filen!")
                    
                    # Dry run option
                    dry_run = st.checkbox("🔍 Preview mode (dry run - ingen faktiske uploads)", value=True, 
                                         help="Test kørslen uden at uploade noget")
                    
                    button_text = "👁️ Preview Upload" if dry_run else "🚀 Upload til Web"
                    
                    if st.button(button_text, width='stretch', key="run_s5"):
                        mode_text = "Preview" if dry_run else "Upload"
                        st.info(f"⏳ Kører Step 5 ({mode_text})...")
                        try:
                            # Build command
                            cmd = [sys.executable, str(SCRIPTS_DIR / "5_upload_to_cms.py")]
                            if dry_run:
                                cmd.append("--dry-run")
                            
                            result = subprocess.run(
                                cmd,
                                cwd=str(PROJECT_ROOT),
                                capture_output=True,
                                text=True,
                                timeout=600
                            )
                            
                            if result.returncode == 0:
                                if not dry_run:
                                    st.session_state.pipeline_status["Step 5 (Upload)"] = True
                                st.success(f"✅ Step 5 {mode_text} fuldført!")
                                
                                # Display upload results
                                results_file = DATA_OUTPUT / "upload_results.json"
                                if results_file.exists():
                                    try:
                                        with open(results_file, 'r', encoding='utf-8') as f:
                                            upload_results = json.load(f)
                                        
                                        st.divider()
                                        st.subheader("📊 Upload Resultater")
                                        
                                        # Summary metrics
                                        success_count = sum(1 for r in upload_results if r['status'] == 'success')
                                        skipped_count = sum(1 for r in upload_results if r['status'] == 'skipped')
                                        error_count = sum(1 for r in upload_results if r['status'] == 'error')
                                        
                                        col1, col2, col3, col4 = st.columns(4)
                                        with col1:
                                            st.metric("Total", len(upload_results))
                                        with col2:
                                            st.metric("✅ Oprettet", success_count)
                                        with col3:
                                            st.metric("⏭️ Sprunget over", skipped_count, 
                                                     help="Produkter der allerede eksisterer")
                                        with col4:
                                            st.metric("❌ Fejl", error_count)
                                        
                                        # Show details in expanders
                                        if skipped_count > 0:
                                            with st.expander(f"⏭️ Vis {skipped_count} oversprungne produkter"):
                                                for result in upload_results:
                                                    if result['status'] == 'skipped':
                                                        st.info(f"**{result['product_number']}**: {result['message']}")
                                        
                                        if error_count > 0:
                                            with st.expander(f"⚠️ Vis {error_count} fejl"):
                                                for result in upload_results:
                                                    if result['status'] == 'error':
                                                        st.error(f"**{result['product_number']}**: {result['message']}")
                                    
                                    except Exception as e:
                                        st.warning(f"Kunne ikke læse upload resultater: {e}")
                            else:
                                error_msg = result.stderr if result.stderr else result.stdout
                                if not error_msg:
                                    error_msg = "Ukendt fejl (ingen output)"
                                
                                st.error(f"❌ Fejl (exit code {result.returncode})")
                                display_msg = error_msg[-2000:] if len(error_msg) > 2000 else error_msg
                                st.code(display_msg, language="text")
                        except Exception as e:
                            error_safe = str(e).encode('ascii', errors='replace').decode('ascii')
                            st.error(f"❌ Fejl: {error_safe}")
                else:
                    st.warning("Ingen final_products.json fundet. Kør Step 4 først.")
    
    st.divider()
    st.subheader("Pipeline Status")
    
    status = get_process_status()
    for step, completed in status.items():
        status_badge = "✅ Fuldført" if completed else "⏸️ Ikke kørt"
        st.markdown(f"**{step}:** {status_badge}")

if not data_ready:
    with tab2:
        st.warning("Hent nyeste data før du ser resultater.")
        st.caption("Gå til fanen 'Upload & Kør' og tryk på 'Hent nyeste data'.")
    with tab_prices:
        st.warning("Prisstyring kræver frisk data fra Dandomain.")
        st.caption("Kør først 'Hent nyeste data' under Upload & Kør.")
    with tab3:
        st.warning("AI Management kræver opdaterede cache-filer.")
        st.caption("Synkronisér data via 'Hent nyeste data'.")
    with tab4:
        st.warning("Log-visning låses op når data er opdateret.")
        st.caption("Tryk på 'Hent nyeste data' på forsiden for at fortsætte.")
    st.stop()

# ============================================================================
# TAB 2: RESULTS GALLERY
# ============================================================================

with tab2:
    st.subheader("📊 Produktresultater")
    
    # Load final products
    final_products_file = DATA_OUTPUT / "final_products.json"
    
    if not os.path.exists(final_products_file):
        st.warning("❌ Ingen resultater fundet. Kør pipeline først!")
    else:
        try:
            products = load_json_file(final_products_file)
            
            if not products:
                st.warning("❌ Ingen produkter i resultater")
            else:
                # Search
                search = st.text_input("🔍 Søg efter produktnummer eller navn:", "")
                
                # Filter
                filtered_products = products
                if search:
                    filtered_products = [
                        p for p in products
                        if search.lower() in str(p.get('product_number', '')).lower() or
                           search.lower() in str(p.get('DESC_SHORT', '')).lower()
                    ]
                    st.info(f"🔍 Fundet **{len(filtered_products)}** produkter")
                
                # Display products - all at once (infinite scroll via browser native scrolling)
                for idx, product in enumerate(filtered_products):
                    display_product_card(product, show_actions=True, product_index=idx)
                
                st.divider()
                
                # Download Assets as ZIP
                st.divider()
                st.markdown("### 📦 Download Assets")
                
                if st.button("📥 Download Billeder & PDF som ZIP", width='stretch'):
                    try:
                        import zipfile
                        import io
                        
                        # Create in-memory ZIP
                        zip_buffer = io.BytesIO()
                        
                        total_files = 0
                        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                            for product in filtered_products:
                                prod_num = product.get('product_number', '').split(' - ')[0].strip()
                                
                                # 1. Add Images
                                # Get app_images (stored in data/output/images)
                                app_images = product.get('app_images', [])
                                if not app_images:
                                    # Fallback: check if images exist in data/output/images
                                    for img_path in product.get('images', []):
                                        if img_path:
                                            img_name = Path(img_path).name
                                            local_img = DATA_OUTPUT / "images" / img_name
                                            if local_img.exists():
                                                app_images.append(str(local_img))
                                
                                for img_path in app_images:
                                    img_file = Path(img_path)
                                    if img_file.exists():
                                        zip_filename = f"images/{prod_num}_{img_file.name}"
                                        zip_file.write(img_file, zip_filename)
                                        total_files += 1
                                
                                # 2. Add PDF (Datablade)
                                # Look in data/output/pdfs
                                pdf_path = DATA_OUTPUT / "pdfs" / f"{prod_num}.pdf"
                                if pdf_path.exists():
                                    zip_filename = f"datablade/{prod_num}.pdf"
                                    zip_file.write(pdf_path, zip_filename)
                                    total_files += 1
                        
                        if total_files == 0:
                            st.warning("❌ Ingen filer fundet til download")
                        else:
                            zip_buffer.seek(0)
                            
                            # Generate filename with timestamp
                            from datetime import datetime
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            zip_filename = f"produkt_assets_{timestamp}.zip"
                            
                            st.download_button(
                                label=f"⬇️ Download ZIP ({total_files} filer)",
                                data=zip_buffer.getvalue(),
                                file_name=zip_filename,
                                mime="application/zip",
                                width='stretch'
                            )
                            st.success(f"✅ ZIP klar til download med {total_files} filer!")
        
                    except Exception as e:
                        st.error(f"❌ Fejl ved oprettelse af ZIP: {e}")
                
                st.caption("💡 ZIP filen indeholder billeder og datablade (PDF) organiseret i mapper.")
        
        except Exception as e:
            st.error(f"❌ Fejl ved indlæsning af produkter: {e}")

# ============================================================================
# TAB 3: AI MANAGEMENT
# ============================================================================

with tab3:
    st.subheader("⚙️ Indstillinger & AI Management")
    
    # Sub-tabs for different AI management functions
    ai_tab1, ai_tab2, ai_tab3 = st.tabs(["✏️ Prompt Editor", "⭐ Golden Examples", "📂 Stier & Mapper"])
    
    # ========================================================================
    # AI TAB 3: PATHS & FOLDERS
    # ========================================================================
    with ai_tab3:
        st.markdown("### 📂 Konfigurer Stier")
        st.info("Her kan du angive hvor billeder skal gemmes og hentes fra.")
        
        # Load current config
        config_path = PROJECT_ROOT / "config.yaml"
        current_config = {}
        if config_path.exists():
            try:
                import yaml
                with open(config_path, 'r', encoding='utf-8') as f:
                    current_config = yaml.safe_load(f) or {}
            except Exception as e:
                st.error(f"Kunne ikke læse config.yaml: {e}")
        
        paths_config = current_config.get('paths', {})
        current_ext_images = paths_config.get('external_images_dir', '')
        current_orig_images = paths_config.get('original_images_dir', '')
        
        st.markdown("#### Billedmapper (OneDrive)")
        
        new_ext_images = st.text_input(
            "Sti til færdigbehandlede billeder (1500x1500):",
            value=current_ext_images,
            help="F.eks. C:/Users/navn/OneDrive.../Produktbilleder_1500x1500"
        )
        
        new_orig_images = st.text_input(
            "Sti til originale billeder (Scraping output):",
            value=current_orig_images,
            help="F.eks. C:/Users/navn/OneDrive.../original billeder/Produktbilleder"
        )
        
        if st.button("💾 Gem Stier"):
            try:
                # Update config object
                if 'paths' not in current_config:
                    current_config['paths'] = {}
                
                current_config['paths']['external_images_dir'] = new_ext_images
                current_config['paths']['original_images_dir'] = new_orig_images
                
                # Save back to yaml
                with open(config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(current_config, f, default_flow_style=False, allow_unicode=True)
                
                st.success("✅ Stier gemt i config.yaml")
                st.warning("⚠️ Hvis du kører i Docker, skal du genstarte containeren for at ændringerne træder i kraft, ELLER sikre at stierne er mounted korrekt.")
                
            except Exception as e:
                st.error(f"❌ Fejl ved gem: {e}")

    # ========================================================================
    # AI TAB 1: PROMPT EDITOR
    # ========================================================================
    with ai_tab1:
        st.markdown("### Rediger AI Prompts")
        st.info("📝 Rediger system- og brugerprompts der bruges til AI-generering i Step 4")
        
        # Load current prompts from ai_config.py
        ai_config_file = SCRIPTS_DIR / "ai_config.py"
        
        if not os.path.exists(ai_config_file):
            st.error("❌ Kan ikke finde ai_config.py")
        else:
            # Read the file
            with open(ai_config_file, 'r', encoding='utf-8') as f:
                ai_config_content = f.read()
            
            # Extract SYSTEM_PROMPT
            import re
            system_prompt_match = re.search(r'SYSTEM_PROMPT = """(.*?)"""', ai_config_content, re.DOTALL)
            user_prompt_match = re.search(r'USER_PROMPT_TEMPLATE = """(.*?)"""', ai_config_content, re.DOTALL)
            
            current_system_prompt = system_prompt_match.group(1) if system_prompt_match else ""
            current_user_prompt = user_prompt_match.group(1) if user_prompt_match else ""
            
            # Editable text areas
            st.markdown("#### System Prompt")
            st.caption("Denne prompt definerer AI'ens rolle og personlighed")
            new_system_prompt = st.text_area(
                "System Prompt:",
                value=current_system_prompt,
                height=400,
                key="system_prompt_editor",
                label_visibility="collapsed"
            )
            
            st.divider()
            
            st.markdown("#### User Prompt Template")
            st.caption("Denne template bruges til at generere beskrivelser. Brug {product_info} og {example_json} som placeholders.")
            new_user_prompt = st.text_area(
                "User Prompt Template:",
                value=current_user_prompt,
                height=700,
                key="user_prompt_editor",
                label_visibility="collapsed"
            )
            
            st.divider()
            
            # Save button
            col1, col2 = st.columns([1, 3])
            with col1:
                if st.button("💾 Gem Prompts", width='stretch'):
                    try:
                        # Replace prompts in config file
                        new_config = ai_config_content
                        
                        # Replace SYSTEM_PROMPT
                        new_config = re.sub(
                            r'SYSTEM_PROMPT = """.*?"""',
                            f'SYSTEM_PROMPT = """{new_system_prompt}"""',
                            new_config,
                            flags=re.DOTALL
                        )
                        
                        # Replace USER_PROMPT_TEMPLATE
                        new_config = re.sub(
                            r'USER_PROMPT_TEMPLATE = """.*?"""',
                            f'USER_PROMPT_TEMPLATE = """{new_user_prompt}"""',
                            new_config,
                            flags=re.DOTALL
                        )
                        
                        # Write back
                        with open(ai_config_file, 'w', encoding='utf-8') as f:
                            f.write(new_config)
                        
                        st.success("✅ Prompts gemt til ai_config.py!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Fejl ved gem: {e}")
            
            with col2:
                if st.button("🔄 Reset til Original", width='stretch'):
                    st.warning("⚠️ Denne funktion er ikke implementeret endnu. Gem en backup manuelt!")
    
    # ========================================================================
    # AI TAB 2: GOLDEN EXAMPLES
    # ========================================================================
    with ai_tab2:
        st.markdown("### ⭐ Administrer Golden Examples")
        st.info("📌 Vælg bedste eksempler for hver kategori - disse vil blive prioriteret over automatisk valg")
        
        # Load ALL products from API cache
        products_cache_file = PROJECT_ROOT / "cache" / "products_cache.json"
        categories_cache_file = PROJECT_ROOT / "cache" / "categories_cache.json"
        golden_examples_file = DATA_CACHE / "golden_examples.json"
        
        if not os.path.exists(products_cache_file):
            st.warning("❌ Ingen produkter fundet i cache. Kør API sync først.")
        elif not os.path.exists(categories_cache_file):
            st.warning("❌ Ingen kategorier fundet i cache. Kør API sync først.")
        else:
            try:
                # Load all products from API
                all_products = load_json_file(products_cache_file) or []
                all_categories = load_json_file(categories_cache_file) or []
                
                # Load existing golden examples
                golden_examples = load_json_file(golden_examples_file) or {}
                
                # Build category map (category number -> category info)
                # API structure: categories have 'id' (internal) and 'number' (business key)
                # Products reference categories via 'number' in DefaultCategoryId/PrimaryCategoryId
                category_map = {}
                
                for cat in all_categories:
                    cat_number = str(cat.get('number', ''))
                    
                    # Get category name from texts.items[0].name
                    cat_name = 'Unknown'
                    texts = cat.get('texts', {})
                    if isinstance(texts, dict):
                        items = texts.get('items', [])
                        if items and len(items) > 0:
                            cat_name = items[0].get('name', 'Unknown')
                    
                    if cat_number:
                        category_map[cat_number] = {
                            'name': cat_name,
                            'number': cat_number,
                            'product_count': 0
                        }
                
                # Count products per category
                for product in all_products:
                    # Products use category_number in primaryCategoryId
                    primary_cat_num = str(product.get('primaryCategoryId', ''))
                    
                    if primary_cat_num and primary_cat_num in category_map:
                        category_map[primary_cat_num]['product_count'] += 1
                
                # Filter to only categories with products
                categories_with_products = {
                    cat_num: info for cat_num, info in category_map.items()
                    if info['product_count'] > 0
                }
                
                if not categories_with_products:
                    st.warning("❌ Ingen kategorier med produkter fundet")
                else:
                    st.success(f"✓ Fandt {len(categories_with_products)} kategorier med produkter")
                    
                    # Category selector
                    selected_category = st.selectbox(
                        "Vælg kategori:",
                        options=sorted(categories_with_products.keys()),
                        format_func=lambda x: f"{categories_with_products[x]['name']} ({categories_with_products[x]['product_count']} produkter)"
                    )
                    
                    # Get products in this category from ALL API products
                    category_products = [
                        p for p in all_products
                        if str(p.get('primaryCategoryId', '')) == selected_category
                    ]
                    
                    st.info(f"📊 **{len(category_products)} produkter** i denne kategori")
                    
                    if category_products:
                        st.divider()
                        st.markdown(f"#### Produkter i kategori: {categories_with_products[selected_category]['name']}")
                        
                        # Get current golden
                        current_golden_id = golden_examples.get(selected_category)
                        
                        # Display products with option to set as golden
                        for prod in category_products:
                            prod_id = prod.get('id')
                            prod_num = prod.get('number', '')
                            prod_name = extract_product_name(prod)
                            
                            is_golden = (str(prod_id) == str(current_golden_id))
                            
                            col_p1, col_p2 = st.columns([3, 1])
                            with col_p1:
                                st.write(f"**{prod_name}** ({prod_num})")
                            
                            with col_p2:
                                if is_golden:
                                    st.success("⭐ Golden Example")
                                else:
                                    if st.button("Sæt som Golden", key=f"set_golden_{prod_id}"):
                                        golden_examples[selected_category] = prod_id
                                        save_json_file(golden_examples_file, golden_examples)
                                        st.success("Gemt!")
                                        st.rerun()
                        
            except Exception as e:
                st.error(f"Fejl ved indlæsning af golden examples: {e}")

# ============================================================================
# TAB PRICES: PRISSTYRING
# ============================================================================

with tab_prices:
    st.subheader("💰 Prisstyring")
    st.info("Her kan du se og rette priser direkte i Dandomain.")

    # Initialize API Manager
    api = get_api_manager()
    
    # Add prompt for user action
    st.markdown("#### Vælg handling")
    action = st.radio(
        "Hvad vil du gøre?",
        options=["Opret tilbud", "Fjern tilbud"],
        index=0
    )

    previous_action = st.session_state.get("price_active_action")
    if previous_action != action:
        st.session_state.pop("price_data", None)
        st.session_state.pop("price_mode", None)
        st.session_state.pop("price_selection_label", None)
        st.session_state.pop("price_selection_number", None)
    st.session_state["price_active_action"] = action

    if action == "Opret tilbud":
        st.markdown("#### 1. Vælg Kategori")
        categories_cache_file = CATEGORIES_WITH_PRODUCTS_FILE
        all_categories = load_json_file(categories_cache_file) or []

        if not all_categories:
            st.warning("Ingen kategorier fundet. Kør 'Hent nyeste data' under Upload & Kør.")
        else:
            cat_options: List[Tuple[str, str, Any]] = []
            for cat in all_categories:
                cat_number = str(cat.get("number")) if cat.get("number") is not None else ""
                cat_name = cat.get("texts", {}).get("items", [{}])[0].get("name", "Unavngivet")
                cat_id = cat.get("id")
                cat_options.append((cat_number, cat_name, cat_id))

            cat_options.sort(key=lambda option: option[1])

            selected_cat_tuple = st.selectbox(
                "Vælg varekategori:",
                options=cat_options,
                format_func=lambda x: f"{x[1]} ({x[0]})" if x[0] else x[1],
            )

            if selected_cat_tuple:
                selected_cat_number = str(selected_cat_tuple[0])
                selected_cat_name = selected_cat_tuple[1]
                previous_selection = st.session_state.get("price_selection_number")
                previous_mode = st.session_state.get("price_mode")
                if previous_mode == "create" and previous_selection and previous_selection != selected_cat_number:
                    st.session_state.pop("price_data", None)

                if st.button("📥 Hent Produkter & Priser", type="primary", key="fetch_offer_create"):
                    with st.spinner(f"Henter produkter for {selected_cat_name}..."):
                        all_products = api.get_all_products(include_prices=True, include_categories=True)
                        matching_rows: List[Dict[str, Any]] = []
                        skipped_numbers: List[str] = []

                        for product in all_products:
                            categories_for_product = extract_category_numbers(product)
                            if selected_cat_number in categories_for_product:
                                row = build_price_row(product)
                                if row:
                                    matching_rows.append(row)
                                else:
                                    skipped_numbers.append(str(product.get("number", "")))

                        df = normalize_price_dataframe(pd.DataFrame(matching_rows))

                        if df.empty:
                            st.session_state.pop("price_data", None)
                            st.warning(f"Ingen produkter fundet i kategorien {selected_cat_name}.")
                        else:
                            st.session_state.price_data = df
                            st.session_state.price_mode = "create"
                            st.session_state.price_selection_label = selected_cat_name
                            st.session_state.price_selection_number = selected_cat_number
                            st.success(f"{len(df)} produkter fundet i kategorien {selected_cat_name}.")

                        if skipped_numbers:
                            preview = ", ".join([num for num in skipped_numbers if num][:5])
                            if preview:
                                if len(skipped_numbers) > 5:
                                    preview += ", ..."
                                st.info(f"Springede {len(skipped_numbers)} produkter over uden standardpris: {preview}")

    elif action == "Fjern tilbud":
        st.markdown("#### 1. Produkter i tilbudskategori")

        if st.button("📥 Hent Produkter & Priser", type="primary", key="fetch_offer_remove"):
            with st.spinner("Henter produkter fra tilbudskategorien..."):
                all_products = api.get_all_products(include_prices=True, include_categories=True)
                matching_rows: List[Dict[str, Any]] = []
                skipped_numbers: List[str] = []

                for product in all_products:
                    categories_for_product = extract_category_numbers(product)
                    if OFFER_CATEGORY_NUMBER in categories_for_product:
                        row = build_price_row(product, mark_for_update=True)
                        if row:
                            matching_rows.append(row)
                        else:
                            skipped_numbers.append(str(product.get("number", "")))

                df = normalize_price_dataframe(pd.DataFrame(matching_rows))

                if df.empty:
                    st.session_state.pop("price_data", None)
                    st.warning("Ingen produkter fundet i tilbudskategorien.")
                else:
                    df["Opdater"] = True
                    st.session_state.price_data = df
                    st.session_state.price_mode = "remove"
                    st.session_state.price_selection_label = f"TILBUD ({OFFER_CATEGORY_NUMBER})"
                    st.session_state.price_selection_number = OFFER_CATEGORY_NUMBER
                    st.success(f"{len(df)} produkter fundet i tilbudskategorien.")

                if skipped_numbers:
                    preview = ", ".join([num for num in skipped_numbers if num][:5])
                    if preview:
                        if len(skipped_numbers) > 5:
                            preview += ", ..."
                        st.info(f"Springede {len(skipped_numbers)} produkter over uden standardpris: {preview}")

        if st.session_state.get("price_mode") == "remove" and st.session_state.get("price_data") is not None:
            st.caption("Alle produkter er markeret til opdatering som udgangspunkt.")

    # 2. Edit Prices
    if "price_data" in st.session_state and not st.session_state.price_data.empty:
        st.divider()
        st.markdown("#### 2. Rediger Priser")

        st.session_state.price_data = normalize_price_dataframe(st.session_state.price_data.copy())
        active_mode = st.session_state.get("price_mode", "create")
        selection_label = st.session_state.get("price_selection_label")
        if selection_label:
            st.caption(f"Data fra: {selection_label}")

        col_check_all, col_uncheck_all = st.columns(2)
        with col_check_all:
            if st.button("✅ Markér alle", key="mark_all"):
                df = st.session_state.price_data.copy()
                df["Opdater"] = True
                st.session_state.price_data = df
                st.rerun()
        with col_uncheck_all:
            if st.button("🚫 Fjern markering", key="unmark_all"):
                df = st.session_state.price_data.copy()
                df["Opdater"] = False
                st.session_state.price_data = df
                st.rerun()
        
        # Bulk Actions
        with st.expander("🛠️ Masseopdatering"):
            col_bulk1, col_bulk2 = st.columns(2)
            with col_bulk1:
                target_margin = st.number_input(
                    "Sæt ønsket margin % for alle:",
                    min_value=0.0,
                    max_value=99.9,
                    value=30.0,
                    step=0.1
                )
                if st.button("Beregn priser ud fra margin"):
                    df = st.session_state.price_data.copy()
                    df["Ny Tilbudspris"] = df.apply(
                        lambda row: calculate_price_from_margin(row.get("_cost_price", 0.0), target_margin),
                        axis=1
                    )
                    df["Ny Margin %"] = df.apply(
                        lambda row: compute_margin_pct(row.get("_cost_price", 0.0), row.get("Ny Tilbudspris")),
                        axis=1
                    )
                    df["Besparelse %"] = df.apply(
                        lambda row: compute_savings_pct(row.get("Nuværende Pris", 0.0), row.get("Ny Tilbudspris", 0.0)),
                        axis=1
                    )
                    df["Opdater"] = True
                    st.session_state.price_data = df
                    st.rerun()
            
            with col_bulk2:
                st.info("Du kan også rette manuelt i tabellen nedenfor.")
        
        # Data Editor (display-only columns)
        display_columns = [
            "Billede",
            "Varenummer",
            "Produktnavn",
            "Tilbud Label",
            "Kostpris",
            "Nuværende Pris",
            "Ny Tilbudspris",
            "Ny Margin %",
            "Besparelse %",
            "Opdater",
        ]

        edited_df = st.data_editor(
            st.session_state.price_data[display_columns],
            column_config={
                "Billede": st.column_config.ImageColumn("Billede", help="Produktbillede", width="large"),
                "Varenummer": st.column_config.TextColumn(disabled=True),
                "Produktnavn": st.column_config.TextColumn(disabled=True),
                "Kostpris": st.column_config.NumberColumn(format="%.2f kr", disabled=True),
                "Nuværende Pris": st.column_config.NumberColumn(format="%.2f kr", disabled=True),
                "Ny Tilbudspris": st.column_config.NumberColumn(format="%.2f kr"),
                "Ny Margin %": st.column_config.NumberColumn(format="%.1f %%", disabled=True),
                "Besparelse %": st.column_config.NumberColumn(format="%.1f %%", disabled=True),
                "Tilbud Label": st.column_config.TextColumn(disabled=True),
                "Opdater": st.column_config.CheckboxColumn("Opdater?", help="Marker produkter der skal have opdateret tilbud"),
            },
            column_order=display_columns,
            hide_index=True,
            width='stretch',
            key="price_editor",
        )

        if not edited_df.empty:
            # Persist user edits back to master dataframe
            for column in display_columns:
                st.session_state.price_data[column] = edited_df[column]

        # Normalize values and recompute savings
        st.session_state.price_data["Ny Tilbudspris"] = st.session_state.price_data["Ny Tilbudspris"].apply(coerce_price_value)
        st.session_state.price_data["Besparelse %"] = st.session_state.price_data.apply(
            lambda row: compute_savings_pct(row.get("Nuværende Pris", 0.0), row.get("Ny Tilbudspris", 0.0)),
            axis=1,
        )
        st.session_state.price_data["Ny Margin %"] = st.session_state.price_data.apply(
            lambda row: compute_margin_pct(row.get("_cost_price", 0.0), row.get("Ny Tilbudspris")),
            axis=1,
        )

        # 3. Offer Actions
        st.divider()
        st.markdown("#### 3. Opret eller fjern tilbud")

        to_update = st.session_state.price_data[st.session_state.price_data["Opdater"] == True]
        count = len(to_update)

        if count == 0:
            st.info("Ingen produkter markeret. Sæt kryds i 'Opdater?' for de produkter du vil ændre.")
        else:
            st.warning(f"⚠️ Du er ved at opdatere tilbud på {count} produkter.")

            def process_offers(action: str) -> None:
                progress_bar = st.progress(0.0)
                status_text = st.empty()
                df = st.session_state.price_data.copy()
                successes: List[str] = []
                failures: List[Tuple[str, str]] = []

                for i, (index, row) in enumerate(to_update.iterrows()):
                    prod_num = str(row.get("Varenummer"))
                    status_text.text(f"Behandler {prod_num}...")
                    new_price = coerce_price_value(row.get("Ny Tilbudspris"))

                    if action == "create" and (new_price is None or new_price <= 0):
                        failures.append((prod_num, "Mangler gyldig tilbudspris"))
                        progress_bar.progress((i + 1) / count)
                        continue

                    try:
                        product_details = api.get_product(
                            prod_num,
                            include_settings=True,
                            include_prices=True,
                            include_categories=True,
                        )
                    except Exception as exc:
                        failures.append((prod_num, f"API-fejl: {exc}"))
                        progress_bar.progress((i + 1) / count)
                        continue

                    success_flag, message, context = execute_offer_action(
                        api,
                        product_details,
                        action,
                        new_price,
                    )

                    if success_flag:
                        successes.append(prod_num)
                        df.loc[index, "Opdater"] = False

                        if action == "create" and new_price is not None:
                            df.loc[index, "Ny Tilbudspris"] = new_price
                            df.loc[index, "Besparelse %"] = compute_savings_pct(
                                df.loc[index, "Nuværende Pris"],
                                new_price,
                            )
                            df.loc[index, "Ny Margin %"] = compute_margin_pct(
                                df.loc[index, "_cost_price"],
                                new_price,
                            )
                            df.loc[index, "Tilbud Label"] = "Tilbud"
                            df.loc[index, "_custom_field3"] = "Tilbud"
                        elif action == "remove":
                            df.loc[index, "Ny Tilbudspris"] = df.loc[index, "Nuværende Pris"]
                            df.loc[index, "Besparelse %"] = 0.0
                            df.loc[index, "Ny Margin %"] = compute_margin_pct(
                                df.loc[index, "_cost_price"],
                                df.loc[index, "Nuværende Pris"],
                            )
                            df.loc[index, "Tilbud Label"] = ""
                            df.loc[index, "_custom_field3"] = ""

                        if context:
                            if "categories" in context:
                                df.loc[index, "_category_numbers"] = context["categories"]
                            if "price_entry" in context:
                                df.loc[index, "_price_payload"] = context["price_entry"]
                    else:
                        failures.append((prod_num, message or "Ukendt fejl"))

                    progress_bar.progress((i + 1) / count)

                progress_bar.empty()
                status_text.empty()
                st.session_state.price_data = df

                if successes:
                    preview = ", ".join(successes[:5])
                    if len(successes) > 5:
                        preview += ", ..."
                    if action == "create":
                        st.success(f"Tilbud oprettet for {len(successes)} produkter ({preview})")
                    else:
                        st.success(f"Tilbud fjernet for {len(successes)} produkter ({preview})")

                if failures:
                    failure_preview = "; ".join([f"{num}: {msg}" for num, msg in failures[:5]])
                    if len(failures) > 5:
                        failure_preview += "; ..."
                    st.error(
                        f"Fejl under tilbudsopdatering for {len(failures)} produkter: {failure_preview}"
                    )

            if active_mode == "create":
                st.caption("Valgte produkter får oprettet tilbudspris, Tilbud-label og tilbudskategori.")
            else:
                st.caption("Valgte produkter får fjernet tilbudspris, label og kategori.")

            if st.button("🚀 Send til CMS (Dandomain)", type="primary"):
                process_offers(active_mode)
