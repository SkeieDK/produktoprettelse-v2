"""
API Manager for produktoprettelse system
Håndterer API calls til kategori data og andre externe services
"""
import requests
import os
import json
import time
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import logging
from tqdm import tqdm
from urllib.parse import quote

class BaseAPI:
    """Base class for shared API logic."""
    def __init__(self, make_request, logger, cache_dir=None):
        self._make_request = make_request
        self.logger = logger
        self.cache_dir = Path(cache_dir) if cache_dir else None

class ProductAPI(BaseAPI):
    """Handles product-related API calls."""
    def __init__(self, make_request, logger, product_url, cache_dir):
        super().__init__(make_request, logger, cache_dir)
        self.product_url = product_url

    def get_all_products(
        self,
        use_cache: bool = True,
        cache_hours: int = 24,
        include_settings: bool = True,
        include_prices: bool = False,
        include_categories: bool = False,
    ) -> List[Dict]:
        """
        Hent alle produkter fra API med paginering
        """
        # Use separate cache file if prices are included
        cache_filename = "products_prices_cache.json" if include_prices else "products_cache.json"
        cache_file = self.cache_dir / cache_filename if self.cache_dir else None
        
        # Tjek cache først
        if use_cache and cache_file and cache_file.exists():
            cache_age = time.time() - cache_file.stat().st_mtime
            if cache_age < (cache_hours * 3600):
                self.logger.info(f"Bruger cached produkt data ({cache_age/3600:.1f} timer gammel)")
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        self.logger.info("Henter produkter fra API...")
        all_products = []
        offset = 0
        limit = 100  # API max er 100
        
        with tqdm(desc="Henter produkter", unit="batch") as pbar:
            while True:
                params: Dict[str, Union[int, str]] = {
                    'limit': limit,
                    'offset': offset
                }
                
                # Build include string
                includes = []
                if include_settings:
                    includes.append('settings')
                if include_prices:
                    includes.append('prices')
                if include_categories:
                    includes.append('categories')
                
                if includes:
                    params['include'] = ','.join(includes)
                
                self.logger.debug(f"Henter batch: offset={offset}, limit={limit}")
                response = self._make_request(self.product_url, params)
                items = response.get('items', [])
                if not items:
                    break
                all_products.extend(items)
                pbar.update(1)
                # Tjek om der er flere
                has_more = response.get('hasMore', False)
                if not has_more:
                    break
                offset += limit
                time.sleep(0.1)
        self.logger.info(f"Hentet {len(all_products)} produkter i alt")
        # Gem til cache
        if cache_file:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(all_products, f, ensure_ascii=False, indent=2)
        return all_products

    def update_product(self, product_number: str, payload: Dict) -> bool:
        """Apply partial update to a product."""
        url = f"{self.product_url}/{product_number}"
        try:
            self._make_request(url, method="PATCH", json_data=payload)
            self.logger.info(f"Patched product {product_number}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to patch product {product_number}: {e}")
            return False

    def process_product_data(self, products: List[Dict]) -> List[Dict]:
        """
        Process produkt data til samme format som M koden forventer
        """
        processed_products = []
        
        for product in products:
            # Extract text fields (name, descriptions, meta)
            text_data = self._extract_product_texts(product)
            
            # Extract price info
            price_info = self._extract_price_info(product)
            
            # Map API felter til M kode kolonner
            processed_product = {
                # Basis produkt info
                'ItemID': product.get('number', ''),
                'ItemName': text_data.get('name', product.get('number', '')),
                'ItemBarcode': product.get('barCodeNumber', ''),
                'VendorNumber': product.get('vendorNumber', ''),
                'ConvertedSystemCost': product.get('costPrice', 0),
                'NetWeight': product.get('weight', 0),
                'TotalStockQty': product.get('stockCount', 0),
                
                # Price fields
                'UnitPrice': price_info.get('unitPrice', 0.0),
                'SpecialOfferPrice': price_info.get('specialOfferPrice', 0.0),
                'PriceCurrency': price_info.get('currencyCode', 'DKK'),
                
                # Text/Description fields (from settings API structure)
                'name': text_data.get('name', ''),
                'shortDescription': text_data.get('shortDescription', ''),
                'longDescription': text_data.get('longDescription', ''),
                'longDescription2': text_data.get('longDescription2', ''),
                'keyWords': text_data.get('keyWords', ''),
                'metaDescription': text_data.get('metaDescription', ''),
                'pageTitle': text_data.get('pageTitle', ''),
                'urlName': text_data.get('urlName', ''),
                
                # Dandomain specifikke felter
                'MinBuyAmount': product.get('minBuyAmount', 1),
                'MaxBuyAmount': product.get('maxBuyAmount', 0),
                'AllowPreOrder': product.get('allowPreOrder', False),
                'AllowBackOrder': product.get('allowBackOrder', False),
                'BackOrderAvailabilityDays': product.get('backOrderAvailabilityDays', 0),
                'StockLimit': product.get('stockLimit', 0),
                'SortOrder': product.get('sortOrder', 100),
                'TypeId': product.get('typeId', 88),
                
                # Feed indstillinger
                'ShowOnGoogleFeed': product.get('showOnGoogleFeed', False),
                'ShowOnFacebookFeed': product.get('showOnFacebookFeed', False),
                'ShowOnPricerunnerFeed': product.get('showOnPricerunnerFeed', True),
                'ShowOnKelkooFeed': product.get('showOnKelkooFeed', True),
                
                # Kategori info
                'DefaultCategoryId': product.get('defaultCategoryId', ''),
                'PrimaryCategoryId': product.get('primaryCategoryId', ''),
                
                # Metadata
                'CreatedDate': product.get('createdDate', ''),
                'EditedDate': product.get('editedDate', ''),
                'PictureLink': product.get('pictureLink', ''),
                'Comments': product.get('comments', ''),
                
                # Kategorier (hvis inkluderet)
                'Categories': self._extract_product_categories(product)
            }
            
            processed_products.append(processed_product)
        
        return processed_products
    
    def _extract_price_info(self, product: Dict) -> Dict:
        """Helper to find the default B2C price (qty 1)"""
        prices = product.get('prices', {}).get('items', [])
        if not prices:
            return {}
            
        # Find default price: usually quantity=1 and no specific B2B group (or default group)
        # Adjust logic based on your specific B2B/B2C setup
        for p in prices:
            if p.get('quantity', 0) == 1 and p.get('currencyCode') == 'DKK':
                return {
                    'unitPrice': p.get('unitPrice', 0.0),
                    'specialOfferPrice': p.get('specialOfferPrice', 0.0),
                    'currencyCode': p.get('currencyCode')
                }
        
        # Fallback to first price if no exact match
        return prices[0] if prices else {}

    def _extract_product_texts(self, product: Dict) -> Dict[str, str]:
        """
        Extract text fields from product's settings structure.
        """
        text_data = {
            'name': '',
            'shortDescription': '',
            'longDescription': '',
            'longDescription2': '',
            'keyWords': '',
            'metaDescription': '',
            'pageTitle': '',
            'urlName': ''
        }
        
        # Check if settings structure exists
        settings = product.get('settings', {})
        if isinstance(settings, dict):
            items = settings.get('items', [])
            if items and len(items) > 0:
                # Take first settings item (usually default language)
                first_setting = items[0]
                text_data['name'] = first_setting.get('name', '')
                text_data['shortDescription'] = first_setting.get('shortDescription', '')
                text_data['longDescription'] = first_setting.get('longDescription', '')
                text_data['longDescription2'] = first_setting.get('longDescription2', '')
                text_data['keyWords'] = first_setting.get('keyWords', '')
                text_data['metaDescription'] = first_setting.get('metaDescription', '')
                text_data['pageTitle'] = first_setting.get('pageTitle', '')
                text_data['urlName'] = first_setting.get('urlName', '')
        
        return text_data
    
    def _extract_product_categories(self, product: Dict) -> List[Dict]:
        """Udtræk kategori information fra produkt"""
        categories = []
        
        if 'categories' in product and 'items' in product['categories']:
            for cat in product['categories']['items']:
                category_info = {
                    'id': cat.get('id'),
                    'number': cat.get('number'),
                    'name': self._get_category_name_from_product(cat),
                    'b2BGroupId': cat.get('b2BGroupId'),
                    'parentIds': cat.get('parentIds', [])
                }
                categories.append(category_info)
        
        return categories
    
    def _get_category_name_from_product(self, category: Dict) -> str:
        """Udtræk kategori navn fra product category struktur"""
        texts = category.get('texts', {}).get('items', [])
        if texts:
            return texts[0].get('name', '')
        return category.get('number', '')

