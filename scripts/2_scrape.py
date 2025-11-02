#!/usr/bin/env python3
"""
Step 2: Supplier Scraping
Reads processed products JSON, scrapes supplier websites for info/images, writes outputs.

Usage:
  python scripts/2_scrape.py [--input path/to/processed.json]
  
  If no input specified, reads from data/cache/processed_products.json
"""

import sys
import os
import json
import logging
from pathlib import Path
from datetime import datetime
import time
import yaml
import importlib
import requests
import pandas as pd
import shutil
import zipfile
from typing import Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# Import utilities and vendor modules
from supplier_pi.utils.pdf_extractor import extract_text_from_pdf
from supplier_pi.utils.image_processor import resize_and_save_all_images

# Safe stream for console output (handles encoding errors)
class SafeStream:
    def __init__(self):
        self.encoding = 'utf-8'
    
    def write(self, msg):
        if not msg:
            return
        try:
            # Try direct write first
            sys.__stdout__.write(msg)
        except UnicodeEncodeError:
            try:
                # Fallback: encode with error replacement
                safe_msg = msg.encode('utf-8', errors='replace').decode(sys.__stdout__.encoding or 'utf-8', errors='replace')
                sys.__stdout__.write(safe_msg)
            except Exception:
                # Last resort: ignore errors
                try:
                    safe_msg = msg.encode('ascii', errors='replace').decode('ascii')
                    sys.__stdout__.write(safe_msg)
                except Exception:
                    pass
    
    def flush(self):
        try:
            sys.__stdout__.flush()
        except Exception:
            pass
    
    def isatty(self):
        return sys.__stdout__.isatty() if hasattr(sys.__stdout__, 'isatty') else False

class SafeStreamHandler(logging.StreamHandler):
    """Custom logging handler that prevents encoding errors"""
    def emit(self, record):
        try:
            msg = self.format(record)
            # Use SafeStream's write method
            self.stream.write(msg)
            self.stream.write('\n')
            self.stream.flush()
        except Exception:
            self.handleError(record)

def setup_logging(log_dir: Path):
    """Configure logging to file and console"""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "2_scrape.log"
    
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='a')
    file_handler.setFormatter(formatter)
    
    console_handler = SafeStreamHandler(SafeStream())
    console_handler.setFormatter(formatter)
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def load_config(config_path: Path) -> dict:
    """Load config.yaml"""
    if not config_path.exists():
        logging.warning(f"Config file not found: {config_path}, using defaults")
        return {}
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def load_vendor_map() -> dict:
    """Load vendor module mapping"""
    vendor_map_path = PROJECT_ROOT / 'supplier_pi' / 'utils' / 'vendor_map.json'
    with open(vendor_map_path, encoding='utf-8') as f:
        raw_map = json.load(f)
    # Case-insensitive mapping
    return {k.strip().lower(): v for k, v in raw_map.items()}

def get_vendor_module(vendor_name: str, vendor_map: dict):
    """Load vendor-specific scraping module"""
    module_name = vendor_map.get(vendor_name.strip().lower())
    if not module_name:
        logging.error(f"No vendor module mapping for '{vendor_name}'")
        return None
    
    module_path = f"supplier_pi.supplier_modules.{module_name.lower()}"
    try:
        return importlib.import_module(module_path)
    except ModuleNotFoundError as e:
        logging.error(f"No vendor module found: {module_path} - {e}")
        return None

def clean_supplier_info(text):
    """Remove excessive whitespace and newlines"""
    if not isinstance(text, str):
        return text
    import re
    cleaned = re.sub(r'[\r\n\t]+', ' ', text)
    cleaned = re.sub(r' +', ' ', cleaned)
    return cleaned.strip()

