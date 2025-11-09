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
import pandas as pd
from PIL import Image
import time
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
DATA_INPUT = PROJECT_ROOT / "data" / "input"
DATA_OUTPUT = PROJECT_ROOT / "data" / "output"
LOGS_DIR = PROJECT_ROOT / "logs"
DATA_CACHE = PROJECT_ROOT / "data" / "cache"
CACHE_DIR = PROJECT_ROOT / "cache"

# Add scripts to path for imports
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(PROJECT_ROOT))

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

# Initialize session state for tracking pipeline execution
if "pipeline_status" not in st.session_state:
    st.session_state.pipeline_status = {
        "Step 1 (Sanitize)": False,
        "Step 2 (Scrape)": False,
        "Step 3 (Images)": False,
        "Step 3.5 (Kategorisering)": False,
        "Step 4 (AI)": False,
    }
if "last_pipeline_run" not in st.session_state:
    st.session_state.last_pipeline_run = None

# Light theme CSS - Clean, minimal design inspired by client's product page
st.markdown("""
<style>
    :root {
        --bg-primary: #ffffff;
        --bg-secondary: #f8f8f8;
        --text-primary: #1a1a1a;
        --text-secondary: #666666;
        --text-light: #999999;
        --border-color: #e0e0e0;
        --accent-color: #0066cc;
        --accent-dark: #0052a3;
        --accent-light: #e8f0ff;
        --shadow-light: 0 1px 3px rgba(0, 0, 0, 0.08);
        --shadow-hover: 0 2px 8px rgba(0, 0, 0, 0.12);
    }
    
    @media (prefers-color-scheme: dark) {
        :root {
            --bg-primary: #1e1e1e;
            --bg-secondary: #2a2a2a;
            --text-primary: #ffffff;
            --text-secondary: #b0b0b0;
            --text-light: #888888;
            --border-color: #404040;
            --accent-color: #4a9eff;
            --accent-dark: #357abd;
            --accent-light: #1a3a52;
            --shadow-light: 0 1px 3px rgba(0, 0, 0, 0.3);
            --shadow-hover: 0 2px 8px rgba(0, 0, 0, 0.5);
        }
    }
    
    /* Global background */
    .main {
        background: var(--bg-primary);
    }
    
    /* Header styling */
    .main-header {
        color: var(--text-primary);
        background: var(--bg-primary);
        border-bottom: 2px solid var(--border-color);
        padding: 30px 20px;
        margin: -20px -20px 20px -20px;
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 2.2em;
        color: var(--text-primary);
        font-weight: 700;
    }
    
    .main-header p {
        margin: 5px 0 0 0;
        color: var(--text-secondary);
        font-size: 0.95em;
    }
    
    /* Product cards - inspired by client design */
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
    
    /* Column styling inside product card */
    .stColumn {
        display: flex;
        align-items: center;
    }
    
    /* Image container - max size constraint */
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
    
    /* Product details */
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
    
    /* Step cards */
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
    
    /* Tabs styling */
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
    
    /* Buttons */
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
    
    /* Expanders */
    .streamlit-expanderHeader {
        background: var(--bg-secondary);
        border: 1px solid var(--border-color);
        color: var(--text-primary);
    }
    
    /* Metric display */
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
    
    /* Text elements */
    body, p, span, div {
        color: var(--text-primary);
    }
    
    /* Input elements */
    .stTextInput input,
    .stSelectbox select,
    .stNumberInput input {
        background: var(--bg-secondary);
        color: var(--text-primary);
        border: 1px solid var(--border-color);
    }
</style>
""", unsafe_allow_html=True)

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
        
        # Load categories - use CACHE_DIR constant defined at top of file
        categories_cache_file = CACHE_DIR / "categories_cache.json"
        products_cache_file = CACHE_DIR / "products_cache.json"
        
        # Debug: Check if file exists
        if not categories_cache_file.exists():
            st.error(f"⚠️ Categories cache file not found at: {categories_cache_file}")
            st.info(f"🔍 Tried path: {categories_cache_file.absolute()}")
            all_categories = []
        else:
            all_categories = load_json_file(categories_cache_file)
            if not all_categories:
                st.warning(f"⚠️ Categories cache file is empty or failed to load")
            else:
                # Filter to only categories with products (like in Step 3.5)
                if products_cache_file.exists():
                    api_products = load_json_file(products_cache_file) or []
                    
                    # Build set of category IDs that have products
                    category_ids_with_products = set()
                    for product_item in api_products:
                        # Products reference categories by 'number' field as primaryCategoryId
                        primary_cat_number = product_item.get('primaryCategoryId', '')
                        default_cat_number = product_item.get('defaultCategoryId', '')
                        
                        # Find the category ID from the number
                        for cat in all_categories:
                            cat_number = cat.get('number', '')
                            if cat_number and (cat_number == primary_cat_number or cat_number == default_cat_number):
                                category_ids_with_products.add(cat.get('id'))
                    
                    # Filter categories to only those with products
                    categories_with_products = [
                        cat for cat in all_categories 
                        if cat.get('id') in category_ids_with_products
                    ]
                    
                    all_categories = categories_with_products
                    st.success(f"✅ Loaded {len(all_categories)} categories with products (filtered from {len(load_json_file(categories_cache_file))} total)")
                else:
                    st.success(f"✅ Loaded {len(all_categories)} categories from cache")
        
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
            
            # Debug: Show what we're looking for
            primary_cat_id_value = product.get('primaryCategoryId', 'None')
            
            # If no ai_categorization.category_id, try to get from primaryCategoryId
            if not current_cat_id and product.get('primaryCategoryId'):
                primary_cat_number = product.get('primaryCategoryId')
                current_cat_id = category_number_to_id.get(primary_cat_number) or category_number_to_id.get(str(primary_cat_number))
                if current_cat_id:
                    st.info(f"🔍 Found category via primaryCategoryId: {primary_cat_number} → ID {current_cat_id}")
            
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
                st.markdown(f'<div class="product-description"><strong>Meta beskrivelse:</strong><br/>{product.get("META_DESCRIPTION", "")}</div>', 
                           unsafe_allow_html=True)
        
        # Action buttons (if enabled)
        if show_actions and product_index is not None:
            st.divider()
            approved = product.get('approved_example')
            
            col_status, col_approve, col_regen = st.columns([2, 1, 1])
            
            with col_status:
                if approved == True:
                    st.success("✅ Godkendt eksempel")
                else:
                    st.info("⏸️ Ikke godkendt")
            
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
                            desc_short=edited_short,
                            desc_long=edited_long,
                            searchwords=edited_search,
                            meta_desc=edited_meta
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
tab1, tab2, tab3, tab4 = st.tabs(["📤 Upload & Kør", "📊 Resultater", "🤖 AI Management", "📋 Logs"])