class CategoryAPI(BaseAPI):
    """Handles category-related API calls."""
    def __init__(self, make_request, logger, category_url, cache_dir):
        super().__init__(make_request, logger, cache_dir)
        self.category_url = category_url

    def get_all_categories(self, use_cache: bool = True, cache_hours: int = 24) -> List[Dict]:
        """
        Hent alle produktkategorier fra API med paginering
        """
        cache_file = self.cache_dir / "categories_cache.json" if self.cache_dir else None
        # Tjek cache først
        if use_cache and cache_file and cache_file.exists():
            cache_age = time.time() - cache_file.stat().st_mtime
            if cache_age < (cache_hours * 3600):
                self.logger.info(f"Bruger cached kategori data ({cache_age/3600:.1f} timer gammel)")
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        self.logger.info("Henter produktkategorier fra API...")
        all_categories = []
        offset = 0
        limit = 100  # API max er 100
        with tqdm(desc="Henter kategorier", unit="batch") as pbar:
            while True:
                params: Dict[str, Union[int, str]] = {
                    'limit': limit,
                    'offset': offset
                }
                self.logger.debug(f"Henter batch: offset={offset}, limit={limit}")
                response = self._make_request(self.category_url, params)
                items = response.get('items', [])
                if not items:
                    break
                all_categories.extend(items)
                pbar.update(1)
                # Tjek om der er flere
                has_more = response.get('hasMore', False)
                if not has_more:
                    break
                offset += limit
                time.sleep(0.1)
        self.logger.info(f"Hentet {len(all_categories)} kategorier i alt")
        # Gem til cache
        if cache_file:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(all_categories, f, ensure_ascii=False, indent=2)
        return all_categories

    def filter_categories(self, categories: List[Dict]) -> List[Dict]:
        """
        Filter kategorier baseret på M kode logik:
        - PROD_CAT_B2BGROUP_ID = "0" 
        - parent ikke "315"
        """
        filtered = []
        
        for cat in categories:
            # Tjek B2B group (skal være "0" eller ikke eksistere)
            b2b_group = cat.get('b2BGroupId', '0')
            if b2b_group != '0' and b2b_group != 0:
                continue
                
            # Tjek parent IDs (må ikke være "315")
            parent_ids = cat.get('parentIds', [])
            if '315' in parent_ids or 315 in parent_ids:
                continue
                
            filtered.append(cat)
        
        return filtered
    
    def process_category_hierarchy(self, categories: List[Dict]) -> List[Dict]:
        """
        Process kategori hierarki som i M koden
        Opretter kategori sti og niveauer
        """
        # Opret lookup dict for hurtig access
        cat_lookup = {str(cat['id']): cat for cat in categories}
        
        processed_categories = []
        
        for cat in categories:
            cat_id = str(cat['id'])
            
            # Basisdata
            processed_cat = {
                'PROD_CAT_ID': cat_id,
                'category_number': cat.get('number', ''),
                'nederste_kategori': self._get_category_name(cat),
                'parent_ids': cat.get('parentIds', [])
            }
            
            # Build hierarki
            hierarchy = self._build_category_hierarchy(cat, cat_lookup)
            processed_cat.update(hierarchy)
            
            # Beregn niveau (brug processed_cat da hierarchy ikke indeholder nederste_kategori)
            processed_cat['kategori_niveau'] = self._calculate_category_level(processed_cat)
            
            # Opret kategori sti
            processed_cat['kategori_sti'] = self._build_category_path(processed_cat)
            processed_cat['kategori_sti_ids'] = self._build_category_path_ids(processed_cat, cat_id)
            
            processed_categories.append(processed_cat)
        
        return processed_categories

    def _get_category_name(self, category: Dict) -> str:
        """Udtræk kategori navn fra texts struktur"""
        texts = category.get('texts', {}).get('items', [])
        if texts:
            return texts[0].get('name', '')
        return category.get('number', '')
    
    def _build_category_hierarchy(self, category: Dict, cat_lookup: Dict) -> Dict[str, Any]:
        """Build kategori hierarki op til 3 niveauer"""
        hierarchy: Dict[str, Any] = {
            'parent_cat': None,
            'overkategori_1': None,
            'parent_cat_1': None,
            'overkategori_2': None,
            'parent_cat_2': None,
            'hovedkategori': None
        }
        parent_ids = category.get('parentIds', [])
        if not parent_ids:
            return hierarchy
        # Niveau 1 parent
        parent_1_id = str(parent_ids[0])
        if parent_1_id in cat_lookup:
            parent_1 = cat_lookup[parent_1_id]
            hierarchy['parent_cat'] = parent_1_id
            hierarchy['overkategori_1'] = self._get_category_name(parent_1)
            # Niveau 2 parent
            parent_1_parents = parent_1.get('parentIds', [])
            if parent_1_parents:
                parent_2_id = str(parent_1_parents[0])
                if parent_2_id in cat_lookup:
                    parent_2 = cat_lookup[parent_2_id]
                    hierarchy['parent_cat_1'] = parent_2_id
                    hierarchy['overkategori_2'] = self._get_category_name(parent_2)
                    # Niveau 3 parent (hovedkategori)
                    parent_2_parents = parent_2.get('parentIds', [])
                    if parent_2_parents:
                        parent_3_id = str(parent_2_parents[0])
                        if parent_3_id in cat_lookup:
                            parent_3 = cat_lookup[parent_3_id]
                            hierarchy['parent_cat_2'] = parent_3_id
                            hierarchy['hovedkategori'] = self._get_category_name(parent_3)
        return hierarchy
    
    def _calculate_category_level(self, processed_cat: Dict) -> int:
        """Beregn kategori niveau baseret på hierarki"""
        if processed_cat.get('hovedkategori'):
            return 3
        elif processed_cat.get('overkategori_2'):
            return 2
        elif processed_cat.get('overkategori_1'):
            return 1
        else:
            return 0
    
    def _build_category_path(self, processed_cat: Dict) -> str:
        """Opret kategori sti tekst"""
        path_parts = []
        
        if processed_cat.get('hovedkategori'):
            path_parts.append(processed_cat['hovedkategori'])
        if processed_cat.get('overkategori_2'):
            path_parts.append(processed_cat['overkategori_2'])
        if processed_cat.get('overkategori_1'):
            path_parts.append(processed_cat['overkategori_1'])
        if processed_cat.get('nederste_kategori'):
            path_parts.append(processed_cat['nederste_kategori'])
        
        return " > ".join(path_parts)
    
    def _build_category_path_ids(self, processed_cat: Dict, cat_id: str) -> str:
        """Opret kategori sti med IDs"""
        path_parts = []
        
        if processed_cat.get('parent_cat_2'):
            path_parts.append(processed_cat['parent_cat_2'])
        if processed_cat.get('parent_cat_1'):
            path_parts.append(processed_cat['parent_cat_1'])
        if processed_cat.get('parent_cat'):
            path_parts.append(processed_cat['parent_cat'])
        path_parts.append(cat_id)
        
        return " > ".join(path_parts)

