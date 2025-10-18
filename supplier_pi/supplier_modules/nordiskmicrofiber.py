import os
import shutil
import logging

__all__ = ["scrape"]

def _log(msg):
    logging.info(f"[nordiskmicrofiber] {msg}")

def scrape(product_number, img_name, download_folder, original_folder, image_folder, **kwargs):
    """
    Scraper for nordiskmicrofiber.dk:
      - Søger efter produktet
      - Navigerer til produktsiden
      - Downloader hovedbillede (Download billeder)
      - Downloader datablad (Download datablad)
      - Henter produktinfo fra content-holder
    Returnerer: (supplier_text, product_url)
    """
    from bs4 import BeautifulSoup
    import requests
    supplier_text = ""
    product_url = ""
    try:
        from utils.pdf_extractor import extract_text_from_pdf
        search_url = f"https://nordiskmicrofiber.dk/?s={product_number}"
        _log(f"Søger på: {search_url}")
        def is_product_link(href):
            # Udeluk søge-URL og tag kun links der ligner produktsider
            if not href:
                return False
            if f"?s={product_number}" in href:
                return False
            if "/kategorier/" in href or "/produkter/" in href:
                return product_number.lower() in href.lower()
            return False
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            options = Options()
            #options.add_argument('--headless')  # Kør med GUI for at debugge
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            import time
            driver = webdriver.Chrome(options=options)
            driver.get(search_url)
            current_url = driver.current_url
            _log(f"Efter driver.get(): current_url = {current_url}")
            # Prøv at acceptere cookie-popup hvis den findes
            try:
                cookie_btn = driver.find_element(By.ID, "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll")
                cookie_btn.click()
                _log("Klikkede på cookie-popup 'Tillad alle'.")
                time.sleep(1)
            except Exception as e:
                _log(f"Ingen cookie-popup fundet eller klik-fejl: {e}")
            time.sleep(5)  # Giv AJAX tid til at loade
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".search-heading a"))
                )
                _log("Ventede på .search-heading a (AJAX)")
            except Exception as e:
                _log(f"⚠️ Timeout på .search-heading a: {e}")
            page_source = driver.page_source
            driver.quit()
            soup = BeautifulSoup(page_source, "html.parser")
            _log("Bruger Selenium til at hente HTML.")
            # Debug: log alle .search-item > a.more-link-links
            all_links = soup.select('.search-item > a.more-link')
            _log(f"Antal .search-item > a.more-link fundet: {len(all_links)}")
            for idx, l in enumerate(all_links):
                _log(f"Link {idx+1}: href={l.get('href')}, tekst={l.get_text(strip=True)}")
            link = all_links[0] if all_links else None
            if link and link.get('href'):
                product_url = link['href']
                _log(f"✅ Fandt produktside-link (første .search-item > a.more-link): {product_url}")
            else:
                _log(f"❌ Ingen produktside-link fundet på {search_url}")
                # Log alle <a>-tags
                all_a = soup.find_all('a')
                _log(f"Antal <a>-tags fundet: {len(all_a)}")
                for idx, a in enumerate(all_a):
                    _log(f"a-tag {idx+1}: href={a.get('href')}, tekst={a.get_text(strip=True)}")
                _log(f"Første 3000 tegn af HTML: {page_source[:3000]}")
                return "", ""
        except Exception as e:
            _log(f"⚠️ Selenium fejlede, bruger requests i stedet: {e}")
            resp = requests.get(search_url)
            soup = BeautifulSoup(resp.text, "html.parser")
            # Debug: log alle .search-heading a-links
            all_links = soup.select('.search-heading a')
            _log(f"Antal .search-heading a-links fundet: {len(all_links)}")
            for idx, l in enumerate(all_links):
                _log(f"Link {idx+1}: href={l.get('href')}, tekst={l.get_text(strip=True)}")
            link = all_links[0] if all_links else None
            if link and link.get('href'):
                product_url = link['href']
                _log(f"✅ Fandt produktside-link (første .search-heading a): {product_url}")
            else:
                _log(f"❌ Ingen produktside-link fundet på {search_url}")
                _log(f"Første 500 tegn af HTML: {soup.prettify()[:500]}")
                return "", ""
        prod_resp = requests.get(product_url)
        prod_soup = BeautifulSoup(prod_resp.text, "html.parser")

        # 2. Download billeder og datablad
        os.makedirs(original_folder, exist_ok=True)
        os.makedirs(download_folder, exist_ok=True)
        image_url = None
        datasheet_url = None
        doc_section = prod_soup.select_one("ul.single-info-documents")
        if doc_section:
            for a in doc_section.find_all("a"):
                text = a.get_text(strip=True).lower()
                if "billeder" in text:
                    image_url = a["href"]
                elif "datablad" in text:
                    datasheet_url = a["href"]
        # Download billede
        if image_url:
            try:
                img_resp = requests.get(image_url, timeout=15, stream=True)
                img_resp.raise_for_status()
                ext = os.path.splitext(image_url)[1] or ".jpg"
                img_path = os.path.join(original_folder, f"{img_name}{ext}")
                with open(img_path, "wb") as f:
                    shutil.copyfileobj(img_resp.raw, f)
                _log(f"✅ Downloadede billede: {img_path}")
            except Exception as e:
                _log(f"⚠️ Kunne ikke downloade billede: {e}")
        else:
            _log("ℹ️ Intet billede fundet.")
        # Download datablad og udtræk tekst
        pdf_text = None
        if datasheet_url:
            try:
                ds_resp = requests.get(datasheet_url, timeout=15, stream=True)
                ds_resp.raise_for_status()
                ext = os.path.splitext(datasheet_url)[1] or ".pdf"
                ds_path = os.path.join(download_folder, f"{product_number}_datablad{ext}")
                with open(ds_path, "wb") as f:
                    shutil.copyfileobj(ds_resp.raw, f)
                _log(f"✅ Downloadede datablad: {ds_path} fra {datasheet_url}")
                # Udtræk tekst fra PDF
                try:
                    pdf_text = extract_text_from_pdf(ds_path)
                    if pdf_text:
                        _log("✅ Udtrak tekst fra datablad PDF.")
                    else:
                        _log("⚠️ PDF-tekst er tom efter udtræk.")
                except Exception as e:
                    _log(f"⚠️ Kunne ikke udtrække tekst fra PDF: {e}")
            except Exception as e:
                _log(f"⚠️ Kunne ikke downloade datablad fra {datasheet_url} til {ds_path}: {e}")
        else:
            _log("ℹ️ Intet datablad fundet.")

        # 3. Produktinfo (HTML fallback)
        content_holder = prod_soup.select_one(".content-holder")
        html_text = content_holder.get_text("\n", strip=True) if content_holder else ""
        if not html_text:
            _log("⚠️ Ingen produktinfo fundet.")

        # Returnér PDF-tekst hvis muligt, ellers HTML
        if pdf_text:
            return pdf_text.strip(), product_url
        else:
            return html_text, product_url
    except Exception as e:
        _log(f"❌ Fejl under nordiskmicrofiber scrape: {e}")
        return "", ""
    finally:
        # Billedbehandling hvis muligt
        try:
            from utils.image_processor import resize_and_save_all_images
            if img_name:
                _log(f"Starter billedbehandling for {img_name}...")
                try:
                    resize_and_save_all_images(original_folder, image_folder, img_name)
                    _log(f"✅ Billedbehandling gennemført for {img_name}.")
                except Exception as e:
                    _log(f"⚠️ Kunne ikke resize billeder for {img_name}: {e}")
            else:
                _log("Ingen img_name angivet, springer billedbehandling over.")
        except Exception as e:
            _log(f"⚠️ Fejl under billedbehandling: {e}")

def extract_supplier_info(row, original_folder, driver=None, download_folder=None):
    product_number = str(row.get("PrimaryVendorItemID", "")).strip()
    img_name = str(row.get("IMG_NAME", "")).strip()
    prod_num = str(row.get("PROD_NUM", "")).strip()
    image_folder = os.path.join(os.path.expanduser("~"), "OneDrive - Bunzl Continental Europe", "Documents - Bonvig", "Produktbilleder_1500x1500")
    download_folder = download_folder or os.path.join(os.path.expanduser("~"), "Downloads")
    supplier_info, product_url = scrape(product_number, img_name, download_folder, original_folder, image_folder)
    return supplier_info, product_url