# ============================================================================
# TAB 1: UPLOAD & EXECUTE
# ============================================================================

with tab1:
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
                    error_msg = result.stderr or result.stdout or "Ukendt fejl"
                    error_safe = error_msg.encode('ascii', errors='replace').decode('ascii')
                    st.error(f"❌ Fejl (exit code {result.returncode}): {error_safe[:500]}")
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
                                error_msg = result.stderr or result.stdout or "Ukendt fejl"
                                error_safe = error_msg.encode('ascii', errors='replace').decode('ascii')
                                st.error(f"❌ Fejl: {error_safe[:500]}")
                        except Exception as e:
                            error_safe = str(e).encode('ascii', errors='replace').decode('ascii')
                            st.error(f"❌ Fejl: {error_safe}")
                else:
                    st.warning("Ingen CSV-fil fundet i upload. Upload en CSV først.")
            
            elif step_choice == "Step 2+3: Scrape & Process":
                st.write("*Input: Saniteret CSV fra Step 1*")
                input_files = list(DATA_OUTPUT.glob("*_sanitized.csv"))
                if input_files:
                    selected_file = st.selectbox(
                        "Saniteret CSV:",
                        [f.name for f in input_files],
                        key="input_sanitized"
                    )
                    if st.button("▶️ Kør Step 2+3 (Scrape & Process)", width='stretch', key="run_s23"):
                        st.info(f"⏳ Kører Step 2+3...")
                        try:
                            # Run step 2 and 3
                            result = subprocess.run(
                                [sys.executable, str(SCRIPTS_DIR / "run_all.py"), "--stop-after", "3"],
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
                                error_msg = result.stderr or result.stdout or "Ukendt fejl"
                                error_safe = error_msg.encode('ascii', errors='replace').decode('ascii')
                                st.error(f"❌ Fejl: {error_safe[:500]}")
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
                                error_msg = result.stderr or result.stdout or "Ukendt fejl"
                                error_safe = error_msg.encode('ascii', errors='replace').decode('ascii')
                                st.error(f"❌ Fejl: {error_safe[:500]}")
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
                                error_msg = result.stderr or result.stdout or "Ukendt fejl"
                                error_safe = error_msg.encode('ascii', errors='replace').decode('ascii')
                                st.error(f"❌ Fejl: {error_safe[:500]}")
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
                                error_msg = result.stderr or result.stdout or "Ukendt fejl"
                                error_safe = error_msg.encode('ascii', errors='replace').decode('ascii')
                                st.error(f"❌ Fejl: {error_safe[:500]}")
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
                
                # Export buttons removed per user request - not useful for workflow
        
        except Exception as e:
            st.error(f"❌ Fejl ved indlæsning af produkter: {e}")

# ============================================================================
# TAB 4: LOGS
# ============================================================================

with tab4:
    st.subheader("📋 Logs")
    
    # Only show main pipeline step logs (not job logs or other debug logs)
    log_dir = Path(LOGS_DIR)
    main_logs = [
        "1_sanitize.log",
        "2_scrape.log", 
        "3_process_images.log",
        "3.5_categorize.log",
        "4_generate_ai.log"
    ]
    
    # Get existing log files in reverse order (newest operations last in list means newest step at top)
    available_logs = []
    for log_name in reversed(main_logs):  # Reverse so Step 4 shows first
        log_path = log_dir / log_name
        if log_path.exists():
            available_logs.append(log_path)
    
    if available_logs:
        selected_log = st.selectbox(
            "Vælg logfil:",
            available_logs,
            format_func=lambda x: f"{x.name} ({x.stat().st_size // 1024} KB)"
        )
        
        # Read log and reverse lines to show newest first
        with open(selected_log, 'r', encoding='utf-8', errors='ignore') as f:
            log_content_lines = f.readlines()
        
        # Reverse to show newest entries at top
        log_content_reversed = ''.join(reversed(log_content_lines))
        log_content = ''.join(log_content_lines)  # Keep original for download
        
        # Statistics
        errors = sum(1 for line in log_content_lines if 'ERROR' in line or 'error' in line)
        warnings = sum(1 for line in log_content_lines if 'WARNING' in line or 'warning' in line)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Linjer", len(log_content_lines))
        with col2:
            st.metric("Fejl", errors)
        with col3:
            st.metric("Advarsler", warnings)
        
        st.divider()
        
        # Log display - newest first
        st.caption("📄 Viser nyeste loglinjer øverst")
        with st.expander("Vis fuldt log", expanded=True):
            st.code(log_content_reversed, language="plaintext")
        
        # Download
        st.download_button(
            label="⬇️ Download logfil",
            data=log_content,
            file_name=selected_log.name,
            mime="text/plain",
            width='stretch'
        )
    
    else:
        st.info("Ingen logs fundet endnu. Kør pipeline for at generere logs.")

# ============================================================================
# TAB 3: AI MANAGEMENT
# ============================================================================

with tab3:
    st.subheader("🤖 AI Management")
    
    # Sub-tabs for different AI management functions
    ai_tab1, ai_tab2 = st.tabs(["✏️ Prompt Editor", "⭐ Golden Examples"])
    
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
                        
                        # Get current golden examples for this category
                        current_golden = golden_examples.get(str(selected_category), [])
                        
                        # Load quality cache (if available)
                        quality_cache = load_json_file(DATA_CACHE / "example_quality_cache.json") or {}
                        quality_scores = quality_cache.get('quality_scores', {})
                        
                        # Display products with checkboxes
                        for product in category_products[:50]:  # Limit to 50 for performance
                            prod_num = product.get('number', 'Unknown')
                            
                            # Get product name and description from settings.items[0]
                            prod_name = prod_num  # Default to number
                            prod_desc = ""
                            
                            settings = product.get('settings', {})
                            if isinstance(settings, dict):
                                items = settings.get('items', [])
                                if items and len(items) > 0:
                                    first_setting = items[0]
                                    prod_name = first_setting.get('name', prod_num)
                                    prod_desc = (
                                        first_setting.get('longDescription', '') or
                                        first_setting.get('shortDescription', '') or
                                        ''
                                    )
                            
                            # Get quality score if available
                            quality_score = quality_scores.get(prod_num, 0.0)
                            
                            # Check if currently golden
                            is_golden = prod_num in current_golden
                            
                            # Display product with checkbox
                            col1, col2 = st.columns([3, 1])
                            with col1:
                                checkbox_key = f"golden_{selected_category}_{prod_num}"
                                is_selected = st.checkbox(
                                    f"**{prod_name[:80]}** ({prod_num})",
                                    value=is_golden,
                                    key=checkbox_key
                                )
                                
                                # Show description preview
                                if prod_desc:
                                    with st.expander("Vis beskrivelse"):
                                        st.write(prod_desc[:500] + "..." if len(prod_desc) > 500 else prod_desc)
                            
                            with col2:
                                if quality_score > 0:
                                    st.metric("Kvalitet", f"{quality_score:.2f}")
                                else:
                                    st.caption("Ikke vurderet")
                                
                                if is_golden:
                                    st.markdown("⭐ **Golden**")
                                
                                # Update golden examples list based on checkbox
                                if is_selected and prod_num not in current_golden:
                                    current_golden.append(prod_num)
                                elif not is_selected and prod_num in current_golden:
                                    current_golden.remove(prod_num)
                        
                        if len(category_products) > 50:
                            st.info(f"ℹ️ Viser kun de første 50 produkter. Total: {len(category_products)}")
                        
                        st.divider()
                        
                        # Save button
                        if st.button("💾 Gem Golden Examples", width='stretch'):
                            try:
                                # Update golden examples
                                golden_examples[str(selected_category)] = current_golden
                                
                                # Save to file
                                with open(golden_examples_file, 'w', encoding='utf-8') as f:
                                    json.dump(golden_examples, f, ensure_ascii=False, indent=2)
                                
                                st.success(f"✅ Gemt {len(current_golden)} golden examples for kategori {selected_category}!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Fejl ved gem: {e}")
                    
            except Exception as e:
                st.error(f"❌ Fejl ved indlæsning: {e}")