def extract_pdf_text(pdf_url, download_folder, product_number):
    """Download PDF and extract text"""
    if not pdf_url or not pdf_url.strip():
        return ""
    
    try:
        pdf_path = Path(download_folder) / f"{product_number}.pdf"
        r = requests.get(pdf_url, timeout=10)
        if r.status_code == 200:
            with open(pdf_path, "wb") as f:
                f.write(r.content)
            text = extract_text_from_pdf(str(pdf_path))
            if text:
                logging.info(f"Extracted PDF text from {pdf_url}")
                return text.replace("\n", " ").strip()
    except Exception as e:
        logging.warning(f"Failed to extract PDF text: {e}")
    
    return ""

def download_and_extract_images(image_zip_url, product_number, img_name, download_folder, original_folder):
    """Download ZIP, extract images"""
    if not image_zip_url or not image_zip_url.strip():
        logging.warning(f"No image ZIP URL for {product_number}")
        return 0
    
    try:
        logging.info("Downloading image ZIP...")
        zip_path = Path(download_folder) / f"{product_number}_images.zip"
        extract_path = Path(download_folder) / f"{product_number}_extracted_images"
        
        r = requests.get(image_zip_url, timeout=10)
        if r.status_code != 200:
            logging.warning(f"Failed to download ZIP: HTTP {r.status_code}")
            return 0
        
        with open(zip_path, "wb") as f:
            f.write(r.content)
        
        if extract_path.exists():
            shutil.rmtree(extract_path)
        extract_path.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_path)
        
        img_counter = 0
        for file in os.listdir(extract_path):
            if file.lower().endswith((".jpg", ".jpeg", ".png")):
                source = extract_path / file
                suffix = f"-{img_counter + 1}" if img_counter > 0 else ""
                target = Path(original_folder) / f"{img_name}{suffix}.jpg"
                shutil.move(str(source), str(target))
                logging.info(f"Saved image: {target}")
                img_counter += 1
        
        # Cleanup
        if zip_path.exists():
            os.remove(zip_path)
        if extract_path.exists():
            shutil.rmtree(extract_path)

        logging.info(f"Extracted {img_counter} images")
        return img_counter
        
    except Exception as e:
        logging.error(f"Error downloading/extracting images: {e}")
        return 0

def download_images_from_urls(image_urls, product_number, img_name, download_folder, original_folder):
    """Download images directly from URLs"""
    if not image_urls or not isinstance(image_urls, list):
        logging.warning(f"No image URLs for {product_number}")
        return 0
    
    try:
        os.makedirs(original_folder, exist_ok=True)
        img_counter = 0

        for i, url in enumerate(image_urls, start=1):
            try:
                resp = requests.get(url, timeout=10, stream=True)
                resp.raise_for_status()
                suffix = f"-{i}" if i > 1 else ""
                ext = os.path.splitext(url)[1] or ".jpg"
                path = Path(original_folder) / f"{img_name}{suffix}{ext}"
                with open(path, "wb") as f:
                    shutil.copyfileobj(resp.raw, f)
                logging.info(f"Saved image: {path}")
                img_counter += 1
            except Exception as e:
                logging.warning(f"Could not download {url}: {e}")

        logging.info(f"Downloaded {img_counter} images")
        return img_counter

    except Exception as e:
        logging.error(f"Error downloading images: {e}")
        return 0

