#!/usr/bin/env python3
"""
Step 3: Process Images
Organizes images from Step 2 into data/output/images/ with relative paths.

Input:  data/output/supplier_info.json (has absolute image paths)
Output: data/output/enriched_products.json (updated with relative image paths)
        data/output/images/ (organized images)

Logs to: logs/3_process_images.log
"""

import json
import os
import sys
import logging
from pathlib import Path
from shutil import copy2
from PIL import Image
import yaml
from datetime import datetime

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


# Safe stream for console output (handles encoding errors)
class SafeStream:
    def __init__(self):
        self.encoding = 'utf-8'
    
    def write(self, msg):
        if not msg:
            return
        try:
            sys.__stdout__.write(msg)
        except UnicodeEncodeError:
            try:
                safe_msg = msg.encode('utf-8', errors='replace').decode(sys.__stdout__.encoding or 'utf-8', errors='replace')
                sys.__stdout__.write(safe_msg)
            except Exception:
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
            self.stream.write(msg)
            self.stream.write('\n')
            self.stream.flush()
        except Exception:
            self.handleError(record)

def load_config():
    """Load config.yaml with defaults."""
    config_path = PROJECT_ROOT / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            # Normalize path keys
            if "paths" in config:
                paths = config["paths"]
                return {
                    "paths": {
                        "input": paths.get("input_dir", "data/input"),
                        "output": paths.get("output_dir", "data/output"),
                        "cache": paths.get("cache_dir", "data/cache"),
                        "logs": paths.get("logs_dir", "logs"),
                    },
                    "logging": config.get("logging", {"level": "INFO"})
                }
            return config
    return {
        "paths": {
            "input": str(PROJECT_ROOT / "data" / "input"),
            "output": str(PROJECT_ROOT / "data" / "output"),
            "cache": str(PROJECT_ROOT / "data" / "cache"),
            "logs": str(PROJECT_ROOT / "logs"),
        },
        "logging": {"level": "INFO"}
    }


def setup_logging(log_dir: Path, log_file_name: str = "3_process_images.log"):
    """Configure logging to file and console"""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / log_file_name
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler (UTF-8)
    file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='a')
    file_handler.setFormatter(formatter)
    
    # Console handler with SafeStream
    console_handler = SafeStreamHandler(SafeStream())
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.handlers.clear()  # Remove existing handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def atomic_write_json(file_path, data):
    """Write JSON atomically: write to .tmp, then rename."""
    tmp_path = str(file_path) + ".tmp"
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    Path(tmp_path).replace(file_path)


