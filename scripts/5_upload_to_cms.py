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

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_OUTPUT = DATA_DIR / "output"
LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Setup logging
log_file = LOGS_DIR / "5_upload_to_cms.log"
logging.basicConfig(
    level=logging.INFO,
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
        self.ftp_host = os.getenv('FTP_HOST', 'webshopdk.dk')
        self.ftp_user = os.getenv('FTP_USER', '')
        self.ftp_password = os.getenv('FTP_PASSWORD', '')
        
        if not self.api_key:
            raise ValueError("API_KEY not found in environment variables!")
        
        # API endpoints
        self.base_url = "https://engrosrengoringsmidler.dk/admin/WebAPI/v2"
        self.products_url = f"{self.base_url}/products"
        
        # FTP paths
        self.ftp_image_path = "/images/produkt_billeder/"
        self.ftp_pdf_path = "/images/produkt_billeder/"  # Same folder or different?
        
        # Image base URL (where uploaded images will be accessible)
        self.image_base_url = "https://engrosrengoringsmidler.dk/images/produkt_billeder/"
        
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
        Check if product already exists by product number or vendor number
        
        Returns:
            (exists, product_data, match_field) - True if exists, along with existing product data and which field matched
        """
        try:
            headers = self._create_auth_header()
            
            # Search by product number
            params = {'number': product_number}
            response = requests.get(self.products_url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            items = data.get('items', [])
            
            if items:
                logger.info(f"Product {product_number} already exists (found by number)")
                return True, items[0], "product number"
            
            # Search by vendor number if not found by product number
            if vendor_number:
                params = {'vendorNumber': vendor_number}
                response = requests.get(self.products_url, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                items = data.get('items', [])
                
                if items:
                    logger.info(f"Product with vendor number {vendor_number} already exists")
                    return True, items[0], "vendor number"
            
            return False, None, None
            
        except Exception as e:
            logger.error(f"Error checking if product exists: {e}")
            # On error, assume it doesn't exist to avoid blocking uploads
            return False, None, None
    
    def upload_image_ftp(self, local_path: Path, product_number: str) -> Optional[str]:
        """
        Upload image to Dandomain FTP server
        
        Args:
            local_path: Path to local image file
            product_number: Product number (used for filename)
        
        Returns:
            URL of uploaded image, or None if upload failed
        """
        if not local_path.exists():
            logger.warning(f"Image file not found: {local_path}")
            return None
        
        # Generate remote filename (e.g., E146223.jpg)
        file_extension = local_path.suffix
        remote_filename = f"{product_number}{file_extension}"
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would upload {local_path.name} → {self.ftp_image_path}{remote_filename}")
            return f"{self.image_base_url}{remote_filename}"
        
        try:
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
            return None
    
    def upload_pdf_ftp(self, local_path: Path, product_number: str) -> Optional[str]:
        """
        Upload PDF (datablad) to Dandomain FTP server
        
        Args:
            local_path: Path to local PDF file
            product_number: Product number (used for filename)
        
        Returns:
            URL of uploaded PDF, or None if upload failed
        """
        if not local_path.exists():
            logger.warning(f"PDF file not found: {local_path}")
            return None
        
        # Generate remote filename (e.g., E146223_datablad.pdf)
        remote_filename = f"{product_number}_datablad.pdf"
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would upload {local_path.name} → {self.ftp_pdf_path}{remote_filename}")
            return f"{self.image_base_url}{remote_filename}"
        
        try:
            # Connect to FTP
            ftp = FTP(self.ftp_host)
            ftp.login(self.ftp_user, self.ftp_password)
            
            # Change to PDF directory
            ftp.cwd(self.ftp_pdf_path)
            
            # Upload file
            with open(local_path, 'rb') as f:
                ftp.storbinary(f'STOR {remote_filename}', f)
            
            ftp.quit()
            
            pdf_url = f"{self.image_base_url}{remote_filename}"
            logger.info(f"✓ Uploaded PDF: {remote_filename}")
            return pdf_url
            
        except Exception as e:
            logger.error(f"Failed to upload PDF via FTP: {e}")
            return None
    
    def map_to_dandomain_schema(self, product: Dict, image_url: Optional[str] = None, 
                                pdf_url: Optional[str] = None) -> Dict:
        """
        Map our product data to Dandomain API schema
        
        Args:
            product: Our product data from final_products.json
            image_url: URL of uploaded image (if any)
            pdf_url: URL of uploaded PDF (if any)
        
        Returns:
            Product data in Dandomain schema format
        """
        # Extract fields from our data
        product_number = product.get('PROD_NUM', '')
        vendor_number = product.get('VendorNumber', '')
        product_name = product.get('PROD_NAME', '')
        short_desc = product.get('DESC_SHORT', '')
        long_desc = product.get('DESC_LONG', '')
        keywords = product.get('ai_keywords', '')
        primary_category_id = product.get('primaryCategoryId', '')
        
        # Build Dandomain product object
        dandomain_product = {
            "number": product_number,
            "vendorNumber": vendor_number,
            "primaryCategoryId": primary_category_id,
            
            # Settings (name, descriptions, etc.) - multi-language support
            "settings": {
                "items": [
                    {
                        "name": product_name,
                        "shortDescription": short_desc,
                        "longDescription": long_desc,
                        "keyWords": keywords,
                        "languageId": 0  # 0 = default language (Danish)
                    }
                ]
            }
        }
        
        # Add image if uploaded
        if image_url:
            dandomain_product["pictureLink"] = image_url
            
            # Also add to media gallery
            dandomain_product["media"] = {
                "items": [
                    {
                        "mediaUrl": image_url,
                        "sortOrder": 0
                    }
                ]
            }
        
        # Add PDF as technical document link if uploaded
        if pdf_url:
            if "settings" in dandomain_product and "items" in dandomain_product["settings"]:
                dandomain_product["settings"]["items"][0]["techDocLink"] = pdf_url
                dandomain_product["settings"]["items"][0]["techDocLinkText"] = "Datablad"
        
        return dandomain_product
    
    def create_product(self, product_data: Dict) -> Tuple[bool, Optional[str]]:
        """
        Create product via Dandomain API
        
        Args:
            product_data: Product data in Dandomain schema format
        
        Returns:
            (success, error_message)
        """
        if self.dry_run:
            logger.info(f"[DRY RUN] Would create product: {product_data.get('number')}")
            logger.debug(f"[DRY RUN] Payload: {json.dumps(product_data, indent=2)}")
            return True, None
        
        try:
            headers = self._create_auth_header()
            
            response = requests.post(
                self.products_url,
                headers=headers,
                json=product_data,
                timeout=30
            )
            
            response.raise_for_status()
            
            logger.info(f"✓ Created product: {product_data.get('number')}")
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
        vendor_number = product.get('VendorNumber', '')
        
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
        
        # 2. Upload image if available
        image_url = None
        image_dir = DATA_DIR / "images" / product_number
        if image_dir.exists():
            # Find first image file
            image_files = list(image_dir.glob("*.jpg")) + list(image_dir.glob("*.png"))
            if image_files:
                image_url = self.upload_image_ftp(image_files[0], product_number)
                result['image_uploaded'] = image_url is not None
        
        # 3. Upload PDF if available
        pdf_url = None
        pdf_dir = DATA_DIR / "pdfs" / product_number
        if pdf_dir.exists():
            pdf_files = list(pdf_dir.glob("*.pdf"))
            if pdf_files:
                pdf_url = self.upload_pdf_ftp(pdf_files[0], product_number)
                result['pdf_uploaded'] = pdf_url is not None
        
        # 4. Map to Dandomain schema
        dandomain_product = self.map_to_dandomain_schema(product, image_url, pdf_url)
        
        # 5. Create product via API
        success, error = self.create_product(dandomain_product)
        
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
