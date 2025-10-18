import os
import re
import time
import glob
import shutil
import requests
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils.pdf_extractor import extract_text_from_pdf

def scrape(driver, product_number, img_name, download_folder, original_folder, **kwargs):
    try:
        search_url = f"https://dk.duni.com/en/search/?text={product_number}"
        driver.get(search_url)

        WebDriverWait(driver, 10).until(lambda d: d.execute_script('return document.readyState') == 'complete')
        is_product_page = "pageType-ProductPage" in driver.find_element(By.TAG_NAME, "body").get_attribute("class")

        if is_product_page:
            product_url = driver.current_url
        else:
            product_link = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.product-tile-link"))
            )
            product_url = product_link.get_attribute("href")
            driver.get(product_url)
            WebDriverWait(driver, 10).until(lambda d: d.execute_script('return document.readyState') == 'complete')

        soup = BeautifulSoup(driver.page_source, "html.parser")

        # 📷 IMAGES: Collect image URLs from carousel (do not download here)
        image_urls = []
        carousel = soup.select_one("div.duni-gallery-carousel-wrapper div.sticky")
        if carousel:
            image_tags = carousel.select("img")
            for img_tag in image_tags:
                img_url = img_tag.get("src")
                if img_url:
                    # Ensure high-resolution
                    img_url = img_url.replace("/96/", "/1200/").replace("/onlineinsp/96/", "/onlineinsp/1200/")
                    if img_url.startswith("http"):
                        image_urls.append(img_url)

        # 📄 PDF HANDLING
        supplier_text = ""
        # Instead of using the broken href, find the downloaded PDF with matching pattern
        pdf_glob = os.path.join(download_folder, f"{product_number}*.pdf")
        matched_files = sorted(glob.glob(pdf_glob), key=os.path.getmtime, reverse=True)

        if matched_files:
            pdf_path = matched_files[0]
            try:
                supplier_text = extract_text_from_pdf(pdf_path)
                if supplier_text:
                    return supplier_text.strip(), product_url, image_urls
            except Exception as e:
                pass  # Only log errors if needed
        desc_tag = soup.select_one("div.description div.summary.js-summary p.summary-collapse.read-more")
        if desc_tag:
            supplier_text = re.sub(r"\s+", " ", desc_tag.get_text(strip=True))
        return supplier_text.strip(), product_url, image_urls
    except Exception as e:
        return "", "", []

def extract_supplier_info(row, original_folder, driver=None, download_folder=None):
    """
    Vendor-specific extraction: returns a dict with supplier_info, product_url, image_urls, pdf_url, image_zip_url
    """
    product_number = str(row.get("PrimaryVendorItemID", "")).strip()
    img_name = str(row.get("IMG_NAME", "")).strip()
    if download_folder is None:
        download_folder = os.path.join(os.path.expanduser("~"), "Downloads")
    supplier_info = ""
    product_url = ""
    image_urls = []
    if driver is not None:
        supplier_info, product_url, image_urls = scrape(driver, product_number, img_name, download_folder, original_folder)
    return {
        "supplier_info": supplier_info,
        "product_url": product_url,
        "image_urls": image_urls,
        "pdf_url": "",
        "image_zip_url": None
    }

def extract_product_data_from_row(row, original_folder, driver=None, download_folder=None):
    """
    Standard interface for new main.py. Extracts product data from a row and returns a dict.
    Uses the vendor-specific extract_supplier_info() if driver is provided, otherwise returns basic info.
    """
    prod_num = str(row.get("PROD_NUM", "")).strip()
    img_name = str(row.get("IMG_NAME", "")).strip()
    supplier_info = ""
    product_url = ""
    if driver is not None:
        result = extract_supplier_info(row, original_folder, driver, download_folder)
        supplier_info = result.get("supplier_info", "")
        product_url = result.get("product_url", "")
    # else: just return empty info (or fallback logic)
    return {
        "PROD_NUM": prod_num,
        "product_name": img_name,
        "image_name": img_name,
        "supplier_information": supplier_info,
        "product_url": product_url
    }