class PriceAPI(BaseAPI):
    """Handles price-related API calls."""
    def __init__(self, make_request, logger, product_url):
        super().__init__(make_request, logger)
        self.product_url = product_url

    def update_product_prices(self, product_number: str, operations: List[Dict[str, Optional[Dict[str, Any]]]]) -> bool:
        """Apply price mutations for a product."""
        url = f"{self.product_url}/{product_number}/prices"

        def _prepare_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
            normalised = {k: v for k, v in payload.items() if v is not None}
            if "unitPrice" in normalised:
                normalised["unitPrice"] = float(normalised["unitPrice"])
            if "specialOfferPrice" in normalised and normalised["specialOfferPrice"] is not None:
                normalised["specialOfferPrice"] = float(normalised["specialOfferPrice"])
            elif "specialOfferPrice" in normalised:
                normalised.pop("specialOfferPrice", None)
            return normalised

        try:
            for operation in operations:
                delete_payload = operation.get("delete") if operation else None
                update_payload = operation.get("update") if operation else None
                create_payload = operation.get("create") if operation else None

                if delete_payload:
                    self.logger.warning(f"Preparing to delete prices for {product_number}: {delete_payload}")
                    if not delete_payload.get("unitPrice"):
                        self.logger.error(f"Invalid delete payload for {product_number}: {delete_payload}")
                        continue
                    prepared_delete = _prepare_payload(delete_payload)
                    try:
                        self._make_request(url, method="DELETE", json_data=prepared_delete)
                    except Exception as delete_error:
                        message = str(delete_error)
                        if "404" in message:
                            self.logger.info(
                                "Prispost fandtes ikke ved sletning for %s (ignorerer 404)",
                                product_number,
                            )
                        else:
                            raise

                if update_payload:
                    prepared_update = _prepare_payload(update_payload)
                    self._make_request(url, method="PUT", json_data=prepared_update)

                if create_payload:
                    prepared_create = _prepare_payload(create_payload)
                    self._make_request(url, method="POST", json_data=prepared_create)

            self.logger.info(f"Updated prices for {product_number}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to update prices for {product_number}: {e}")
            return False

