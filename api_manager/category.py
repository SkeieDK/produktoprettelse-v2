from typing import Dict, List, Optional, Any
from pathlib import Path
from tqdm import tqdm
import time
import json
import logging
from .base import BaseAPI


class CategoryAPI(BaseAPI):
    def __init__(self, http_client, logger: logging.Logger, category_url: str, cache_dir: Optional[Path] = None):
        super().__init__(http_client, logger, cache_dir)
        self.category_url = category_url

    def get_all_categories(self, use_cache: bool = True, cache_hours: int = 24) -> List[Dict]:
        cache_file = Path(self.cache_dir) / "categories_cache.json" if self.cache_dir else None
        if use_cache and cache_file and cache_file.exists():
            cache_age = time.time() - cache_file.stat().st_mtime
            if cache_age < (cache_hours * 3600):
                self.logger.info(f"Bruger cached kategori data ({cache_age/3600:.1f} timer gammel)")
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        self.logger.info("Henter produktkategorier fra API...")
        all_categories = []
        offset = 0
        limit = 100
        with tqdm(desc="Henter kategorier", unit="batch") as pbar:
            while True:
                params = {'limit': limit, 'offset': offset}
                self.logger.debug(f"Henter batch: offset={offset}, limit={limit}")
                response = self.http.request(self.category_url, params=params, method='GET')
                items = response.get('items', [])
                if not items:
                    break
                all_categories.extend(items)
                pbar.update(1)
                has_more = response.get('hasMore', False)
                if not has_more:
                    break
                offset += limit
                time.sleep(0.1)
        self.logger.info(f"Hentet {len(all_categories)} kategorier i alt")
        if cache_file:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(all_categories, f, ensure_ascii=False, indent=2)
        return all_categories

    def filter_categories(self, categories: List[Dict]) -> List[Dict]:
        filtered = []
        for cat in categories:
            b2b_group = cat.get('b2BGroupId', '0')
            if b2b_group != '0' and b2b_group != 0:
                continue
            parent_ids = cat.get('parentIds', [])
            if '315' in parent_ids or 315 in parent_ids:
                continue
            filtered.append(cat)
        return filtered

    def process_category_hierarchy(self, categories: List[Dict]) -> List[Dict]:
        cat_lookup = {str(cat['id']): cat for cat in categories}
        processed_categories = []
        for cat in categories:
            cat_id = str(cat['id'])
            processed_cat = {
                'PROD_CAT_ID': cat_id,
                'category_number': cat.get('number', ''),
                'nederste_kategori': self._get_category_name(cat),
                'parent_ids': cat.get('parentIds', [])
            }
            hierarchy = self._build_category_hierarchy(cat, cat_lookup)
            processed_cat.update(hierarchy)
            processed_cat['kategori_niveau'] = self._calculate_category_level(processed_cat)
            processed_cat['kategori_sti'] = self._build_category_path(processed_cat)
            processed_cat['kategori_sti_ids'] = self._build_category_path_ids(processed_cat, cat_id)
            processed_categories.append(processed_cat)
        return processed_categories

    def _get_category_name(self, category: Dict) -> str:
        texts = category.get('texts', {}).get('items', [])
        if texts:
            return texts[0].get('name', '')
        return category.get('number', '')

    def _build_category_hierarchy(self, category: Dict, cat_lookup: Dict) -> Dict:
        hierarchy = {
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
        parent_1_id = str(parent_ids[0])
        if parent_1_id in cat_lookup:
            parent_1 = cat_lookup[parent_1_id]
            hierarchy['parent_cat'] = parent_1_id
            hierarchy['overkategori_1'] = self._get_category_name(parent_1)
            parent_1_parents = parent_1.get('parentIds', [])
            if parent_1_parents:
                parent_2_id = str(parent_1_parents[0])
                if parent_2_id in cat_lookup:
                    parent_2 = cat_lookup[parent_2_id]
                    hierarchy['parent_cat_1'] = parent_2_id
                    hierarchy['overkategori_2'] = self._get_category_name(parent_2)
                    parent_2_parents = parent_2.get('parentIds', [])
                    if parent_2_parents:
                        parent_3_id = str(parent_2_parents[0])
                        if parent_3_id in cat_lookup:
                            parent_3 = cat_lookup[parent_3_id]
                            hierarchy['parent_cat_2'] = parent_3_id
                            hierarchy['hovedkategori'] = self._get_category_name(parent_3)
        return hierarchy

    def _calculate_category_level(self, processed_cat: Dict) -> int:
        if processed_cat.get('hovedkategori'):
            return 3
        elif processed_cat.get('overkategori_2'):
            return 2
        elif processed_cat.get('overkategori_1'):
            return 1
        else:
            return 0

    def _build_category_path(self, processed_cat: Dict) -> str:
        path_parts = []
        if processed_cat.get('hovedkategori'):
            path_parts.append(processed_cat['hovedkategori'])
        if processed_cat.get('overkategori_2'):
            path_parts.append(processed_cat['overkategori_2'])
        if processed_cat.get('overkategori_1'):
            path_parts.append(processed_cat['overkategori_1'])
        if processed_cat.get('nederste_kategori'):
            path_parts.append(processed_cat['nederste_kategori'])
        return ' > '.join(path_parts)

    def _build_category_path_ids(self, processed_cat: Dict, cat_id: str) -> str:
        path_parts = []
        if processed_cat.get('parent_cat_2'):
            path_parts.append(processed_cat['parent_cat_2'])
        if processed_cat.get('parent_cat_1'):
            path_parts.append(processed_cat['parent_cat_1'])
        if processed_cat.get('parent_cat'):
            path_parts.append(processed_cat['parent_cat'])
        path_parts.append(cat_id)
        return ' > '.join(path_parts)
