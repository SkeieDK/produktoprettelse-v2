import time
import logging
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def scrape(driver, product_number):
    """
    PlusPack vendor module - THIN VERSION
    Only navigates and finds URLs. Main.py handles all downloads/processing.
    
    Returns: {
        "product_url": str,
        "image_zip_url": str or None,
        "pdf_url": str or None
    }
    """
    result = {
        "product_url": "",
        "image_zip_url": None,
        "pdf_url": None
    }
    
    try:
        print(f"\n🔍 Searching PlusPack for: {product_number}")
        search_url = f"https://www.pluspack.com/products/global-search/{product_number}"
        driver.get(search_url)
        time.sleep(1.5)

        # Navigate to product page
        product_link = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "ul.product-grid-container a"))
        )
        product_url = product_link.get_attribute("href")
        result["product_url"] = product_url
        print(f"🔗 Product page found")
        driver.get(product_url)
        time.sleep(1.5)

        # Find image ZIP URL and PDF URL from page
        soup = BeautifulSoup(driver.page_source, "html.parser")
        
        # Search for image ZIP link
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            aria_label = link.get("aria-label", "").lower()
            if "image" in aria_label and ".zip" in href:
                result["image_zip_url"] = href
                print(f"📥 Image ZIP URL found")
                break
        
        # Search for PDF link
        for link in soup.find_all("a", href=True):
            href = link.get("href", "")
            aria_label = link.get("aria-label", "").lower()
            if "data sheet" in aria_label or href.endswith(".pdf"):
                result["pdf_url"] = href
                print(f"📄 PDF URL found")
                break

        return result

    except Exception as e:
        logging.error(f"❌ Error scraping PlusPack: {e}")
        print(f"❌ Error scraping PlusPack: {e}")
        return result


def extract_supplier_info(row, original_folder, driver=None, download_folder=None):
    """
    Vendor-specific extraction wrapper.
    Returns dict with URLs only - main.py handles all downloads/processing.
    """
    product_number = str(row.get("PrimaryVendorItemID", "")).strip()
    
    result = {
        "product_url": "",
        "image_zip_url": None,
        "pdf_url": None
    }
    
    if driver is not None and product_number:
        result = scrape(driver, product_number)
    
    return result