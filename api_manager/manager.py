import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from .http import HTTPClient
from .logger import create_logger
from .cache import CacheManager
from .product import ProductAPI
from .category import CategoryAPI
from .price import PriceAPI


class APIManager:
    def __init__(self, api_key: Optional[str] = None, api_username: Optional[str] = None, product_api_url: Optional[str] = None, category_api_url: Optional[str] = None, cache_dir: Optional[Path] = None, log_dir: Optional[Path] = None):
        self.api_key = api_key or os.getenv('DANDOMAIN_API_KEY')
        self.api_username = api_username or os.getenv('API_USERNAME', '')
        if not self.api_key:
            raise ValueError("DANDOMAIN_API_KEY miljøvariabel ikke fundet!")

        self.product_api_url = product_api_url or "https://engrosrengoringsmidler.dk/admin/WebAPI/v2/products"
        self.category_api_url = category_api_url or "https://engrosrengoringsmidler.dk/admin/WebAPI/v2/categories"

        # Paths
        root = Path(__file__).parent.parent
        self.cache_dir = Path(cache_dir) if cache_dir else (root / "cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir = Path(log_dir) if log_dir else (root / "logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Setup logger and http client
        self.logger = create_logger("APIManager", self.log_dir)
        self.http = HTTPClient(self.api_key, self.logger, api_username=self.api_username)
        self.cache = CacheManager(self.cache_dir, self.logger)

        # Submodules
        self.product = ProductAPI(self.http, self.logger, self.product_api_url, self.cache_dir)
        self.category = CategoryAPI(self.http, self.logger, self.category_api_url, self.cache_dir)
        self.price = PriceAPI(self.http, self.logger, self.product_api_url)
        # debug summary
        try:
            key_tail = self.api_key[-4:]
        except Exception:
            key_tail = "unknown"
        self.logger.debug(f"APIManager initialized; api_username={self.api_username or '<unset>'}, api_key_tail={key_tail}, product_url={self.product_api_url}, category_url={self.category_api_url}, cache_dir={self.cache_dir}")

    # Product delegations
    def get_product(self, product_number: str, include_settings: bool = True, include_prices: bool = True, include_categories: bool = True) -> Dict:
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
        return self.http.request(url, params=params, method='GET')

    def get_all_products(self, *args, **kwargs):
        return self.product.get_all_products(*args, **kwargs)

    def get_processed_products(self, use_cache: bool = True):
        all_products = self.product.get_all_products(use_cache)
        self.logger.info(f"Processerer {len(all_products)} produkter...")
        return self.product.process_product_data(all_products)

    # Category delegations
    def get_processed_categories(self, use_cache: bool = True):
        all_categories = self.category.get_all_categories(use_cache)
        self.logger.info(f"Processerer {len(all_categories)} kategorier...")
        filtered = self.category.filter_categories(all_categories)
        return self.category.process_category_hierarchy(filtered)

    # Cache utilities
    def clear_cache(self, cache_type: str = "all"):
        if cache_type in ["all", "categories"]:
            self.cache.clear("categories_cache.json")
            self.cache.clear("categories_with_products.json")
        if cache_type in ["all", "products"]:
            self.cache.clear("products_cache.json")
            self.cache.clear("products_prices_cache.json")
            self.cache.clear("products_cache_with_cats.json")
            self.cache.clear("products_cache_no_cats.json")
        if cache_type == "products_prices":
            self.cache.clear("products_prices_cache.json")

    def get_cache_info(self) -> Dict[str, Any]:
        files = ["categories_cache.json", "categories_with_products.json", "products_cache.json", "products_prices_cache.json"]
        info: Dict[str, Any] = {}
        for f in files:
            info[f] = self.cache.file_info(f)
        return info

    def refresh_all_caches(self) -> Dict[str, Any]:
        stats: Dict[str, Any] = {}
        self.logger.info("Starter fuld dataopdatering fra API")
        self.clear_cache('all')
        categories = self.category.get_all_categories(use_cache=False)
        stats['total_categories'] = len(categories)
        products = self.product.get_all_products(use_cache=False, include_prices=False, include_categories=True)
        stats['total_products'] = len(products)
        products_with_prices = self.product.get_all_products(use_cache=False, include_prices=True, include_categories=True)
        stats['total_products_with_prices'] = len(products_with_prices)

        # similar processing as before
        category_numbers_with_products = set()
        for product in products:
            primary = product.get('primaryCategoryId'); default = product.get('defaultCategoryId')
            if primary: category_numbers_with_products.add(str(primary))
            if default: category_numbers_with_products.add(str(default))
            categories_rel = product.get('categories', {}).get('items', []) if isinstance(product.get('categories'), dict) else []
            for cat in categories_rel:
                number = cat.get('number')
                if number: category_numbers_with_products.add(str(number))

        for product in products:
            product['allCategories'] = [cat.get('number') for cat in product.get('categories', {}).get('items', []) if cat.get('number')]

        try:
            self.cache.write_json('products_cache.json', products)
            self.logger.info("Updated products cache written successfully.")
        except Exception as e:
            self.logger.error(f"Failed to write updated products cache: {e}")

        filtered_categories = []
        primary_category_numbers = {str(product.get('primaryCategoryId')) for product in products if product.get('primaryCategoryId')}
        for category in categories:
            number = category.get('number')
            if number and str(number) in primary_category_numbers:
                filtered_categories.append(category)
            else:
                self.logger.debug(f"Skipped category not in primary categories: {category}")

        self.logger.info(f"Filtered primary categories count: {len(filtered_categories)}")
        try:
            self.cache.write_json('categories_with_products.json', filtered_categories)
            self.logger.info("Filtered categories written successfully.")
        except Exception as e:
            self.logger.error(f"Failed to write filtered categories: {e}")

        stats["categories_with_products"] = len(filtered_categories)
        self.logger.info("Fuld dataopdatering færdig: %s", stats)
        return stats

    # Price operations
    def update_product_prices(self, product_number: str, operations: List[Dict[str, Optional[Dict[str, Any]]]]) -> bool:
        return self.price.update_product_prices(product_number, operations)

    # Product patch delegate
    def patch_product(self, product_number: str, payload: Dict) -> bool:
        return self.product.update_product(product_number, payload)

    def update_product_categories(self, product_number: str, category_numbers: List[str]) -> bool:
        # resolve ids using categories cache file if present
        resolved_ids: List[str] = []
        cache_file = self.cache_dir / "categories_cache.json"
        mapping = {}
        if cache_file.exists():
            try:
                cats = self.cache.read_json('categories_cache.json', default=[]) or []
                for cat in cats:
                    num = str(cat.get('number')) if cat.get('number') is not None else None
                    cid = cat.get('id')
                    if num and cid is not None:
                        mapping[str(num)] = str(cid)
            except Exception as e:
                self.logger.debug(f"Could not build category mapping from cache: {e}")
        for cat in category_numbers:
            cat_str = str(cat)
            if cat_str in mapping:
                resolved_ids.append(mapping[cat_str])
            else:
                resolved_ids.append(cat_str)
        payload = {"categoriesIds": resolved_ids}
        return self.patch_product(product_number, payload)

    def update_product_custom_field3(self, product_number: str, language_id: int = 0, value: str = "", site_id: int = 26) -> bool:
        payload = {"customField3": value or ""}
        try:
            url = f"{self.product_api_url}/{product_number}/sites/{site_id}/settings"
            self.http.request(url, method="PATCH", json_data=payload)
            self.logger.info(f"Patched product {product_number} settings (customField3={value}) for site {site_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to update customField3 for {product_number}: {e}")
            return False


# =============================================================================
# Factory and Singleton Pattern
# =============================================================================
# The singleton is kept for backward compatibility, but we now provide:
# - create_api_manager(): Factory function for testing with custom config
# - reset_api_manager(): Clear singleton for test isolation
# - get_api_manager(): Singleton accessor (unchanged API)

_api_manager: Optional[APIManager] = None


def create_api_manager(
    api_key: Optional[str] = None,
    api_username: Optional[str] = None,
    product_api_url: Optional[str] = None,
    category_api_url: Optional[str] = None,
    cache_dir: Optional[Path] = None,
    log_dir: Optional[Path] = None,
) -> APIManager:
    """
    Factory function to create an APIManager instance.
    
    Use this for testing or when you need multiple instances with different
    configurations. For normal use, prefer get_api_manager() singleton.
    
    Args:
        api_key: Dandomain API key (defaults to DANDOMAIN_API_KEY env var)
        api_username: API username (defaults to API_USERNAME env var)
        product_api_url: Product API base URL
        category_api_url: Category API base URL
        cache_dir: Directory for cache files
        log_dir: Directory for log files
    
    Returns:
        New APIManager instance
    
    Example:
        # For testing with mock config
        test_api = create_api_manager(
            api_key="test_key",
            cache_dir=Path("/tmp/test_cache"),
        )
    """
    return APIManager(
        api_key=api_key,
        api_username=api_username,
        product_api_url=product_api_url,
        category_api_url=category_api_url,
        cache_dir=cache_dir,
        log_dir=log_dir,
    )


def get_api_manager() -> APIManager:
    """
    Get the singleton APIManager instance.
    
    Creates the instance on first call using environment variables.
    Subsequent calls return the same instance.
    
    Returns:
        Singleton APIManager instance
    
    Raises:
        ValueError: If DANDOMAIN_API_KEY is not set
    """
    global _api_manager
    if _api_manager is None:
        _api_manager = APIManager()
        _api_manager.logger.info("Created singleton APIManager instance")
    return _api_manager


def reset_api_manager() -> None:
    """
    Reset the singleton APIManager instance.
    
    Use this for test isolation - call between tests to ensure
    a fresh instance is created on next get_api_manager() call.
    
    Example:
        def teardown_function():
            reset_api_manager()
    """
    global _api_manager
    _api_manager = None


# Convenience wrappers

def get_categories(use_cache: bool = True):
    return get_api_manager().get_processed_categories(use_cache)


def refresh_categories():
    mgr = get_api_manager(); mgr.clear_cache("categories"); return mgr.get_processed_categories(use_cache=False)


def get_products(use_cache: bool = True):
    return get_api_manager().get_processed_products(use_cache)


def refresh_products():
    mgr = get_api_manager(); mgr.clear_cache("products"); return mgr.get_processed_products(use_cache=False)


def get_cache_status():
    return get_api_manager().get_cache_info()
