import sys
import os
import importlib
import pandas as pd
import logging
import json
import zipfile
import shutil
from utils.image_processor import resize_and_save_all_images
import requests
from utils.pdf_extractor import extract_text_from_pdf

# Ensure the parent directory is in sys.path for relative imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# === Setup folders and file paths ===
user_profile = os.path.expanduser("~")
excel_path = os.path.join(user_profile, "OneDrive - Bunzl Continental Europe", "Documents - Bonvig", "Produktoprettelser", "produktoprettelse_bulk_AI.xlsx")
download_folder = os.path.join(user_profile, "Downloads")
image_folder = os.path.join(user_profile, "OneDrive - Bunzl Continental Europe", "Documents - Bonvig", "Produktbilleder_1500x1500")
original_folder = os.path.join(user_profile, "OneDrive - Bunzl Continental Europe", "Documents - Bonvig", "original billeder", "Produktbilleder")
output_csv_path = os.path.join(user_profile, "OneDrive - Bunzl Continental Europe", "Documents - Bonvig", "Produktoprettelser", "supplier_info_output.csv")

os.makedirs(download_folder, exist_ok=True)
os.makedirs(image_folder, exist_ok=True)
os.makedirs(original_folder, exist_ok=True)

# === Logging ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("main.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# Load vendor map from JSON (case-insensitive keys)
with open(os.path.join(os.path.dirname(__file__), 'utils', 'vendor_map.json'), encoding='utf-8') as f:
    raw_vendor_map = json.load(f)
    # Create a case-insensitive mapping
    vendor_map = {k.strip().lower(): v for k, v in raw_vendor_map.items()}

def get_vendor_module(vendor_name):
    # Use case-insensitive vendor_map to get the correct module name
    module_name = vendor_map.get(vendor_name.strip().lower(), None)
    if not module_name:
        logging.error(f"No vendor module mapping found for '{vendor_name}' in vendor_map.json (case-insensitive)")
        return None
    module_path = f"supplier_modules.{module_name.lower()}"
    try:
        return importlib.import_module(module_path)
    except ModuleNotFoundError as e:
        logging.error(f"No vendor module found for '{vendor_name}' (tried '{module_path}'): {e}")
        return None

