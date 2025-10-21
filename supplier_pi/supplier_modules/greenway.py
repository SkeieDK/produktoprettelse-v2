import os
import logging
import time
import requests
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def scrape(driver, product_number, img_name, download_folder, original_folder):
    try:
        logging.info(f"\n🔍 Searching Greenway for: {product_number}")
        search_url = "https://greenway-denmark.dk/"
        driver.get(search_url)
        time.sleep(2)

        # 1. Find søgefelt og indtast produktnummer
        search_input = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='q']"))
        )
        search_input.clear()
        search_input.send_keys(product_number)
        time.sleep(2)

        # 2. Udfør søgning og klik på første produkt manuelt
        logging.warning("⚠️ Dropdown autocomplete not found – submitting search and clicking first product manually.")
        search_input.submit()
        time.sleep(3)
        try:
            link = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "ol.products.list.items.product-items li.item.product a.product-item-link"))
            )
            driver.get(link.get_attribute("href"))
            time.sleep(2)
        except Exception as e:
            logging.error(f"❌ Could not find product manually: {e}")
            return "", ""

        product_url = driver.current_url
        logging.info(f"🔗 Product page: {product_url}")

        # Luk popup via SVG title hvis den vises
        try:
            popup_close_btn = WebDriverWait(driver, 2).until(
                EC.presence_of_element_located((By.XPATH, "//title[text()='Close dialog']/parent::*"))
            )
            driver.execute_script("arguments[0].click();", popup_close_btn)
            logging.info("✅ Closed popup using SVG title fallback.")
            time.sleep(0.5)
        except Exception as e:
            logging.warning(f"⚠️ Popup not found or could not be closed: {e}")

        # 3. Klik på thumbnail for at åbne billedvisning og gem alle billeder
        try:
            thumb = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".product.media img"))
            )
            thumb.click()
            time.sleep(1)

            seen_urls = set()
            image_count = 0

            while True:
                img_tag = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "img.mfp-img"))
                )
                img_url = img_tag.get_attribute("src")

                if img_url in seen_urls:
                    break
                seen_urls.add(img_url)

                image_path = os.path.join(original_folder, f"{img_name}{'-' + str(image_count + 1) if image_count > 0 else ''}.jpg")
                try:
                    r = requests.get(img_url, timeout=10)
                    with open(image_path, "wb") as f:
                        f.write(r.content)
                    logging.info(f"✅ Saved image: {image_path}")
                except Exception as e:
                    logging.warning(f"⚠️ Failed to download image: {img_url} - {e}")

                image_count += 1

                try:
                    next_btn = WebDriverWait(driver, 2).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "button.mfp-arrow.mfp-arrow-right"))
                    )
                    driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
                    time.sleep(0.2)
                    driver.execute_script("arguments[0].click();", next_btn)
                except Exception as e:
                    logging.error(f"❌ Could not click next button: {e}")
                    break

        except Exception as e:
            logging.warning(f"⚠️ Failed to process images: {e}")

        # 4. Hent teknisk info fra "Produkt detaljer"
        try:
            soup = BeautifulSoup(driver.page_source, "html.parser")
            details_section = soup.select_one("#product-attribute-specs-table")
            if not details_section:
                raise Exception("Couldn't find product info section.")

            text = details_section.get_text(separator=" ", strip=True)
            logging.info("📝 Text extracted from product details.")
        except Exception as e:
            logging.warning(f"⚠️ Failed to extract product text: {e}")
            text = ""

        return text, product_url

    except Exception as e:
        logging.error(f"❌ Error while scraping Greenway: {e}")
        return "", ""