class APIManager:
    """Centralized API manager with submodules"""
    def __init__(self):
        self.api_key = os.getenv('DANDOMAIN_API_KEY')
        self.api_username = os.getenv('API_USERNAME', '')  # Optional username
        if not self.api_key:
            raise ValueError("DANDOMAIN_API_KEY miljøvariabel ikke fundet!")
        # Base URLs
        self.category_api_url = "https://engrosrengoringsmidler.dk/admin/WebAPI/v2/categories"
        self.product_api_url = "https://engrosrengoringsmidler.dk/admin/WebAPI/v2/products"
        # Cache directory
        self.cache_dir = Path(__file__).parent / "cache"
        self.cache_dir.mkdir(exist_ok=True)
        # Log directory
        self.log_dir = Path(__file__).parent / "logs"
        self.log_dir.mkdir(exist_ok=True)
        log_file_path = self.log_dir / "api_manager.log"
        # Setup logging
        self.logger = logging.getLogger("APIManager")
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        # Stream handler (console)
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        # File handler (log file)
        file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        file_handler.setFormatter(formatter)
        # Avoid duplicate handlers
        if not self.logger.hasHandlers():
            self.logger.addHandler(stream_handler)
            self.logger.addHandler(file_handler)
        else:
            self.logger.handlers.clear()
            self.logger.addHandler(stream_handler)
            self.logger.addHandler(file_handler)
        
        # Debug log to confirm cache directory
        self.logger.debug(f"Cache directory set to: {self.cache_dir}")

        # Initialize submodules
        self.product = ProductAPI(self._make_api_request, self.logger, self.product_api_url, self.cache_dir)
        self.category = CategoryAPI(self._make_api_request, self.logger, self.category_api_url, self.cache_dir)
        self.price = PriceAPI(self._make_api_request, self.logger, self.product_api_url)

    def _create_auth_string(self) -> str:
        """Opret korrekt Base64 encoded auth string"""
        import base64
        auth_text = f":{self.api_key}"
        return base64.b64encode(auth_text.encode('utf-8')).decode('utf-8')
        
    def _make_api_request(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        method: str = "GET",
        json_data: Optional[Dict] = None,
        timeout: int = 30,
    ) -> Dict:
        """Generisk API request med error handling"""
        auth_string = self._create_auth_string()
        headers = {
            'accept': 'text/plain',
            'Authorization': f'Basic {auth_string}'
        }
        try:
            # URL encoding
            url = quote(url, safe=':/')
            
            if method == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=timeout)
            elif method == "POST":
                headers['Content-Type'] = 'application/json'
                response = requests.post(url, headers=headers, params=params, json=json_data, timeout=timeout)
            elif method == "PUT":
                headers['Content-Type'] = 'application/json'
                response = requests.put(url, headers=headers, params=params, json=json_data, timeout=timeout)
            elif method == "PATCH":
                headers['Content-Type'] = 'application/json'
                response = requests.patch(url, headers=headers, params=params, json=json_data, timeout=timeout)
            elif method == "DELETE":
                headers['Content-Type'] = 'application/json'
                response = requests.delete(url, headers=headers, params=params, json=json_data, timeout=timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            if not response.content:
                return {}
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request fejlede: {e}")
        except json.JSONDecodeError as e:
            raise Exception(f"Kunne ikke parse JSON response: {e}")
    
    def _setup_logger(self):
        pass

    def get_product(
        self,
        product_number: str,
        include_settings: bool = True,
        include_prices: bool = True,
        include_categories: bool = True,
    ) -> Dict:
        """Fetch single product with optional expansions."""
        includes: List[str] = []
        if include_settings:
            includes.append("settings")
        if include_prices:
            includes.append("prices")
        if include_categories:
            includes.append("categories")
        params: Dict[str, str] = {}
        if includes:
            params["include"] = ",".join(includes)
        url = f"{self.product_api_url}/{product_number}"
        return self._make_api_request(url, params=params)
    
    def get_processed_products(self, use_cache: bool = True) -> List[Dict]:
        """Hent og process alle produkter med fuld API logik"""
        all_products = self.product.get_all_products(use_cache)
        print(f"Processerer {len(all_products)} produkter...")
        processed_products = self.product.process_product_data(all_products)
        print(f"Processeret: {len(processed_products)} produkter")
        return processed_products
    
    def get_processed_categories(self, use_cache: bool = True) -> List[Dict]:
        """Hent og process alle kategorier med fuld Power Query logik"""
        all_categories = self.category.get_all_categories(use_cache)
        print(f"Processerer {len(all_categories)} kategorier...")
        filtered_categories = self.category.filter_categories(all_categories)
        print(f"Filtreret: {len(filtered_categories)} kategorier")
        processed_categories = self.category.process_category_hierarchy(filtered_categories)
        print(f"Processeret: {len(processed_categories)} kategorier")
        return processed_categories
    
    def clear_cache(self, cache_type: str = "all"):
        """Ryd API cache filer."""
        cache_files = []
        if cache_type in ["all", "categories"]:
            cache_files.append(self.cache_dir / "categories_cache.json")
            cache_files.append(self.cache_dir / "categories_with_products.json")
        if cache_type in ["all", "products"]:
            cache_files.append(self.cache_dir / "products_cache.json")
            cache_files.append(self.cache_dir / "products_prices_cache.json")
            cache_files.append(self.cache_dir / "products_cache_with_cats.json")
            cache_files.append(self.cache_dir / "products_cache_no_cats.json")
        if cache_type == "products_prices":
            cache_files.append(self.cache_dir / "products_prices_cache.json")
        for cache_file in cache_files:
            if cache_file.exists():
                cache_file.unlink()
                print(f"Ryddet cache: {cache_file.name}")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Få information om cache status"""
        cache_info = {}
        cache_files = [
            "categories_cache.json",
            "categories_with_products.json",
            "products_cache.json",
            "products_prices_cache.json"
        ]
        for filename in cache_files:
            cache_file = self.cache_dir / filename
            if cache_file.exists():
                cache_age = time.time() - cache_file.stat().st_mtime
                cache_info[filename] = {
                    'exists': True,
                    'age_hours': cache_age / 3600,
                    'size_mb': cache_file.stat().st_size / (1024 * 1024)
                }
            else:
                cache_info[filename] = {'exists': False}
        return cache_info

    def refresh_all_caches(self) -> Dict[str, Any]:
        """Hent og opdater alle cache filer fra Dandomain API."""
        stats: Dict[str, Any] = {}
        self.logger.info("Starter fuld dataopdatering fra API")
        self.clear_cache("all")
        categories = self.category.get_all_categories(use_cache=False)
        stats["total_categories"] = len(categories)
        products = self.product.get_all_products(use_cache=False, include_prices=False, include_categories=True)
        stats["total_products"] = len(products)
        products_with_prices = self.product.get_all_products(use_cache=False, include_prices=True, include_categories=True)
        stats["total_products_with_prices"] = len(products_with_prices)
        
        category_numbers_with_products = set()
        for product in products:
            primary = product.get('primaryCategoryId')
            default = product.get('defaultCategoryId')
            if primary:
                category_numbers_with_products.add(str(primary))
            if default:
                category_numbers_with_products.add(str(default))
            categories_rel = product.get('categories', {}).get('items', []) if isinstance(product.get('categories'), dict) else []
            for cat in categories_rel:
                number = cat.get('number')
                if number:
                    category_numbers_with_products.add(str(number))

        # Ensure all categories are included in the cache
        for product in products:
            product['allCategories'] = [cat.get('number') for cat in product.get('categories', {}).get('items', []) if cat.get('number')]

        # Write updated products cache
        products_cache_path = self.cache_dir / "products_cache.json"
        try:
            with open(products_cache_path, 'w', encoding='utf-8') as f:
                json.dump(products, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Updated products cache written successfully to: {products_cache_path}")
        except Exception as e:
            self.logger.error(f"Failed to write updated products cache: {e}")
        
        filtered_categories = []
        # Adjust filtering logic to include only primary categories
        primary_category_numbers = {str(product.get('primaryCategoryId')) for product in products if product.get('primaryCategoryId')}

        for category in categories:
            number = category.get('number')
            if number and str(number) in primary_category_numbers:
                filtered_categories.append(category)
            else:
                self.logger.debug(f"Skipped category not in primary categories: {category}")

        # Log the final filtered categories
        self.logger.info(f"Filtered primary categories count: {len(filtered_categories)}")
        
        filtered_path = self.cache_dir / "categories_with_products.json"
        self.logger.info(f"Writing filtered categories to: {filtered_path}")
        # Verify cache directory exists
        if not self.cache_dir.exists():
            self.logger.error(f"Cache directory does not exist: {self.cache_dir}")
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Created cache directory: {self.cache_dir}")

        # Debug log for categories and products
        self.logger.debug(f"Categories fetched: {len(categories)}")
        self.logger.debug(f"Products fetched: {len(products)}")
        self.logger.debug(f"Products with prices fetched: {len(products_with_prices)}")

        # Debug log for category numbers with products
        self.logger.debug(f"Category numbers with products: {category_numbers_with_products}")

        # Debug log for filtered categories
        self.logger.debug(f"Filtered categories: {len(filtered_categories)}")

        # Ensure file writing is successful
        try:
            with open(filtered_path, 'w', encoding='utf-8') as f:
                json.dump(filtered_categories, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Filtered categories written successfully to: {filtered_path}")
        except Exception as e:
            self.logger.error(f"Failed to write filtered categories: {e}")
        stats["categories_with_products"] = len(filtered_categories)
        self.logger.info("Fuld dataopdatering færdig: %s", stats)
        return stats

    def update_product_prices(self, product_number: str, operations: List[Dict[str, Optional[Dict[str, Any]]]]) -> bool:
        """Delegate to PriceAPI"""
        return self.price.update_product_prices(product_number, operations)

    def patch_product(self, product_number: str, payload: Dict) -> bool:
        """Delegate to ProductAPI"""
        return self.product.update_product(product_number, payload)

    def update_product_categories(self, product_number: str, category_numbers: List[str]) -> bool:
        """Replace product categories with provided numbers."""
        payload = {"categoriesIds": [str(cat) for cat in category_numbers]}
        return self.patch_product(product_number, payload)

    def update_product_custom_field3(self, product_number: str, language_id: int, value: str) -> bool:
        """Update CustomField3 for a specific language."""
        payload = {
            "settings": {
                "items": [
                    {
                        "languageId": language_id,
                        "customField3": value or "",
                    }
                ]
            }
        }
        return self.patch_product(product_number, payload)

    def get_all_products(self, use_cache: bool = True, include_prices: bool = False, include_categories: bool = False) -> List[Dict]:
        """Fetch all products with optional expansions."""
        return self.product.get_all_products(use_cache=use_cache, include_prices=include_prices, include_categories=include_categories)

_api_manager = None

def get_api_manager() -> APIManager:
    """Lazy-instantiated APIManager."""
    global _api_manager
    if _api_manager is None:
        _api_manager = APIManager()
    return _api_manager

# Convenience functions
def get_categories(use_cache: bool = True):
    return get_api_manager().get_processed_categories(use_cache)

def refresh_categories():
    mgr = get_api_manager()
    mgr.clear_cache("categories")
    return mgr.get_processed_categories(use_cache=False)

def get_products(use_cache: bool = True):
    return get_api_manager().get_processed_products(use_cache)

def refresh_products():
    mgr = get_api_manager()
    mgr.clear_cache("products")
    return mgr.get_processed_products(use_cache=False)

def get_cache_status():
    return get_api_manager().get_cache_info()

if __name__ == "__main__":
    # Test script
    try:
        print("=== API Manager Test ===")
        mgr = get_api_manager()
        if mgr.api_key:
            mgr.logger.info("API_KEY fundet")
        else:
            mgr.logger.error("API_KEY ikke fundet")
            exit(1)
        
        print(f"\n=== Cache Status ===")
        cache_info = mgr.get_cache_info()
        for filename, info in cache_info.items():
            if info['exists']:
                print(f"[OK] {filename}: {info['age_hours']:.1f}t gammel, {info['size_mb']:.1f}MB")
            else:
                print(f"[X] {filename}: Ikke cached")
    except Exception as e:
        import logging
        logging.error(f"Fejl i test block: {e}")