def process_vendor_row(vendor_name, row, driver=None, download_folder=None):
    vendor_module = get_vendor_module(vendor_name)
    product_number = str(row.get("PrimaryVendorItemID", "")).strip()
    img_name = str(row.get("IMG_NAME", "")).strip()
    prod_num = str(row.get("PROD_NUM", "")).strip()
    image_url = str(row.get("ImageURL", "")).strip()
    supplier_info = ""
    product_url = ""
    fallback_pdfs = []
    pdf_folder = os.path.join(user_profile, "OneDrive - Bunzl Continental Europe", "Documents - Bonvig", "Produktoprettelser",  "prod_pdf_information")
    pdf_columns = [
        "DatabladMGURL", "DatabladURL", "DeclarationOfComplianceURL", "ProductDataSheetURL", "SDSDocumentURL", "MSDSDocumentURL"
    ]
    priority_pdf_column = "ProductDataSheetURL"
    image_files = []
    image_sizes = []
    supplier_info_source = "none"
    
    if vendor_module is not None:
        # Use new centralized approach for all vendors
        result = vendor_module.extract_supplier_info(row, original_folder, driver=driver, download_folder=download_folder)
        if isinstance(result, dict):
            product_url = result.get("product_url", "")
            # Handle different image formats
            image_zip_url = result.get("image_zip_url")
            image_urls = result.get("image_urls", [])
            logging.info(f"Image URLs for {product_number}: {image_urls}")
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
        if pd.notna(row.get(priority_pdf_column)):
            url = str(row.get(priority_pdf_column)).strip()
            colname = priority_pdf_column.replace("URL", "")
            prod_short = prod_num.split(" - ")[0]
            filename = f"{prod_short}-{colname}.pdf"
            path = os.path.join(pdf_folder, filename)
            try:
                r = requests.get(url, timeout=10)
                if r.status_code == 200:
                    with open(path, "wb") as f:
                        f.write(r.content)
                    fallback_pdfs.append(path)
            except Exception as e:
                logging.error(f"Failed to fetch prioritized {url}: {e}")
        for col in [c for c in pdf_columns if c != priority_pdf_column]:
            url = row.get(col)
            if pd.notna(url):
                url = str(url).strip()
                colname = col.replace("URL", "")
                prod_short = prod_num.split(" - ")[0]
                filename = f"{prod_short}-{colname}.pdf"
                path = os.path.join(pdf_folder, filename)
                test_urls = [url]
                if "DeclarationOfCompliance/" in url:
                    test_urls.append(url.replace("DeclarationOfCompliance/", "DeclarationOfConformity/"))
                for test_url in test_urls:
                    try:
                        r = requests.get(test_url, timeout=10)
                        if r.status_code == 200:
                            with open(path, "wb") as f:
                                f.write(r.content)
                            fallback_pdfs.append(path)
                            break
                    except Exception as e:
                        logging.error(f"Failed to fetch {test_url}: {e}")
        for path in fallback_pdfs:
            try:
                text = extract_text_from_pdf(path)
                if text.strip():
                    supplier_info = text
                    supplier_info_source = "pdf"
                    logging.info(f"Extracted info from fallback PDF: {os.path.basename(path)}")
                    break
            except Exception as e:
                logging.warning(f"Could not extract from {path}: {e}")
        if image_url:
            try:
                response = requests.get(image_url, timeout=10)
                if response.status_code == 200:
                    original_path = os.path.join(original_folder, f"{img_name}.jpg")
                    with open(original_path, "wb") as f:
                        f.write(response.content)
                    logging.info(f"Fallback image saved: {original_path}")
                    resize_and_save_all_images(original_folder, image_folder, img_name)
                else:
                    logging.warning(f"Could not fetch image: {image_url}")
            except Exception as e:
                logging.error(f"Error during fallback image processing: {e}")
        else:
            logging.error(f"Missing ImageURL for fallback image processing in row {prod_num}")
    supplier_info = clean_supplier_info(supplier_info)
    # Gather image info for summary
    if img_name:
        for file in os.listdir(original_folder):
            if file.startswith(img_name) and file.lower().endswith((".jpg", ".jpeg", ".png")):
                path = os.path.join(original_folder, file)
                if os.path.exists(path):
                    image_files.append(path)
                    try:
                        from PIL import Image
                        with Image.open(path) as im:
                            image_sizes.append(im.size)
                    except Exception:
                        image_sizes.append("unknown")
    supplier_data = {
        "product_number": prod_num,
        "product_url": product_url,
        "supplier_info": supplier_info
    }
    run_summary = {
        "product_number": prod_num,
        "status": "success" if supplier_info and product_url else "partial" if supplier_info or product_url else "failed",
        "images_found": len(image_files),
        "image_sizes": image_sizes,
        "supplier_info_source": supplier_info_source,
        "missing_supplier_info": not bool(supplier_info),
        "missing_product_url": not bool(product_url)
    }
    return supplier_data, run_summary

# If you want to keep cleaning, use a local function instead:
def clean_supplier_info(text):
    if not isinstance(text, str):
        return text
    import re
    cleaned = re.sub(r'[\r\n\t]+', ' ', text)
    cleaned = re.sub(r' +', ' ', cleaned)
    return cleaned.strip()

def extract_pdf_text(pdf_url, download_folder, product_number):
    """
    Download PDF from URL and extract text.
    Returns: extracted text or empty string
    """
    if not pdf_url or not pdf_url.strip():
        return ""
    
    try:
        pdf_path = os.path.join(download_folder, f"{product_number}.pdf")
        r = requests.get(pdf_url, timeout=10)
        if r.status_code == 200:
            with open(pdf_path, "wb") as f:
                f.write(r.content)
            text = extract_text_from_pdf(pdf_path)
            if text:
                logging.info(f"✅ Extracted PDF text from {pdf_url}")
                return text.replace("\n", " ").strip()
    except Exception as e:
        logging.warning(f"⚠️ Failed to extract PDF text: {e}")
    
    return ""

