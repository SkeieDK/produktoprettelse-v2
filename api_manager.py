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

class APIManager:
    """Centraliseret API manager for eksterne data sources"""
    def __init__(self):
        self.api_key = os.getenv('API_KEY')
        self.api_username = os.getenv('API_USERNAME', '')  # Optional username
        if not self.api_key:
            raise ValueError("API_KEY miljøvariabel ikke fundet!")
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
    
    def _create_auth_string(self) -> str:
        """Opret korrekt Base64 encoded auth string"""
        import base64
        
        # API format er ":apikey" (colon + apikey) som base64 encoded
        auth_text = f":{self.api_key}"
        
        # Base64 encode
        return base64.b64encode(auth_text.encode('utf-8')).decode('utf-8')
        
    def _make_api_request(self, url: str, params: Optional[Dict[str, Any]] = None, timeout: int = 30) -> Dict:
        """Generisk API request med error handling"""
        # Opret korrekt Basic Auth header
        auth_string = self._create_auth_string()
        
        headers = {
            'accept': 'text/plain',
            'Authorization': f'Basic {auth_string}'
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request fejlede: {e}")
        except json.JSONDecodeError as e:
            raise Exception(f"Kunne ikke parse JSON response: {e}")
    
    def get_all_categories(self, use_cache: bool = True, cache_hours: int = 24) -> List[Dict]:
        """
        Hent alle produktkategorier fra API med paginering
        """
        cache_file = self.cache_dir / "categories_cache.json"
        # Tjek cache først
        if use_cache and cache_file.exists():
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
                response = self._make_api_request(self.category_api_url, params)
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
    
    def get_all_products(self, use_cache: bool = True, cache_hours: int = 24) -> List[Dict]:
        """
        Hent alle produkter fra API med paginering
        """
        cache_file = self.cache_dir / "products_cache.json"
        # Tjek cache først
        if use_cache and cache_file.exists():
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
                self.logger.debug(f"Henter batch: offset={offset}, limit={limit}")
                response = self._make_api_request(self.product_api_url, params)
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
        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(all_products, f, ensure_ascii=False, indent=2)
        return all_products
    
    def process_product_data(self, products: List[Dict]) -> List[Dict]:
        """
        Process produkt data til samme format som M koden forventer
        """
        processed_products = []
        
        for product in products:
            # Map API felter til M kode kolonner
            processed_product = {
                # Basis produkt info
                'ItemID': product.get('number', ''),
                'ItemName': self._get_product_name(product),
                'ItemBarcode': product.get('barCodeNumber', ''),
                'VendorNumber': product.get('vendorNumber', ''),
                'ConvertedSystemCost': product.get('costPrice', 0),
                'NetWeight': product.get('weight', 0),
                'TotalStockQty': product.get('stockCount', 0),
                
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
    
    def _get_product_name(self, product: Dict) -> str:
        """Udtræk produkt navn - skal måske hentes fra texts senere"""
        # For nu returnerer vi product number da navn ikke er i basis API
        return product.get('number', '')
    
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
    
    def get_processed_products(self, use_cache: bool = True) -> List[Dict]:
        """
        Hent og process alle produkter med fuld API logik
        Returns:
            List af processede produkter klar til brug
        """
        # Hent alle produkter
        all_products = self.get_all_products(use_cache)
        print(f"📊 Processerer {len(all_products)} produkter...")
        # Process produkter
        processed_products = self.process_product_data(all_products)
        print(f"✅ {len(processed_products)} produkter processeret")
        return processed_products
    
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
    
    def get_processed_categories(self, use_cache: bool = True) -> List[Dict]:
        """
        Hent og process alle kategorier med fuld Power Query logik
        
        Returns:
            List af processede kategorier klar til brug
        """
        # Hent alle kategorier
        all_categories = self.get_all_categories(use_cache)
        
        print(f"📊 Processerer {len(all_categories)} kategorier...")
        
        # Filtrér baseret på regler
        filtered_categories = self.filter_categories(all_categories)
        print(f"🔍 {len(filtered_categories)} kategorier efter filtrering")
        
        # Process hierarki
        processed_categories = self.process_category_hierarchy(filtered_categories)
        print(f"✅ {len(processed_categories)} kategorier processeret")
        
        return processed_categories
    
    def clear_cache(self, cache_type: str = "all"):
        """
        Ryd API cache
        
        Args:
            cache_type: "all", "categories", "products", eller "products_no_cats"
        """
        cache_files = []
        
        if cache_type in ["all", "categories"]:
            cache_files.append(self.cache_dir / "categories_cache.json")
        
        if cache_type in ["all", "products"]:
            cache_files.append(self.cache_dir / "products_cache_with_cats.json")
            cache_files.append(self.cache_dir / "products_cache_no_cats.json")
        
        if cache_type == "products_no_cats":
            cache_files.append(self.cache_dir / "products_cache_no_cats.json")
        
        for cache_file in cache_files:
            if cache_file.exists():
                cache_file.unlink()
                print(f"🗑️ Ryddet cache: {cache_file.name}")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Få information om cache status"""
        cache_info = {}
        cache_files = [
            "categories_cache.json",
            "products_cache.json"
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

_api_manager = None

def get_api_manager() -> APIManager:
    """Lazy-instantiated APIManager. Instantiating at import time previously raised if API_KEY missing,
    which could terminate processes unexpectedly. This factory defers instantiation until needed.
    """
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
        # Test API key
        mgr = get_api_manager()
        if mgr.api_key:
            mgr.logger.info("API_KEY fundet")
        else:
            mgr.logger.error("API_KEY ikke fundet")
            exit(1)
        # Test kategori hentning
        categories = mgr.get_processed_categories()
        if categories:
            print(f"\n📊 Eksempel kategori data:")
            example = categories[0]
            for key, value in example.items():
                print(f"  {key}: {value}")
            print(f"\n📈 Kategori niveau fordeling:")
            levels = {}
            for cat in categories:
                level = cat['kategori_niveau']
                levels[level] = levels.get(level, 0) + 1
            for level, count in sorted(levels.items()):
                print(f"  Niveau {level}: {count} kategorier")
        # Test produkt hentning
        print(f"\n=== Test Produkter ===")
        products = mgr.get_processed_products(use_cache=True)
        if products:
            print(f"✅ {len(products)} produkter hentet")
            # Vis eksempel produkt
            example_product = products[0]
            print(f"\n📦 Eksempel produkt data:")
            for key, value in list(example_product.items())[:10]:  # Vis kun første 10 felter
                print(f"  {key}: {value}")
        # Vis cache status
        print(f"\n=== Cache Status ===")
        cache_info = mgr.get_cache_info()
        for filename, info in cache_info.items():
            if info['exists']:
                print(f"✅ {filename}: {info['age_hours']:.1f}t gammel, {info['size_mb']:.1f}MB")
            else:
                print(f"❌ {filename}: Ikke cached")
    except Exception as e:
        mgr = None
        try:
            mgr = get_api_manager()
        except Exception:
            pass
        if mgr:
            mgr.logger.error(f"Fejl: {e}")
        else:
            import logging
            logging.error(f"Fejl i test block: {e}")