def process_vendor_row(vendor_name, row, driver, download_folder, original_folder, image_folder, vendor_map):
    """Process one product row"""
    vendor_module = get_vendor_module(vendor_name, vendor_map)
    product_number = str(row.get("PrimaryVendorItemID", "")).strip()
    img_name = str(row.get("IMG_NAME", "")).strip()
    prod_num = str(row.get("PROD_NUM", "")).strip()
    image_url = str(row.get("ImageURL", "")).strip()
    
    supplier_info = ""
    product_url = ""
    image_files = []
    image_sizes = []
    supplier_info_source = "none"
    
    if vendor_module is not None:
        result = vendor_module.extract_supplier_info(row, original_folder, driver=driver, download_folder=download_folder)
        
        if isinstance(result, dict):
            product_url = result.get("product_url", "")
            image_zip_url = result.get("image_zip_url")
            image_urls = result.get("image_urls", [])
            
            if image_zip_url:
                download_and_extract_images(image_zip_url, product_number, img_name, download_folder, original_folder)
                resize_and_save_all_images(original_folder, image_folder, img_name)
            elif image_urls:
                download_images_from_urls(image_urls, product_number, img_name, download_folder, original_folder)
                resize_and_save_all_images(original_folder, image_folder, img_name)
            
            pdf_url = result.get("pdf_url")
            if pdf_url:
                supplier_info = extract_pdf_text(pdf_url, download_folder, product_number)
                supplier_info_source = "pdf"
            
            if not supplier_info:
                supplier_info = result.get("supplier_info", "")
                if supplier_info:
                    supplier_info_source = "description"
        else:
            supplier_info, product_url = result if isinstance(result, tuple) else ("", result)
            if supplier_info:
                supplier_info_source = "description"
    else:
        # Fallback: try image URL if no vendor module
        if image_url:
            try:
                response = requests.get(image_url, timeout=10)
                if response.status_code == 200:
                    original_path = Path(original_folder) / f"{img_name}.jpg"
                    with open(original_path, "wb") as f:
                        f.write(response.content)
                    logging.info(f"Fallback image saved: {original_path}")
                    resize_and_save_all_images(original_folder, image_folder, img_name)
            except Exception as e:
                logging.error(f"Error during fallback image processing: {e}")
    
    supplier_info = clean_supplier_info(supplier_info)
    
    # Gather image info
    if img_name:
        for file in os.listdir(original_folder):
            if file.startswith(img_name) and file.lower().endswith((".jpg", ".jpeg", ".png")):
                path = Path(original_folder) / file
                if path.exists():
                    image_files.append(str(path))
                    try:
                        from PIL import Image
                        with Image.open(path) as im:
                            image_sizes.append(list(im.size))
                    except Exception:
                        image_sizes.append("unknown")
    
    # Images are in external OneDrive folder, so store absolute paths
    supplier_data = {
        "product_number": prod_num,
        "product_url": product_url,
        "supplier_info": supplier_info,
        "images": [str(Path(p)).replace('\\', '/') for p in image_files]
    }
    
    run_summary = {
        "product_number": prod_num,
        "status": ("success" if supplier_info and product_url else "partial" if supplier_info or product_url else "failed"),
        "images_found": len(image_files),
        "image_sizes": image_sizes,
        "supplier_info_source": supplier_info_source,
        "missing_supplier_info": not bool(supplier_info),
        "missing_product_url": not bool(product_url)
    }
    
    return supplier_data, run_summary

def atomic_write_json(data, path: Path):
    """Write JSON atomically"""
    tmp = path.with_suffix('.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)

def setup_selenium(config: dict):
    """Initialize Selenium WebDriver"""
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import SessionNotCreatedException
    from webdriver_manager.chrome import ChromeDriverManager
    import subprocess
    import re
    
    chrome_settings = config.get('chrome', {})
    
    options = Options()
    if chrome_settings.get('headless', True):
        options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920x1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # Try to find Chrome binary
    chrome_path = chrome_settings.get('binary_path', '')
    if not chrome_path:
        chrome_path = shutil.which("chrome") or shutil.which("google-chrome") or shutil.which("chrome.exe")
        if not chrome_path:
            possible = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            ]
            for p in possible:
                if os.path.exists(p):
                    chrome_path = p
                    break
    
    if chrome_path:
        options.binary_location = chrome_path
        logging.info(f"Using Chrome: {chrome_path}")
    
    # Try to install matching chromedriver
    try:
        driver_exe = ChromeDriverManager().install()
        driver = webdriver.Chrome(service=Service(driver_exe), options=options)
    except SessionNotCreatedException:
        logging.warning("Chrome crashed in headless mode, retrying without headless")
        if chrome_settings.get('retry_without_headless', True):
            options_no_head = Options()
            options_no_head.add_argument("--window-size=1920x1080")
            options_no_head.add_argument("--no-sandbox")
            if chrome_path:
                options_no_head.binary_location = chrome_path
            driver = webdriver.Chrome(service=Service(driver_exe), options=options_no_head)
        else:
            raise
    
    return driver