def process_images(logger, config):
    """
    Process images from supplier_info.json:
    1. Read supplier_info.json (scraped data)
    2. Load original processed products for metadata enrichment
    3. Merge processed metadata into supplier data
    4. Copy images to data/output/images/
    5. Update JSON with relative paths
    6. Write to enriched_products.json
    """
    output_dir = Path(config["paths"]["output"])
    cache_dir = Path(config["paths"]["cache"])
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)
    
    # Create PDF directory for datablad
    pdfs_dir = output_dir / "pdfs"
    pdfs_dir.mkdir(exist_ok=True)
    
    supplier_info_path = output_dir / "supplier_info.json"
    if not supplier_info_path.exists():
        logger.error(f"Input file not found: {supplier_info_path}")
        return False
    
    # Load original processed products for metadata
    processed_products_path = cache_dir / "processed_products.json"
    processed_by_prod_num = {}
    if processed_products_path.exists():
        logger.info(f"Loading processed products metadata: {processed_products_path}")
        try:
            with open(processed_products_path, 'r', encoding='utf-8') as f:
                processed_products = json.load(f)
                if isinstance(processed_products, dict):
                    processed_products = [processed_products]
                # Index by PROD_NUM for fast lookup
                for prod in processed_products:
                    prod_num = prod.get("PROD_NUM")
                    if prod_num:
                        processed_by_prod_num[prod_num] = prod
                logger.info(f"  Indexed {len(processed_by_prod_num)} products by PROD_NUM")
        except Exception as e:
            logger.warning(f"  Could not load processed products: {e}")
    else:
        logger.warning(f"Processed products file not found: {processed_products_path}")
    
    logger.info(f"Reading supplier info: {supplier_info_path}")
    with open(supplier_info_path, 'r', encoding='utf-8') as f:
        supplier_data = json.load(f)
    
    # Handle both list and single dict
    if isinstance(supplier_data, dict):
        supplier_data = [supplier_data]
    
    logger.info(f"Processing {len(supplier_data)} products")
    
    processed_count = 0
    image_count = 0
    pdf_count = 0
    
    for idx, product in enumerate(supplier_data, 1):
        product_num = product.get("product_number", f"product_{idx}")
        logger.info(f"[{idx}/{len(supplier_data)}] {product_num}")
        
        # Merge metadata from original processed data
        if product_num in processed_by_prod_num:
            processed_row = processed_by_prod_num[product_num]
            # Add all metadata fields from processed (don't override existing supplier data)
            for key, value in processed_row.items():
                # Skip keys that are already in supplier_data (keep scraped data)
                if key not in product or key in ["PROD_NUM", "PROD_NUM_old"]:
                    product[key] = value
            logger.debug(f"  Merged metadata from processed products")
        
        # Download datablad PDF if available
        # Priority: ProductDataSheetURL > SDSDocumentURL > DatabladMGURL > etc.
        pdf_url_fields = [
            "ProductDataSheetURL", "SDSDocumentURL", "DatabladMGURL", 
            "DatabladURL", "DeclarationOfComplianceURL", "MSDSDocumentURL"
        ]
        
        product_num_clean = product.get("PROD_NUM_old", product_num.replace(" - Deaktiveret", ""))
        pdf_downloaded = False
        
        for field in pdf_url_fields:
            pdf_url = product.get(field)
            if pdf_url and str(pdf_url).strip() and not pdf_downloaded:
                try:
                    import requests
                    response = requests.get(str(pdf_url).strip(), timeout=10)
                    response.raise_for_status()
                    
                    # Save PDF with clean product number
                    pdf_path = pdfs_dir / f"{product_num_clean}.pdf"
                    with open(pdf_path, 'wb') as f:
                        f.write(response.content)
                    
                    logger.info(f"  Downloaded datablad PDF from {field}")
                    pdf_count += 1
                    pdf_downloaded = True
                    break  # Only download one PDF per product
                    
                except Exception as e:
                    logger.debug(f"  Failed to download PDF from {field}: {e}")
                    continue
        
        if "images" not in product or not product["images"]:
            logger.debug(f"  No images for {product_num}")
            continue
        
        # Process each image
        new_images = []
        for img_path_str in product["images"]:
            if not img_path_str:
                continue
            
            img_path = Path(img_path_str)
            if not img_path.exists():
                logger.warning(f"  Image not found: {img_path}")
                continue
            
            try:
                # Generate unique filename
                img_name = img_path.name
                dest_path = images_dir / img_name
                
                # Copy image
                copy2(img_path, dest_path)
                
                # Verify it's a valid image
                try:
                    Image.open(dest_path).verify()
                except Exception as e:
                    logger.warning(f"  Image verification failed: {img_name} - {e}")
                    dest_path.unlink()  # Remove invalid image
                    continue
                
                # Store relative path
                rel_path = f"images/{img_name}"
                new_images.append(rel_path)
                image_count += 1
                logger.debug(f"  Copied: {img_name}")
                
            except Exception as e:
                logger.error(f"  Error processing image {img_path}: {e}")
                continue
        
        # Update product with relative paths
        product["images"] = new_images
        logger.debug(f"  Updated {len(new_images)} images")
        processed_count += 1
    
    # Write enriched output
    enriched_path = output_dir / "enriched_products.json"
    atomic_write_json(enriched_path, supplier_data)
    logger.info(f"✓ Enriched JSON: {enriched_path}")
    
    logger.info("=" * 60)
    logger.info("✓ Step 3 complete")
    logger.info(f"  Processed: {processed_count} products")
    logger.info(f"  Images copied: {image_count}")
    logger.info(f"  PDFs downloaded: {pdf_count}")
    logger.info(f"  Output images: {images_dir}")
    logger.info(f"  Output PDFs: {pdfs_dir}")
    logger.info(f"  Output JSON: {enriched_path}")
    logger.info("=" * 60)
    
    return True


def main():
    """Main entry point."""
    config = load_config()
    logger = setup_logging(Path(config["paths"]["logs"]))
    
    logger.info("=" * 60)
    logger.info("Step 3: Image Processing")
    logger.info("=" * 60)
    
    success = process_images(logger, config)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
