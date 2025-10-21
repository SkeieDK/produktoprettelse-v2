import os
import re
import time
import glob
import shutil
import logging
import requests
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from supplier_pi.utils.pdf_extractor import extract_text_from_pdf


def handle_cookie_consent(driver, screenshot_dir="."):
    """Handle Vikan’s cookie consent dialog (if present)."""
    btn_id = "CybotCookiebotDialogBodyLevelOptinAllowallSelection"
    try:
        btns = driver.find_elements(By.ID, btn_id)
        if btns and btns[0].is_displayed():
            btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, btn_id))
            )
            btn.click()
            WebDriverWait(driver, 10).until_not(
                EC.presence_of_element_located((By.ID, "CybotCookiebotDialog"))
            )
            logging.info("✅ Cookie consent accepted.")
        else:
            logging.info("ℹ️ No visible cookie consent banner found, nothing to do.")
    except Exception as e:
        ts = int(time.time())
        path = os.path.join(screenshot_dir, f"cookie_consent_error_{ts}.png")
        driver.save_screenshot(path)
        logging.warning(f"⚠️ Cookie consent handling failed, screenshot saved to {path}: {e}")


def scrape(driver, product_number, img_name, download_folder, original_folder, image_folder, **kwargs):
    """
    Scrape Vikan.com - find product and resource URLs only.
    Main.py handles downloading images and PDFs.
    Returns: {"product_url": str, "image_urls": [...], "pdf_url": str or None}
    """
    result = {"product_url": "", "image_urls": [], "pdf_url": None}

    try:
        driver.set_window_size(1600, 1000)
        driver.get("https://www.vikan.com/dk")
        handle_cookie_consent(driver)

        # Search for product
        search = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'input[title="Søg"]'))
        )
        search.clear()
        search.send_keys(product_number)
        logging.info(f"🔍 Searching Vikan for: {product_number}")
        
        try:
            search_result = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, f"a[href*='{product_number}']"))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", search_result)
            driver.execute_script("arguments[0].click();", search_result)
        except Exception as e:
            logging.error(f"Search result not found: {e}")
            raise
        
        result["product_url"] = driver.current_url
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        logging.info("🔗 Product page found")

        # Parse page
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Find image URLs (don't download, just collect)
        main_img = soup.select_one(".product-feature__figure img")
        if main_img and main_img.get("src"):
            result["image_urls"].append(main_img["src"])

        for item in soup.select(".product-carousel__gallery .owl-item a.fancybox")[:3]:
            href = item.get("href")
            if href:
                result["image_urls"].append(href)

        if result["image_urls"]:
            logging.info(f"📥 Found {len(result['image_urls'])} image URLs")

        # Find PDF URL (don't download, just collect)
        datasheet_pdf = None
        for block in soup.select('div.product-downloads__sub-block'):
            header = block.select_one('div.product-downloads__sub-header')
            if header and 'Produktdatablad' in header.get_text():
                for a in block.select('a[href$=".pdf"]'):
                    href = a.get('href', '')
                    if 'ProductSheet_DAN' in href:
                        datasheet_pdf = href
                        break
            if datasheet_pdf:
                break
        
        if datasheet_pdf:
            result["pdf_url"] = datasheet_pdf
            if not result["pdf_url"].startswith('http'):
                result["pdf_url"] = f"https://www.vikan.com{result['pdf_url']}"
            logging.info("📄 PDF URL found")
        else:
            # Fallback PDF
            pdf_link = soup.find('a', href=lambda x: x and str(x).endswith('.pdf'))
            if pdf_link and pdf_link.get('href'):
                result["pdf_url"] = pdf_link['href']
                if not result["pdf_url"].startswith('http'):
                    result["pdf_url"] = f"https://www.vikan.com{result['pdf_url']}"
                logging.info("📄 PDF URL found (fallback)")

        return result
    
    except Exception as e:
        logging.error(f"❌ Error scraping Vikan: {e}")
        return result


def extract_supplier_info(row, original_folder, driver=None, download_folder=None):
    """Wrapper for main.py - returns URLs dict."""
    product_number = str(row.get("PrimaryVendorItemID", "")).strip()
    img_name = str(row.get("IMG_NAME", "")).strip()
    
    if download_folder is None:
        download_folder = os.path.join(os.path.expanduser("~"), "Downloads")
    
    result = {"product_url": "", "image_urls": [], "pdf_url": None}
    
    if driver is not None and product_number and img_name:
        result = scrape(driver, product_number, img_name, download_folder, original_folder, None)
    
    return result

