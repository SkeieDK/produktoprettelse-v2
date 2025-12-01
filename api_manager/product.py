from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import time
from tqdm import tqdm
import json
import logging
from .base import BaseAPI


class ProductAPI(BaseAPI):
    def __init__(self, http_client, logger: logging.Logger, product_url: str, cache_dir: Optional[Path] = None):
        super().__init__(http_client, logger, cache_dir)
        self.product_url = product_url

    def get_all_products(
        self,
        use_cache: bool = True,
        cache_hours: int = 24,
        include_settings: bool = True,
        include_prices: bool = False,
        include_categories: bool = False,
    ) -> List[Dict]:
        cache_filename = "products_prices_cache.json" if include_prices else "products_cache.json"
        cache_file = Path(self.cache_dir) / cache_filename if self.cache_dir else None
        # check cache
        if use_cache and cache_file and cache_file.exists():
            cache_age = time.time() - cache_file.stat().st_mtime
            if cache_age < (cache_hours * 3600):
                self.logger.info(f"Bruger cached produkt data ({cache_age/3600:.1f} timer gammel)")
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        self.logger.info("Henter produkter fra API...")
        all_products = []
        offset = 0
        limit = 100
        with tqdm(desc="Henter produkter", unit="batch") as pbar:
            while True:
                params: Dict[str, Union[int, str]] = {
                    'limit': limit,
                    'offset': offset
                }
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
                response = self.http.request(self.product_url, params=params, method='GET')
                items = response.get('items', [])
                if not items:
                    break
                all_products.extend(items)
                pbar.update(1)
                has_more = response.get('hasMore', False)
                if not has_more:
                    break
                offset += limit
                time.sleep(0.1)
        self.logger.info(f"Hentet {len(all_products)} produkter i alt")
        if cache_file:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(all_products, f, ensure_ascii=False, indent=2)
        return all_products


    def update_product(self, product_number: str, payload: Dict) -> bool:
        url = f"{self.product_url}/{product_number}"
        try:
            self.logger.debug(f"Patching product {product_number} with payload: {payload}")
            self.http.request(url, method='PATCH', json_data=payload)
            self.logger.info(f"Patched product {product_number}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to patch product {product_number}: {e}")
            return False

    def process_product_data(self, products: List[Dict]) -> List[Dict]:
        processed_products = []
        for product in products:
            text_data = self._extract_product_texts(product)
            price_info = self._extract_price_info(product)
            processed_product = {
                'ItemID': product.get('number', ''),
                'ItemName': text_data.get('name', product.get('number', '')),
                'ItemBarcode': product.get('barCodeNumber', ''),
                'VendorNumber': product.get('vendorNumber', ''),
                'ConvertedSystemCost': product.get('costPrice', 0),
                'NetWeight': product.get('weight', 0),
                'TotalStockQty': product.get('stockCount', 0),
                'UnitPrice': price_info.get('unitPrice', 0.0),
                'SpecialOfferPrice': price_info.get('specialOfferPrice', 0.0),
                'PriceCurrency': price_info.get('currencyCode', 'DKK'),
                'name': text_data.get('name', ''),
                'shortDescription': text_data.get('shortDescription', ''),
                'longDescription': text_data.get('longDescription', ''),
                'longDescription2': text_data.get('longDescription2', ''),
                'keyWords': text_data.get('keyWords', ''),
                'metaDescription': text_data.get('metaDescription', ''),
                'pageTitle': text_data.get('pageTitle', ''),
                'urlName': text_data.get('urlName', ''),
                'MinBuyAmount': product.get('minBuyAmount', 1),
                'MaxBuyAmount': product.get('maxBuyAmount', 0),
                'AllowPreOrder': product.get('allowPreOrder', False),
                'AllowBackOrder': product.get('allowBackOrder', False),
                'BackOrderAvailabilityDays': product.get('backOrderAvailabilityDays', 0),
                'StockLimit': product.get('stockLimit', 0),
                'SortOrder': product.get('sortOrder', 100),
                'TypeId': product.get('typeId', 88),
                'ShowOnGoogleFeed': product.get('showOnGoogleFeed', False),
                'ShowOnFacebookFeed': product.get('showOnFacebookFeed', False),
                'ShowOnPricerunnerFeed': product.get('showOnPricerunnerFeed', True),
                'ShowOnKelkooFeed': product.get('showOnKelkooFeed', True),
                'DefaultCategoryId': product.get('defaultCategoryId', ''),
                'PrimaryCategoryId': product.get('primaryCategoryId', ''),
                'CreatedDate': product.get('createdDate', ''),
                'EditedDate': product.get('editedDate', ''),
                'PictureLink': product.get('pictureLink', ''),
                'Comments': product.get('comments', ''),
                'Categories': self._extract_product_categories(product)
            }
            processed_products.append(processed_product)
        return processed_products

    def _extract_price_info(self, product: Dict) -> Dict:
        prices = product.get('prices', {}).get('items', [])
        if not prices:
            return {}
        for p in prices:
            if p.get('quantity', 0) == 1 and p.get('currencyCode') == 'DKK':
                return {
                    'unitPrice': p.get('unitPrice', 0.0),
                    'specialOfferPrice': p.get('specialOfferPrice', 0.0),
                    'currencyCode': p.get('currencyCode')
                }
        return prices[0] if prices else {}

    def _extract_product_texts(self, product: Dict) -> Dict[str, str]:
        text_data = {'name': '', 'shortDescription': '', 'longDescription': '', 'longDescription2': '', 'keyWords': '', 'metaDescription': '', 'pageTitle': '', 'urlName': ''}
        settings = product.get('settings', {})
        if isinstance(settings, dict):
            items = settings.get('items', [])
            if items and len(items) > 0:
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
        texts = category.get('texts', {}).get('items', [])
        if texts:
            return texts[0].get('name', '')
        return category.get('number', '')
