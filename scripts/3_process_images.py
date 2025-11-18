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

from scripts.utils import setup_logging, load_config, atomic_write_json

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
    paths = config.get("paths", {})
    output_dir = PROJECT_ROOT / paths.get("output_dir", "data/output")
    cache_dir = PROJECT_ROOT / paths.get("cache_dir", "data/cache")
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)
    
    # Create PDF directory for datablad
    pdfs_dir = output_dir / "pdfs"
    pdfs_dir.mkdir(exist_ok=True)
    
    # Determine external PDF directory (sibling to external images dir)
    external_images_dir_str = paths.get("external_images_dir")
    external_pdfs_dir = None
    if external_images_dir_str:
        try:
            ext_img_path = Path(external_images_dir_str)
            # Create 'Datablade' folder next to the images folder
            external_pdfs_dir = ext_img_path.parent / "Datablade"
            external_pdfs_dir.mkdir(exist_ok=True)
            logger.info(f"Using external PDF directory: {external_pdfs_dir}")
        except Exception as e:
            logger.warning(f"Could not setup external PDF directory: {e}")
    
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
            # List of important fields to preserve from processed data (prices, metadata, etc.)
            important_fields = {
                "PROD_NUM", "PROD_NUM_old", "PROD_COST_PRICE", "Retail_Price", "Flerstk. pris", 
                "Besparelse", "PROD_WEIGHT", "PROD_BARCODE_NUMBER", "STOCK_COUNT", "PROD_MIN_BUY",
                "PROD_MAX_BUY", "PROD_SORT", "PROD_HIDDEN", "PROD_FRONT_PAGE", "PROD_DELIVERY",
                "PROD_DELIVERY_NOT_IN_STOCK", "PROD_NEW", "PROD_SHOW_ON_GOOGLE_FEED",
                "PROD_SHOW_ON_FACEBOOK_FEED", "PROD_SHOW_ON_PRICERUNNER_FEED",
                "FIELD_1", "FIELD_2", "FIELD_17", "FIELD_18", "FIELD_20",
                "SalesUnitID", "StockUnitID", "DataAreaID", "UnitConvStockPurch"
            }
            # Add all fields from processed (prefer processed over scraped for these fields)
            for key, value in processed_row.items():
                if key in important_fields or key not in product:
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
                logger.info(f"  Found PDF URL in {field}: {pdf_url}")
                try:
                    import requests
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.9',
                        'Referer': 'https://www.bunzl.dk/',
                    }
                    response = requests.get(str(pdf_url).strip(), headers=headers, timeout=30)
                    response.raise_for_status()
                    
                    # Check content type
                    content_type = response.headers.get('Content-Type', '').lower()
                    if 'application/pdf' not in content_type and 'application/octet-stream' not in content_type:
                        logger.warning(f"  Warning: Content-Type is {content_type}, not PDF")
                    
                    # Save PDF with clean product number
                    pdf_path = pdfs_dir / f"{product_num_clean}.pdf"
                    with open(pdf_path, 'wb') as f:
                        f.write(response.content)
                    
                    # Copy to external if configured
                    if external_pdfs_dir and external_pdfs_dir.exists():
                        try:
                            copy2(pdf_path, external_pdfs_dir / pdf_path.name)
                            logger.info(f"  ✓ Copied PDF to external: {external_pdfs_dir}")
                        except Exception as e:
                            logger.warning(f"  Failed to copy PDF to external: {e}")
                    
                    logger.info(f"  ✓ Downloaded datablad PDF from {field}")
                    pdf_count += 1
                    pdf_downloaded = True
                    break  # Only download one PDF per product
                    
                except Exception as e:
                    logger.warning(f"  Failed to download PDF from {field}: {e}")
                    continue
        
        if not pdf_downloaded:
            logger.debug(f"  No PDF downloaded for {product_num}")
        
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
                
                # Check if source and destination are the same (can happen in some configs)
                if img_path.resolve() == dest_path.resolve():
                    logger.debug(f"  Source and dest are same, skipping copy: {img_name}")
                else:
                    # Copy image
                    copy2(img_path, dest_path)
                
                # Verify it's a valid image
                try:
                    Image.open(dest_path).verify()
                except Exception as e:
                    logger.warning(f"  Image verification failed: {img_name} - {e}")
                    if dest_path.exists() and img_path.resolve() != dest_path.resolve():
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
        
        # Preserve app_images from scraping step if available
        if "app_images" in product:
            # Convert app_images to relative paths within data/output/images
            app_images_rel = []
            for app_img_path in product.get("app_images", []):
                app_img = Path(app_img_path)
                if app_img.exists():
                    # Copy to output images and create relative path
                    dest_name = app_img.name
                    dest_path = images_dir / dest_name
                    if not dest_path.exists():
                        copy2(app_img, dest_path)
                    app_images_rel.append(f"images/{dest_name}")
            
            product["app_images"] = app_images_rel
        
        logger.debug(f"  Updated {len(new_images)} images")
        processed_count += 1
    
    # Write enriched output
    enriched_path = output_dir / "enriched_products.json"
    atomic_write_json(supplier_data, enriched_path)
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
    config_path = PROJECT_ROOT / "config.yaml"
    config = load_config(config_path)
    paths = config.get("paths", {})
    logs_dir = PROJECT_ROOT / paths.get("logs_dir", "logs")
    
    logger = setup_logging(logs_dir, "3_process_images")
    
    logger.info("=" * 60)
    logger.info("Step 3: Image Processing")
    logger.info("=" * 60)
    
    success = process_images(logger, config)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
