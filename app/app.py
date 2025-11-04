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

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
DATA_INPUT = PROJECT_ROOT / "data" / "input"
DATA_OUTPUT = PROJECT_ROOT / "data" / "output"
LOGS_DIR = PROJECT_ROOT / "logs"
DATA_CACHE = PROJECT_ROOT / "data" / "cache"

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

def display_product_card(product):
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
                                st.image(img, use_container_width=True)
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
        
        # Metadata
        if product.get('META_DESCRIPTION'):
            with st.expander("🎯 SEO Metadata"):
                st.markdown(f'<div class="product-description"><strong>Meta beskrivelse:</strong><br/>{product.get("META_DESCRIPTION", "")}</div>', 
                           unsafe_allow_html=True)
    
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
tab1, tab2, tab3, tab4 = st.tabs(["📤 Upload & Kør", "⚙️ Status", "📊 Resultater", "📋 Logs"])

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
                st.dataframe(df, use_container_width=True)
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
        
        if st.button("▶️ Kør Alle Trin", use_container_width=True, key="run_all_steps"):
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
                ["Step 1: Sanitize", "Step 2+3: Scrape & Process", "Step 3.5: Kategorisering", "Step 4: AI Enrichment"],
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
                    if st.button("▶️ Kør Step 1 (Sanitize)", use_container_width=True, key="run_s1"):
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
                    if st.button("▶️ Kør Step 2+3 (Scrape & Process)", use_container_width=True, key="run_s23"):
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
                    if st.button("▶️ Kør Step 3.5 (Kategorisering)", use_container_width=True, key="run_s35"):
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
                            else:
                                error_msg = result.stderr or result.stdout or "Ukendt fejl"
                                error_safe = error_msg.encode('ascii', errors='replace').decode('ascii')
                                st.error(f"❌ Fejl: {error_safe[:500]}")
                        except Exception as e:
                            error_safe = str(e).encode('ascii', errors='replace').decode('ascii')
                            st.error(f"❌ Fejl: {error_safe}")
                else:
                    st.warning("Ingen produkter fundet. Kør Step 2+3 først.")
            
            else:  # Step 4: AI Enrichment
                st.write("*Input: JSON-fil med produkter*")
                input_files = list(DATA_OUTPUT.glob("*.json"))
                if input_files:
                    selected_file = st.selectbox(
                        "JSON-fil:",
                        [f.name for f in input_files],
                        key="input_json"
                    )
                    if st.button("▶️ Kør Step 4 (AI Enrichment)", use_container_width=True, key="run_s4"):
                        st.info(f"⏳ Kører Step 4 med `{selected_file}`...")
                        try:
                            full_path = DATA_OUTPUT / selected_file
                            result = subprocess.run(
                                [sys.executable, str(SCRIPTS_DIR / "4_generate_ai.py"), str(full_path)],
                                cwd=str(PROJECT_ROOT),
                                capture_output=True,
                                text=True,
                                timeout=600
                            )
                            if result.returncode == 0:
                                st.session_state.pipeline_status["Step 4 (AI)"] = True
                                st.success("✅ Step 4 fuldført!")
                            else:
                                error_msg = result.stderr or result.stdout or "Ukendt fejl"
                                error_safe = error_msg.encode('ascii', errors='replace').decode('ascii')
                                st.error(f"❌ Fejl: {error_safe[:500]}")
                        except Exception as e:
                            error_safe = str(e).encode('ascii', errors='replace').decode('ascii')
                            st.error(f"❌ Fejl: {error_safe}")
                else:
                    st.warning("Ingen JSON-fil fundet. Kør Step 2+3 først eller upload din egen JSON.")
    
    st.divider()
    st.subheader("Pipeline Status")
    
    status = get_process_status()
    for step, completed in status.items():
        status_badge = "✅ Fuldført" if completed else "⏸️ Ikke kørt"
        st.markdown(f"**{step}:** {status_badge}")

# ============================================================================
# TAB 2: PROCESS STATUS
# ============================================================================

with tab2:
    st.subheader("Processtatus")
    
    status = get_process_status()
    
    for i, (step, completed) in enumerate(status.items(), 1):
        status_class = "status-complete" if completed else "status-pending"
        status_text = "✅" if completed else "⏸️"
        
        st.markdown(f"""
        <div class="step-card">
            <span class="step-status {status_class}">{status_text} {step}</span>
        </div>
        """, unsafe_allow_html=True)
    
    st.divider()
    st.subheader("🔍 Seneste Log Lines")
    
    log_content = get_latest_log_lines(30)
    with st.expander("Vis log"):
        st.code(log_content, language="plaintext")

# ============================================================================
# TAB 3: RESULTS GALLERY
# ============================================================================

with tab3:
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
                for product in filtered_products:
                    display_product_card(product)
                
                st.divider()
                
                # Export
                col1, col2 = st.columns(2)
                
                with col1:
                    json_str = json.dumps(filtered_products, ensure_ascii=False, indent=2)
                    st.download_button(
                        label="⬇️ Download som JSON",
                        data=json_str,
                        file_name=f"produkter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        use_container_width=True
                    )
                
                with col2:
                    try:
                        df = pd.DataFrame(filtered_products)
                        csv = df.to_csv(index=False, encoding='utf-8-sig')
                        st.download_button(
                            label="⬇️ Download som CSV",
                            data=csv,
                            file_name=f"produkter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"Could not generate CSV: {e}")
        
        except Exception as e:
            st.error(f"❌ Fejl ved indlæsning af produkter: {e}")

# ============================================================================
# TAB 4: LOGS
# ============================================================================

with tab4:
    st.subheader("📋 Logs")
    
    # Log file selector
    log_dir = Path(LOGS_DIR)
    log_files = sorted(log_dir.glob("*.log"), key=lambda x: x.stat().st_mtime, reverse=True)
    
    if log_files:
        selected_log = st.selectbox(
            "Vælg logfil:",
            log_files,
            format_func=lambda x: f"{x.name} ({x.stat().st_mtime})"
        )
        
        # Read log
        with open(selected_log, 'r', encoding='utf-8', errors='ignore') as f:
            log_content = f.read()
        
        # Statistics
        lines = log_content.split('\n')
        errors = sum(1 for line in lines if 'ERROR' in line or 'error' in line)
        warnings = sum(1 for line in lines if 'WARNING' in line or 'warning' in line)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Linjer", len(lines))
        with col2:
            st.metric("Fejl", errors)
        with col3:
            st.metric("Advarsler", warnings)
        
        st.divider()
        
        # Log display
        with st.expander("Vis fuldt log", expanded=True):
            st.code(log_content, language="plaintext")
        
        # Download
        st.download_button(
            label="⬇️ Download logfil",
            data=log_content,
            file_name=selected_log.name,
            mime="text/plain",
            use_container_width=True
        )
    
    else:
        st.info("Ingen logs fundet endnu. Kør pipeline for at generere logs.")