def download_and_extract_images(image_zip_url, product_number, img_name, download_folder, original_folder):
    """
    Download image ZIP from URL, extract images, and save to original_folder.
    Centralized image handling for all vendor modules.
    Returns: number of images extracted
    """
    if not image_zip_url or not image_zip_url.strip():
        logging.warning(f"❌ No image ZIP URL provided for product {product_number}")
        return 0
    
    try:
        print(f"📥 Downloading image ZIP...")
        zip_path = os.path.join(download_folder, f"{product_number}_images.zip")
        extract_path = os.path.join(download_folder, f"{product_number}_extracted_images")
        
        # Download ZIP
        r = requests.get(image_zip_url, timeout=10)
        if r.status_code != 200:
            logging.warning(f"⚠️ Failed to download image ZIP: HTTP {r.status_code}")
            return 0
        
        with open(zip_path, "wb") as f:
            f.write(r.content)
        
        # Extract ZIP
        if os.path.exists(extract_path):
            shutil.rmtree(extract_path)
        os.makedirs(extract_path, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_path)
        
        # Move images to original_folder
        extracted_files = os.listdir(extract_path)
        img_counter = 0
        for file in extracted_files:
            if file.lower().endswith((".jpg", ".jpeg", ".png")):
                source = os.path.join(extract_path, file)
                suffix = f"-{img_counter + 1}" if img_counter > 0 else ""
                target = os.path.join(original_folder, f"{img_name}{suffix}.jpg")
                shutil.move(source, target)
                logging.info(f"✅ Saved image: {target}")
                img_counter += 1
        
        # Cleanup
        if os.path.exists(zip_path):
            os.remove(zip_path)
        if os.path.exists(extract_path):
            shutil.rmtree(extract_path)
        
        print(f"✅ Extracted {img_counter} images")
        return img_counter
        
    except Exception as e:
        logging.error(f"❌ Error downloading/extracting images: {e}")
        return 0

def download_images_from_urls(image_urls, product_number, img_name, download_folder, original_folder):
    """
    Download images directly from URL list (for vendors like Vikan).
    Returns: number of images downloaded
    """
    if not image_urls or not isinstance(image_urls, list):
        logging.warning(f"❌ No image URLs provided for product {product_number}")
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
                path = os.path.join(original_folder, f"{img_name}{suffix}{ext}")
                with open(path, "wb") as f:
                    shutil.copyfileobj(resp.raw, f)
                logging.info(f"✅ Saved image: {path}")
                img_counter += 1
            except Exception as e:
                logging.warning(f"⚠️ Could not download image {url}: {e}")
        
        print(f"✅ Downloaded {img_counter} images")
        return img_counter
        
    except Exception as e:
        logging.error(f"❌ Error downloading images: {e}")
        return 0

if __name__ == "__main__":
    try:
        # === Load JSON data ===
        json_path = os.path.join(os.path.dirname(__file__), '..', 'cache', 'processed_products.json')
        json_path = os.path.abspath(json_path)
        
        if not os.path.exists(json_path):
            raise FileNotFoundError(f"JSON file not found: {json_path}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            products = json.load(f)
        
        logging.info(f"Loaded {len(products)} products from {json_path}")

        # === Set up Selenium driver ===
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920x1080")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--remote-debugging-port=9222")
        options.add_experimental_option("prefs", {"download.prompt_for_download": False})
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        supplier_data_list = []
        run_summary_list = []
        for index, product in enumerate(products):
            vendor_name = str(product.get("PrimaryVendorName", "")).strip().lower()
            if not vendor_name:
                continue
            try:
                supplier_data, run_summary = process_vendor_row(vendor_name, product, driver=driver, download_folder=download_folder)
                supplier_data_list.append(supplier_data)
                run_summary_list.append(run_summary)
            except Exception as e:
                run_summary_list.append({
                    "product_number": product.get("PROD_NUM", ""),
                    "status": "failed",
                    "missing_supplier_info": True,
                    "missing_product_url": True,
                    "error": str(e)
                })
        # Print run summary report
        print("\n=== Run Summary ===")
        for item in run_summary_list:
            print(f"Product: {item['product_number']}")
            print(f"  Status: {item['status']}")
            print(f"  Images found: {item['images_found']}")
            if item['images_found'] > 0:
                print(f"  Image sizes: {item['image_sizes']}")
            print(f"  Supplier info source: {item['supplier_info_source']}")
            if item.get('missing_supplier_info'):
                print("  Missing supplier info")
            if item.get('missing_product_url'):
                print("  Missing product URL")
            if item.get('error'):
                print(f"  Error: {item['error']}")
            print()
        # Save supplier data to JSON
        output_json_path = os.path.join(user_profile, "OneDrive - Bunzl Continental Europe", "Documents - Bonvig", "Produktoprettelser", "supplier_info_output.json")
        try:
            with open(output_json_path, 'w', encoding='utf-8') as f:
                json.dump(supplier_data_list, f, ensure_ascii=False, indent=4)
            print(f"✅ Supplier info saved to {output_json_path}")
        except Exception as e:
            logging.error(f"Failed to save supplier info to JSON: {e}")
            print(f"❌ Failed to save supplier info: {e}")
        driver.quit()

    except Exception as e:
        logging.error(f"Fatal error in main execution: {e}")
        print(f"❌ Fatal error: {e}")
        try:
            driver.quit()
        except:
            pass
        import sys
        sys.exit(1)

