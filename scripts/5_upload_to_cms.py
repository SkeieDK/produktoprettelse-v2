"""
Step 5: Upload products to Dandomain CMS
========================================

This script:
1. Uploads images/PDFs via FTP to Dandomain server
2. Creates/updates products via API with media URLs
3. Validates products don't already exist (by number and vendorNumber)
4. Maps our data to Dandomain schema
5. Tracks upload results

Author: AI Assistant
"""

import json
import sys
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from ftplib import FTP
import base64
import requests
from tqdm import tqdm
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_OUTPUT = DATA_DIR / "output"
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Image source directory (1500x1500 processed images)
IMAGES_SOURCE_DIR = Path(r"C:\Users\anton\OneDrive - Bunzl Continental Europe\Documents - Bonvig\Produktbilleder_1500x1500")

# Setup logging
log_file = LOGS_DIR / "5_upload_to_cms.log"
logging.basicConfig(
    level=logging.DEBUG,  # Changed to DEBUG to see payload
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DandomainUploader:
    """Handles uploading products to Dandomain CMS"""
    
    def __init__(self, dry_run: bool = False):
        """
        Initialize uploader
        
        Args:
            dry_run: If True, only preview what would be sent without actually uploading
        """
        self.dry_run = dry_run
        
        # Load credentials from environment
        self.api_key = os.getenv('API_KEY')
        self.ftp_host = os.getenv('FTP_HOST', '')
        self.ftp_user = os.getenv('FTP_USER', '')
        self.ftp_password = os.getenv('FTP_PASSWORD', '')
        
        if not self.api_key:
            raise ValueError("API_KEY not found in environment variables!")
        
        if not self.ftp_host or not self.ftp_user or not self.ftp_password:
            logger.warning("FTP credentials not fully configured - image/PDF upload will fail!")
            logger.warning(f"FTP_HOST: {'✓' if self.ftp_host else '✗'}")
            logger.warning(f"FTP_USER: {'✓' if self.ftp_user else '✗'}")
            logger.warning(f"FTP_PASSWORD: {'✓' if self.ftp_password else '✗'}")
        
        # API endpoints
        self.base_url = "https://engrosrengoringsmidler.dk/admin/WebAPI/v2"
        self.products_url = f"{self.base_url}/products"
        
        # FTP paths
        self.ftp_image_path = "/images/produkt_billeder/"
        self.ftp_pdf_path = "/images/datablade/"
        
        # Image base URL (relative path - no domain prefix)
        self.image_base_url = "/images/produkt_billeder/"
        self.pdf_base_url = "/images/datablade/"
        
        # Load products cache for duplicate checking
        cache_file = PROJECT_ROOT / "cache" / "products_cache.json"
        self.existing_products = []
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    self.existing_products = json.load(f)
                logger.info(f"Loaded {len(self.existing_products)} existing products from cache")
            except Exception as e:
                logger.warning(f"Could not load products cache: {e}")
        else:
            logger.warning("products_cache.json not found - cannot check for duplicates!")
        
        logger.info("Dandomain uploader initialized")
        if self.dry_run:
            logger.info("🔍 DRY RUN MODE - No actual uploads will be performed")
    
    def _create_auth_header(self) -> Dict[str, str]:
        """Create Basic Auth header for API requests"""
        auth_text = f":{self.api_key}"
        auth_string = base64.b64encode(auth_text.encode('utf-8')).decode('utf-8')
        
        return {
            'accept': 'text/plain',
            'Authorization': f'Basic {auth_string}',
            'Content-Type': 'application/json'
        }
    
    def check_product_exists(self, product_number: str, vendor_number: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Check if product already exists by product number or vendor number using local cache
        
        Returns:
            (exists, product_data, match_field) - True if exists, along with existing product data and which field matched
        """
        # Search in cache by product number (exact match)
        for product in self.existing_products:
            if product.get('number') == product_number:
                logger.info(f"Product {product_number} already exists (found by number in cache)")
                return True, product, "product number"
        
        # Search by vendor number if not found by product number
        if vendor_number:
            for product in self.existing_products:
                if str(product.get('vendorNumber', '')) == str(vendor_number):
                    logger.info(f"Product with vendor number {vendor_number} already exists (found in cache)")
                    return True, product, "vendor number"
        
        return False, None, None
    
    def upload_image_ftp(self, local_path: Path, remote_filename: str = None) -> Optional[str]:
        """
        Upload image to Dandomain FTP server
        
        Args:
            local_path: Path to local image file
            remote_filename: Optional remote filename (if None, uses local filename)
        
        Returns:
            URL of uploaded image, or None if upload failed
        """
        if not local_path.exists():
            logger.warning(f"Image file not found: {local_path}")
            return None
        
        # Use original filename if no remote filename specified
        if remote_filename is None:
            remote_filename = local_path.name
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would upload {local_path.name} → {self.ftp_image_path}{remote_filename}")
            return f"{self.image_base_url}{remote_filename}"
        
        ftp = None
        try:
            # Validate FTP credentials
            if not self.ftp_host or not self.ftp_user or not self.ftp_password:
                logger.error("FTP credentials missing - cannot upload image")
                return None
            
            # Connect to FTP
            ftp = FTP(self.ftp_host)
            ftp.login(self.ftp_user, self.ftp_password)
            
            # Change to images directory
            ftp.cwd(self.ftp_image_path)
            
            # Upload file
            with open(local_path, 'rb') as f:
                ftp.storbinary(f'STOR {remote_filename}', f)
            
            ftp.quit()
            
            image_url = f"{self.image_base_url}{remote_filename}"
            logger.info(f"✓ Uploaded image: {remote_filename}")
            return image_url
            
        except Exception as e:
            logger.error(f"Failed to upload image via FTP: {e}")
            if ftp:
                try:
                    ftp.quit()
                except:
                    pass
            return None
    
    def upload_pdf_ftp(self, local_path: Path, product_number_clean: str) -> Optional[str]:
        """
        Upload PDF (datablad) to Dandomain FTP server
        
        Args:
            local_path: Path to local PDF file
            product_number_clean: Clean product number without " - Deaktiveret" (e.g., E146230)
        
        Returns:
            URL of uploaded PDF, or None if upload failed
        """
        if not local_path.exists():
            logger.warning(f"PDF file not found: {local_path}")
            return None
        
        # Remote filename is just the product number (e.g., E146230.pdf)
        remote_filename = f"{product_number_clean}.pdf"
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would upload {local_path.name} → {self.ftp_pdf_path}{remote_filename}")
            return f"{self.pdf_base_url}{remote_filename}"
        
        ftp = None
        try:
            # Validate FTP credentials
            if not self.ftp_host or not self.ftp_user or not self.ftp_password:
                logger.error("FTP credentials missing - cannot upload PDF")
                return None
            
            # Connect to FTP
            ftp = FTP(self.ftp_host)
            ftp.login(self.ftp_user, self.ftp_password)
            
            # Change to PDF directory
            ftp.cwd(self.ftp_pdf_path)
            
            # Upload file
            with open(local_path, 'rb') as f:
                ftp.storbinary(f'STOR {remote_filename}', f)
            
            ftp.quit()
            
            pdf_url = f"{self.pdf_base_url}{remote_filename}"
            logger.info(f"✓ Uploaded PDF: {remote_filename}")
            return pdf_url
            
        except Exception as e:
            logger.error(f"Failed to upload PDF via FTP: {e}")
            if ftp:
                try:
                    ftp.quit()
                except:
                    pass
            return None
    
    def map_to_dandomain_schema(self, product: Dict, image_urls: List[str] = None, 
                                pdf_url: Optional[str] = None) -> Tuple[Dict, Dict]:
        """
        Map our product data to Dandomain API schema
        
        Args:
            product: Our product data from final_products.json
            image_urls: List of URLs of uploaded images (if any)
            pdf_url: URL of uploaded PDF (if any)
        
        Returns:
            Product data in Dandomain schema format
        """
        # Extract fields from our data
        product_number = product.get('PROD_NUM', '')
        # Get vendor number - ORIGINAL_VENDOR_NUM is the Bunzl vendor number used in Dandomain
        vendor_number = str(product.get('ORIGINAL_VENDOR_NUM', '') or product.get('VendorNumber', ''))
        if vendor_number == '':
            vendor_number = ''
        
        # Get product name - prefer PROD_NAME, fallback to ORIGINAL_PROD_NAME or DESC_SHORT
        product_name = product.get('PROD_NAME') or product.get('ORIGINAL_PROD_NAME') or product.get('DESC_SHORT', '')
        short_desc = product.get('DESC_SHORT', '')
        long_desc = product.get('DESC_LONG', '')
        keywords = product.get('ai_keywords', '')
        
        # Get category NUMBER (not ID!) - use primaryCategoryId which contains the category number
        category_number = product.get('primaryCategoryId', None)
        
        # Get other product data
        cost_price = product.get('PROD_COST_PRICE', 0)
        weight = product.get('PROD_WEIGHT', '')
        barcode = product.get('PROD_BARCODE_NUMBER', '')
        stock_count = product.get('STOCK_COUNT', 0)
        stock_limit = product.get('STOCK_LIMIT', 0)
        min_buy = product.get('PROD_MIN_BUY', 1)
        max_buy = product.get('PROD_MAX_BUY', 0)
        sort_order = product.get('PROD_SORT', 0)
        
        # Build Dandomain product object (basic product data)
        dandomain_product = {
            "number": product_number,
            "vendorNumber": vendor_number,
            "costPrice": cost_price,
            "weight": float(str(weight).replace(',', '.')) if weight else 0,
            "barCodeNumber": str(barcode) if barcode else "",
            "stockCount": int(stock_count) if stock_count else 0,
            "stockLimit": int(stock_limit) if stock_limit else 0,
            "minBuyAmount": int(min_buy) if min_buy else 1,
            "maxBuyAmount": int(max_buy) if max_buy else 0,
            "sortOrder": int(sort_order) if sort_order else 0,
        }
        
        # Add category if available (using category NUMBER, not ID!)
        if category_number:
            dandomain_product["categoriesIds"] = [str(category_number)]
            dandomain_product["defaultCategoryId"] = str(category_number)
        
        # Add images if uploaded
        if image_urls and len(image_urls) > 0:
            # First image as primary picture
            dandomain_product["pictureLink"] = image_urls[0]
            
            # All images in media gallery
            dandomain_product["media"] = {
                "items": [
                    {
                        "mediaUrl": url,
                        "sortOrder": idx
                    }
                    for idx, url in enumerate(image_urls)
                ]
            }
        
        # Build settings object (to be sent separately)
        settings_data = {
            "name": product_name,
            "shortDescription": short_desc,
            "longDescription": long_desc,
            "keyWords": keywords,
            "languageId": 0  # 0 = default language (Danish)
        }
        
        # Add metaDescription if available
        meta_description = product.get('META_DESCRIPTION', '')
        if meta_description:
            settings_data["metaDescription"] = meta_description
        
        # Add customer fields (FIELD_1 through FIELD_20)
        customer_fields = {}
        for i in range(1, 21):
            field_name = f"FIELD_{i}"
            field_value = product.get(field_name)
            if field_value is not None and str(field_value).strip() != '':
                # Dandomain uses field1, field2, ... naming
                customer_fields[f"field{i}"] = str(field_value)
        
        if customer_fields:
            settings_data["customerFields"] = customer_fields
        
        # Add PDF as technical document link if uploaded
        if pdf_url:
            settings_data["techDocLink"] = pdf_url
        
        return dandomain_product, settings_data
    
    def create_product_settings(self, product_number: str, settings_data: Dict, site_id: int = 26) -> Tuple[bool, Optional[str]]:
        """
        Create/update product settings (name, descriptions, etc.) via separate API endpoint
        
        Args:
            product_number: Product number
            settings_data: Settings data (name, shortDescription, longDescription, etc.)
            site_id: Site ID (default 26 for Danish site)
        
        Returns:
            (success, error_message)
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would update settings for product: {product_number}")
            return True, None
        
        try:
            headers = self._create_auth_header()
            
            # Settings endpoint: /products/{productNumber}/sites/{siteId}/settings
            settings_url = f"{self.base_url}/products/{product_number}/sites/{site_id}/settings"
            
            response = requests.post(
                settings_url,
                headers=headers,
                json=settings_data,
                timeout=30
            )
            
            response.raise_for_status()
            
            logger.info(f"✓ Updated settings for product: {product_number}")
            return True, None
            
        except requests.exceptions.HTTPError as e:
            error_msg = f"{e.response.status_code} {e.response.reason} for url: {e.response.url}"
            if e.response.text:
                error_msg += f" - {e.response.text}"
            return False, error_msg
        except Exception as e:
            return False, str(e)
    
    def create_product(self, product_data: Dict, settings_data: Dict = None) -> Tuple[bool, Optional[str]]:
        """
        Create product via Dandomain API (in two steps)
        
        Args:
            product_data: Product data in Dandomain schema format (without settings)
            settings_data: Settings data to be sent separately (optional)
        
        Returns:
            (success, error_message)
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would create product: {product_data.get('number')}")
            logger.debug(f"[DRY RUN] Payload: {json.dumps(product_data, indent=2)}")
            if settings_data:
                logger.debug(f"[DRY RUN] Settings: {json.dumps(settings_data, indent=2)}")
            return True, None
        
        try:
            headers = self._create_auth_header()
            
            # Step 1: Create basic product (without settings)
            logger.debug(f"API Payload: {json.dumps(product_data, indent=2)}")
            
            response = requests.post(
                self.products_url,
                headers=headers,
                json=product_data,
                timeout=30
            )
            
            response.raise_for_status()
            
            logger.info(f"✓ Created product: {product_data.get('number')}")
            
            # Step 2: Update settings separately if provided
            if settings_data:
                success, error = self.create_product_settings(
                    product_data.get('number'),
                    settings_data
                )
                if not success:
                    logger.warning(f"⚠️  Product created but settings update failed: {error}")
            
            return True, None
            
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                error_msg = f"{e} - {e.response.text}"
            logger.error(f"Failed to create product {product_data.get('number')}: {error_msg}")
            return False, error_msg
    
    def process_product(self, product: Dict) -> Dict:
        """
        Process single product: upload media, check existence, create/skip
        
        Returns:
            Result dict with status and details
        """
        product_number = product.get('PROD_NUM', 'UNKNOWN')
        # Get vendor number - ORIGINAL_VENDOR_NUM is the Bunzl vendor number used in Dandomain
        vendor_number = str(product.get('ORIGINAL_VENDOR_NUM', '') or product.get('VendorNumber', ''))
        if vendor_number == '':
            vendor_number = ''
        
        result = {
            'product_number': product_number,
            'status': 'pending',
            'message': '',
            'image_uploaded': False,
            'pdf_uploaded': False
        }
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing: {product_number} - {product.get('PROD_NAME', '')}")
        logger.info(f"{'='*60}")
        
        # 1. Check if product already exists
        exists, existing_data, match_field = self.check_product_exists(product_number, vendor_number)
        if exists:
            result['status'] = 'skipped'
            # Show which field matched
            if match_field == "product number":
                result['message'] = f"Product already exists (matched by product number: {product_number})"
            elif match_field == "vendor number":
                result['message'] = f"Product already exists (matched by vendor number: {vendor_number})"
            else:
                result['message'] = f"Product already exists"
            logger.warning(f"⚠️  Skipping - {result['message']}")
            return result
        
        # 2. Upload images if available (all images from product data)
        uploaded_image_urls = []
        
        # Check if product has images in JSON data
        product_images = product.get("images", [])
        if product_images:
            logger.info(f"Found {len(product_images)} images to upload")
            for idx, image_path in enumerate(product_images, 1):
                # Convert relative path to absolute (remove "images/" prefix)
                image_filename = image_path.replace("images/", "")
                
                # Look in the 1500x1500 processed images folder
                image_file = IMAGES_SOURCE_DIR / image_filename
                
                if image_file.exists():
                    # Upload with original filename
                    image_url = self.upload_image_ftp(image_file)
                    if image_url:
                        uploaded_image_urls.append(image_url)
                else:
                    logger.warning(f"Image file not found: {image_file}")
            
            result['image_uploaded'] = len(uploaded_image_urls) > 0
            logger.info(f"Uploaded {len(uploaded_image_urls)}/{len(product_images)} images")
        else:
            # Fallback: Try product-specific folder
            image_dir = DATA_OUTPUT / "images" / product_number
            image_files = []
            if image_dir.exists():
                image_files = list(image_dir.glob("*.jpg")) + list(image_dir.glob("*.png"))
            
            # If no product folder, look for images in root images/ folder matching product number
            if not image_files:
                images_root = DATA_OUTPUT / "images"
                if images_root.exists():
                    # Look for files starting with product number (e.g., e146230-*.jpg)
                    image_files = list(images_root.glob(f"{product_number.lower()}-*.jpg")) + \
                                 list(images_root.glob(f"{product_number.lower()}-*.png"))
            
            if image_files:
                for image_file in image_files:
                    image_url = self.upload_image_ftp(image_file)
                    if image_url:
                        uploaded_image_urls.append(image_url)
                result['image_uploaded'] = len(uploaded_image_urls) > 0
        
        # Use first uploaded image as primary image
        primary_image_url = uploaded_image_urls[0] if uploaded_image_urls else None
        
        # 3. Upload PDF datablad if available
        # Get clean product number (without " - Deaktiveret")
        product_number_clean = product.get('PROD_NUM_old', product_number.replace(' - Deaktiveret', ''))
        
        pdf_url = None
        # Look for PDF in data/output/pdfs folder with clean product number
        pdf_file = DATA_OUTPUT / "pdfs" / f"{product_number_clean}.pdf"
        
        if pdf_file.exists():
            pdf_url = self.upload_pdf_ftp(pdf_file, product_number_clean)
            result['pdf_uploaded'] = pdf_url is not None
        else:
            logger.debug(f"No PDF datablad found for {product_number_clean}")
        
        # 4. Map to Dandomain schema (returns product data + settings separately)
        dandomain_product, settings_data = self.map_to_dandomain_schema(product, uploaded_image_urls, pdf_url)
        
        # 5. Create product via API (in two steps: product + settings)
        success, error = self.create_product(dandomain_product, settings_data)
        
        if success:
            result['status'] = 'success'
            result['message'] = 'Product created successfully'
        else:
            result['status'] = 'error'
            result['message'] = error or 'Unknown error'
        
        return result


def main():
    """Main upload workflow"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Upload products to Dandomain CMS')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Preview what would be uploaded without actually uploading')
    parser.add_argument('--input', type=str, default='final_products.json',
                       help='Input JSON file (default: final_products.json)')
    args = parser.parse_args()
    
    logger.info("="*80)
    logger.info("Step 5: Upload to Dandomain CMS")
    logger.info("="*80)
    
    # Load products
    input_file = DATA_OUTPUT / args.input
    if not input_file.exists():
        logger.error(f"Input file not found: {input_file}")
        sys.exit(1)
    
    with open(input_file, 'r', encoding='utf-8') as f:
        products = json.load(f)
    
    logger.info(f"Loaded {len(products)} products from {args.input}")
    
    # Initialize uploader
    uploader = DandomainUploader(dry_run=args.dry_run)
    
    # Process all products
    results = []
    for product in tqdm(products, desc="Uploading products"):
        result = uploader.process_product(product)
        results.append(result)
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("UPLOAD SUMMARY")
    logger.info("="*80)
    
    success_count = sum(1 for r in results if r['status'] == 'success')
    skipped_count = sum(1 for r in results if r['status'] == 'skipped')
    error_count = sum(1 for r in results if r['status'] == 'error')
    
    logger.info(f"Total products:    {len(results)}")
    logger.info(f"Successfully created: {success_count}")
    logger.info(f"Skipped (existing):   {skipped_count}")
    logger.info(f"Errors:            {error_count}")
    
    # Save results
    results_file = DATA_OUTPUT / "upload_results.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\nResults saved to: {results_file}")
    
    if args.dry_run:
        logger.info("\n🔍 This was a DRY RUN - no actual changes were made")
        logger.info("Run without --dry-run to perform actual upload")


if __name__ == "__main__":
    main()
