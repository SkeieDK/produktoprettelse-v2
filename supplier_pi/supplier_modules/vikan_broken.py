import os
import logging
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def scrape(driver, product_number, img_name, download_folder, original_folder, image_folder, **kwargs):
    """
    Scrape Vikan.com - finds URLs for images and PDF.
    Returns: {"product_url": str, "image_urls": [...], "pdf_url": str or None}
    """
    result = {"product_url": "", "image_urls": [], "pdf_url": None}

    try:
        driver.get("https://www.vikan.com/dk")
        
        # Try to dismiss cookie banner (non-critical)
        try:
            btn = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.ID, "CybotCookiebotDialogBodyLevelOptinAllowallSelection"))
            )
            btn.click()
        except:
            pass
        
        # Search for product
        search_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[title="Søg"]'))
        )
        search_input.send_keys(product_number)
        logging.info(f"🔍 Searching Vikan for: {product_number}")
        
        # Click search result with scroll into view (needed for interactability)
        result_link = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, f"a[href*='{product_number}']"))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", result_link)
        driver.execute_script("arguments[0].click();", result_link)
        
        result["product_url"] = driver.current_url
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        print(f"🔗 Product page found")

        # Parse page
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Find images (main + carousel)
        main_img = soup.select_one(".product-feature__figure img")
        if main_img and main_img.get("src"):
            result["image_urls"].append(main_img["src"])

        for item in soup.select(".product-carousel__gallery .owl-item a.fancybox")[:3]:
            href = item.get("href")
            if href:
                result["image_urls"].append(href)

        if result["image_urls"]:
            print(f"📥 Found {len(result['image_urls'])} image URLs")

        # Find PDF (Danish datasheet preferred, fallback to any PDF)
        for link in soup.select('div.product-downloads__sub-block a[href$=".pdf"]'):
            href = link.get('href', '')
            if 'ProductSheet_DAN' in href:
                result["pdf_url"] = href
                break

        if not result["pdf_url"]:
            pdf_links = [link.get('href') for link in soup.select('a[href$=".pdf"]') if link.get('href')]
            if pdf_links:
                result["pdf_url"] = pdf_links[0]

        # Make PDF URL absolute
        if result["pdf_url"] and not result["pdf_url"].startswith('http'):
            result["pdf_url"] = f"https://www.vikan.com{result['pdf_url']}"

        if result["pdf_url"]:
            print(f"📄 PDF URL found")

        return result

    except Exception as e:
        logging.error(f"❌ Error scraping Vikan: {e}")
        print(f"❌ Error scraping Vikan: {e}")
        return result


def extract_supplier_info(row, original_folder, driver=None, download_folder=None):
    """Wrapper for main.py."""
    product_number = str(row.get("PrimaryVendorItemID", "")).strip()
    
    if download_folder is None:
        download_folder = os.path.join(os.path.expanduser("~"), "Downloads")
    
    result = {"product_url": "", "image_urls": [], "pdf_url": None}
    
    if driver is not None and product_number:
        result = scrape(driver, product_number, str(row.get("IMG_NAME", "")).strip(), 
                       download_folder, original_folder, None)
    
    return result