def main():
    # Load config
    config_path = PROJECT_ROOT / "config.yaml"
    config = load_config(config_path)
    paths = config.get('paths', {})
    
    # Set up directories
    cache_dir = PROJECT_ROOT / paths.get('cache_dir', 'data/cache')
    output_dir = PROJECT_ROOT / paths.get('output_dir', 'data/output')
    logs_dir = PROJECT_ROOT / paths.get('logs_dir', 'logs')
    
    download_folder = cache_dir / 'downloads'
    download_folder.mkdir(parents=True, exist_ok=True)
    
    # External folders (OneDrive paths from original scraper)
    user_profile = Path(os.path.expanduser("~"))
    original_folder = user_profile / "OneDrive - Bunzl Continental Europe" / "Documents - Bonvig" / "original billeder" / "Produktbilleder"
    image_folder = user_profile / "OneDrive - Bunzl Continental Europe" / "Documents - Bonvig" / "Produktbilleder_1500x1500"
    
    original_folder.mkdir(parents=True, exist_ok=True)
    image_folder.mkdir(parents=True, exist_ok=True)
    
    # Set up logging
    logger = setup_logging(logs_dir)
    
    logger.info("=" * 60)
    logger.info("Step 2: Supplier Scraping")
    logger.info("=" * 60)
    
    # Load input
    input_path = cache_dir / "processed_products.json"
    if len(sys.argv) > 1:
        input_path = Path(sys.argv[1])
    
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        sys.exit(1)
    
    logger.info(f"Input: {input_path}")
    
    with open(input_path, 'r', encoding='utf-8') as f:
        products = json.load(f)
    
    logger.info(f"Loaded {len(products)} products")
    
    # Load vendor map
    vendor_map = load_vendor_map()
    
    # Set up Selenium
    logger.info("Initializing Selenium WebDriver...")
    driver = setup_selenium(config)
    
    # Process products
    supplier_data_list = []
    run_summary_list = []
    
    output_json = output_dir / "supplier_info.json"
    summary_json = output_dir / "run_summary.json"
    
    for index, product in enumerate(products, 1):
        vendor_name = str(product.get("PrimaryVendorName", "")).strip().lower()
        if not vendor_name:
            logger.warning(f"Product {index}/{len(products)}: No vendor name, skipping")
            continue
        
        prod_num = product.get("PROD_NUM", "")
        logger.info(f"[{index}/{len(products)}] Processing {prod_num} ({vendor_name})")
        
        try:
            supplier_data, run_summary = process_vendor_row(
                vendor_name, product, driver, 
                str(download_folder), str(original_folder), str(image_folder),
                vendor_map
            )
            supplier_data_list.append(supplier_data)
            run_summary_list.append(run_summary)
            
            # Write incrementally
            atomic_write_json(supplier_data_list, output_json)
            atomic_write_json(run_summary_list, summary_json)
            
        except Exception as e:
            logger.error(f"Failed to process {prod_num}: {e}", exc_info=True)
            run_summary_list.append({
                "product_number": prod_num,
                "status": "failed",
                "missing_supplier_info": True,
                "missing_product_url": True,
                "images_found": 0,
                "image_sizes": [],
                "supplier_info_source": "none",
                "error": str(e)
            })
    
    driver.quit()
    
    # Summary
    logger.info("=" * 60)
    logger.info("Run Summary:")
    for item in run_summary_list:
        logger.info(f"  {item.get('product_number')}: {item.get('status')} - {item.get('images_found', 0)} images")
    
    logger.info("=" * 60)
    logger.info(f"✓ Step 2 complete")
    logger.info(f"  Processed: {len(run_summary_list)}/{len(products)}")
    logger.info(f"  Output: {output_json}")
    logger.info(f"  Summary: {summary_json}")
    logger.info("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
