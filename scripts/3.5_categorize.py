#!/usr/bin/env python3
"""
Step 3.5: Embedding-Based Product Categorization (Cost-Optimized)
Uses OpenAI embeddings for semantic similarity matching (75x cheaper than LLM).

Strategy:
1. Generate embeddings for all categories (one-time, cached)
2. Generate embedding for each product
3. Find best match using cosine similarity
4. Fallback to gpt-3.5-turbo only if confidence < 70%

Cost: ~$0.000002 per product (vs $0.00015 with LLM)

Input:  data/output/enriched_products.json (from Step 3)
Output: data/output/categorized_products.json (with category assignments)
Logs to: logs/3.5_categorize.log
"""

import json
import sys
import logging
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple
from datetime import datetime
import yaml
from dotenv import load_dotenv
from openai import OpenAI
import numpy as np

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from api_manager import get_categories, get_products, get_cache_status
from ai_config import get_model_config, calculate_cost, PRICING

# Safe stream for console output (handles encoding errors)
class SafeStream:
    def __init__(self):
        self.encoding = 'utf-8'
    
    def write(self, msg):
        if not msg:
            return
        try:
            sys.__stdout__.write(msg)
        except UnicodeEncodeError:
            try:
                safe_msg = msg.encode('utf-8', errors='replace').decode(sys.__stdout__.encoding or 'utf-8', errors='replace')
                sys.__stdout__.write(safe_msg)
            except Exception:
                try:
                    safe_msg = msg.encode('ascii', errors='replace').decode('ascii')
                    sys.__stdout__.write(safe_msg)
                except Exception:
                    pass
    
    def flush(self):
        try:
            sys.__stdout__.flush()
        except Exception:
            pass
    
    def isatty(self):
        return sys.__stdout__.isatty() if hasattr(sys.__stdout__, 'isatty') else False


class SafeStreamHandler(logging.StreamHandler):
    """Custom logging handler that prevents encoding errors"""
    def emit(self, record):
        try:
            msg = self.format(record)
            self.stream.write(msg)
            self.stream.write('\n')
            self.stream.flush()
        except Exception:
            self.handleError(record)


def load_config():
    """Load config.yaml with defaults."""
    config_path = PROJECT_ROOT / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            if "paths" in config:
                paths = config["paths"]
                return {
                    "paths": {
                        "input": paths.get("input_dir", "data/input"),
                        "output": paths.get("output_dir", "data/output"),
                        "cache": paths.get("cache_dir", "cache"),
                        "logs": paths.get("logs_dir", "logs"),
                    },
                    "ai": config.get("ai", {}),
                    "categorization": config.get("categorization", {}),
                    "logging": config.get("logging", {"level": "INFO"})
                }
            return config
    return {
        "paths": {
            "input": str(PROJECT_ROOT / "data" / "input"),
            "output": str(PROJECT_ROOT / "data" / "output"),
            "cache": str(PROJECT_ROOT / "cache"),
            "logs": str(PROJECT_ROOT / "logs"),
        },
        "ai": {"provider": "openai", "model": "text-embedding-3-small", "temperature": 0.3},
        "categorization": {"confidence_threshold": 70, "batch_size": 10},
        "logging": {"level": "INFO"}
    }


def setup_logging(log_dir: Path, log_file_name: str = "3.5_categorize.log"):
    """Configure logging to file and console"""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / log_file_name
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler (UTF-8)
    file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='a')
    file_handler.setFormatter(formatter)
    
    # Console handler with SafeStream
    console_handler = SafeStreamHandler(SafeStream())
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def get_api_key(logger, config):
    """Get OpenAI API key from .env, environment, or config."""
    # Load .env file
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logger.debug(f"Loaded .env from {env_path}")
    
    # Try environment variable first
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("AI_API_KEY")
    if api_key:
        logger.info("Using OpenAI API key from environment (.env or system)")
        return api_key
    
    # Try config file
    if config.get("ai", {}).get("api_key"):
        logger.info("Using OpenAI API key from config")
        return config["ai"]["api_key"]
    
    logger.error("No API key found! Set OPENAI_API_KEY in .env or config.yaml")
    return None


def build_category_text(category: Dict, example_products: List[Dict]) -> str:
    """
    Build text representation of category for embedding.
    Now works with RAW API category data.
    
    Includes: category name, description, and example products.
    """
    # Get category name from texts.items[0].name
    cat_name = 'Unknown'
    texts = category.get('texts', {})
    if isinstance(texts, dict):
        items = texts.get('items', [])
        if items and len(items) > 0:
            cat_name = items[0].get('name', 'Unknown')
    
    cat_number = category.get('number', '')
    
    text_parts = [f"Category: {cat_name}"]
    
    if cat_number:
        text_parts.append(f"Category number: {cat_number}")
    
    # Add example products if available
    if example_products:
        product_names = [p['name'] for p in example_products[:5]]
        text_parts.append(f"Example products: {', '.join(product_names)}")
    
    return " | ".join(text_parts)


def build_product_text(product: Dict, include_details: bool = False) -> str:
    """
    Build text representation of product for embedding.
    
    Args:
        product: Product details
        include_details: If True, include full description (for fallback)
    """
    prod_name = product.get('ORIGINAL_PROD_NAME', product.get('PROD_NAME', 'Unknown'))
    vendor = product.get('PrimaryVendorName', 'Unknown')
    
    text_parts = [f"Product: {prod_name}", f"Vendor: {vendor}"]
    
    if include_details:
        supplier_info = product.get('supplier_info', {})
        if isinstance(supplier_info, dict):
            description = supplier_info.get('description', '')
            if description:
                text_parts.append(f"Description: {description[:300]}")
        elif supplier_info:
            text_parts.append(f"Description: {str(supplier_info)[:300]}")
    
    return " | ".join(text_parts)


def get_embedding(text: str, client: OpenAI, model: str = "text-embedding-3-small") -> List[float]:
    """
    Get embedding vector for text.
    
    Args:
        text: Text to embed
        client: OpenAI client
        model: Embedding model (default: text-embedding-3-small)
    
    Returns:
        List of floats (embedding vector)
    """
    response = client.embeddings.create(
        input=text,
        model=model
    )
    return response.data[0].embedding


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Returns:
        Similarity score (0-1, higher is more similar)
    """
    vec1_np = np.array(vec1)
    vec2_np = np.array(vec2)
    
    dot_product = np.dot(vec1_np, vec2_np)
    norm1 = np.linalg.norm(vec1_np)
    norm2 = np.linalg.norm(vec2_np)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return dot_product / (norm1 * norm2)


def build_category_with_products_map(categories: List[Dict], products: List[Dict], logger) -> Dict[str, Dict]:
    """
    Build a map of categories with example products from each.
    Now works with RAW API category data (has 'id' and 'number' fields).
    
    Returns:
        Dict mapping category_id (API 'id') to {category_info, example_products}
    """
    logger.info("Building category-to-products map...")
    
    # Create category map with API 'id' as key
    cat_map = {}
    # Also create a lookup from category 'number' to category 'id'
    cat_number_to_id = {}
    
    for cat in categories:
        cat_id = str(cat.get('id', ''))
        cat_number = str(cat.get('number', ''))
        
        if not cat_id:
            continue
        
        cat_map[cat_id] = {
            'category_info': cat,
            'example_products': []
        }
        
        if cat_number:
            cat_number_to_id[cat_number] = cat_id
    
    logger.info(f"Built lookup for {len(cat_number_to_id)} category numbers")
    
    # Map products to categories (products have 'defaultCategoryId' and 'primaryCategoryId' as NUMBERS)
    for product in products:
        # Get category identifiers from product (these are category NUMBERS, not IDs)
        default_cat_num = str(product.get('defaultCategoryId', ''))
        primary_cat_num = str(product.get('primaryCategoryId', ''))
        
        category_ids = set()
        
        # Convert category numbers to category IDs
        if default_cat_num and default_cat_num in cat_number_to_id:
            category_ids.add(cat_number_to_id[default_cat_num])
        
        if primary_cat_num and primary_cat_num in cat_number_to_id:
            category_ids.add(cat_number_to_id[primary_cat_num])
        
        # Add product to relevant categories (limit 5 examples per category)
        # Get product name from settings.items[0].name
        product_name = product.get('number', 'Unknown')
        settings = product.get('settings', {})
        if isinstance(settings, dict):
            items = settings.get('items', [])
            if items and len(items) > 0:
                product_name = items[0].get('name', product_name)
        
        for cat_id in category_ids:
            if cat_id in cat_map and len(cat_map[cat_id]['example_products']) < 5:
                cat_map[cat_id]['example_products'].append({
                    'name': product_name,
                    'vendor': product.get('vendorNumber', ''),
                    'number': product.get('number', '')
                })
    
    categories_with_products = len([c for c in cat_map.values() if c['example_products']])
    logger.info(f"Mapped products to {categories_with_products} categories (out of {len(cat_map)} total)")
    return cat_map


def load_or_generate_category_embeddings(
    categories: List[Dict],
    category_product_map: Dict[str, Dict],
    client: OpenAI,
    cache_dir: Path,
    logger,
    force_refresh: bool = False
) -> Dict[str, List[float]]:
    """
    Load cached category embeddings or generate new ones.
    Now works with RAW API category data (uses 'id' field).
    
    Returns:
        Dict mapping category_id to embedding vector
    """
    cache_file = cache_dir / "category_embeddings.json"
    
    # Try to load from cache
    if cache_file.exists() and not force_refresh:
        logger.info(f"Loading cached category embeddings from {cache_file}...")
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Validate cache has all categories
            cached_ids = set(cache_data.keys())
            current_ids = set(str(cat.get('id', '')) for cat in categories if cat.get('id'))
            
            if cached_ids == current_ids:
                logger.info(f"Using cached embeddings for {len(cache_data)} categories")
                return cache_data
            else:
                logger.warning(f"Cache mismatch: {len(current_ids - cached_ids)} new categories, regenerating...")
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}, regenerating...")
    
    # Generate embeddings
    logger.info(f"Generating embeddings for {len(categories)} categories (this may take a minute)...")
    embeddings = {}
    
    for i, category in enumerate(categories, 1):
        cat_id = str(category.get('id', ''))
        if not cat_id:
            continue
            
        example_products = category_product_map.get(cat_id, {}).get('example_products', [])
        
        # Build category text
        cat_text = build_category_text(category, example_products)
        
        # Get embedding
        try:
            embedding = get_embedding(cat_text, client)
            embeddings[cat_id] = embedding
            
            if i % 10 == 0:
                logger.info(f"  Generated embeddings for {i}/{len(categories)} categories...")
            
            # Rate limiting (basic)
            time.sleep(0.05)  # 20 requests/second
            
        except Exception as e:
            logger.error(f"Failed to embed category {cat_id}: {e}")
            # Use zero vector as fallback
            embeddings[cat_id] = [0.0] * 1536
    
    # Save to cache
    logger.info(f"Saving category embeddings to cache...")
    cache_dir.mkdir(parents=True, exist_ok=True)
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(embeddings, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Category embeddings cached to {cache_file}")
    return embeddings


def find_best_category_by_embedding(
    product: Dict,
    categories: List[Dict],
    category_embeddings: Dict[str, List[float]],
    client: OpenAI,
    logger,
    include_details: bool = False
) -> Tuple[str, float, str]:
    """
    Find best matching category using embedding similarity.
    
    Args:
        product: Product to categorize
        categories: List of all categories
        category_embeddings: Precomputed category embeddings
        client: OpenAI client
        logger: Logger
        include_details: If True, include full product details in embedding
    
    Returns:
        Tuple of (category_id, confidence_score, reasoning)
    """
    # Build product text
    prod_text = build_product_text(product, include_details=include_details)
    
    # Get product embedding
    try:
        prod_embedding = get_embedding(prod_text, client)
    except Exception as e:
        logger.error(f"Failed to embed product: {e}")
        return None, 0, f"Embedding error: {str(e)}"
    
    # Calculate similarities
    similarities = {}
    for cat_id, cat_embedding in category_embeddings.items():
        similarity = cosine_similarity(prod_embedding, cat_embedding)
        similarities[cat_id] = similarity
    
    # Find best match
    if not similarities:
        return None, 0, "No categories available"
    
    best_cat_id = max(similarities, key=similarities.get)
    best_similarity = similarities[best_cat_id]
    
    # Convert similarity (0-1) to confidence (0-100)
    confidence = int(best_similarity * 100)
    
    # Get category info for reasoning (RAW API data uses 'id' field)
    category = next((c for c in categories if str(c.get('id', '')) == best_cat_id), None)
    if category:
        # Get category name from texts.items[0].name
        cat_name = 'Unknown'
        texts = category.get('texts', {})
        if isinstance(texts, dict):
            items = texts.get('items', [])
            if items and len(items) > 0:
                cat_name = items[0].get('name', 'Unknown')
        reasoning = f"Best match: {cat_name} (similarity: {best_similarity:.3f})"
    else:
        reasoning = f"Best match ID: {best_cat_id} (similarity: {best_similarity:.3f})"
    
    return best_cat_id, confidence, reasoning


def categorize_with_llm_fallback(
    product: Dict,
    categories: List[Dict],
    category_product_map: Dict[str, Dict],
    client: OpenAI,
    logger
) -> Dict[str, Any]:
    """
    Use LLM (fallback model from ai_config) as fallback for low-confidence cases.
    
    This is expensive but accurate - only used when embeddings fail.
    """
    from categorize_helpers import get_category_system_prompt, get_category_user_prompt, build_category_tree
    
    # Get fallback model from ai_config
    model_config = get_model_config(step="categorization")
    fallback_model = model_config["fallback_model"]
    
    # Build compact category tree
    category_tree = build_category_tree(categories, category_product_map, compact=True)
    
    # Get prompts
    system_prompt = get_category_system_prompt()
    user_prompt = get_category_user_prompt(product, category_tree, include_details=True)
    
    try:
        response = client.chat.completions.create(
            model=fallback_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=300,
            response_format={"type": "json_object"}
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Parse JSON
        result = json.loads(result_text)
        
        # Add fallback indicator
        result['fallback_used'] = True
        
        return result
        
    except Exception as e:
        logger.error(f"LLM fallback error: {e}")
        return {
            "category_id": None,
            "confidence": 0,
            "reasoning": f"LLM fallback error: {str(e)}",
            "error": True
        }


def process_products(
    products: List[Dict],
    categories: List[Dict],
    api_products: List[Dict],
    client: OpenAI,
    config: Dict,
    logger
) -> Tuple[List[Dict], Dict[str, float]]:
    """
    Process all products and assign categories using embeddings.
    
    Returns:
        Tuple of (categorized_products, cost_tracking_dict)
    """
    confidence_threshold = config.get("categorization", {}).get("confidence_threshold", 70)
    cache_dir = Path(config["paths"]["cache"])
    
    # Build category ID to number mapping (for setting primaryCategoryId)
    # categories from API have both 'id' and 'number'
    category_id_to_number = {}
    for cat in categories:
        cat_id = cat.get('id')
        cat_number = cat.get('number', '')
        if cat_id and cat_number:
            category_id_to_number[cat_id] = cat_number
            category_id_to_number[str(cat_id)] = cat_number  # Handle both int and string
    
    logger.info(f"Built category ID->number mapping for {len(category_id_to_number)} categories")
    
    # Build category-to-products map
    logger.info(f"Mapping {len(api_products)} existing products to categories...")
    category_product_map = build_category_with_products_map(categories, api_products, logger)
    
    # FILTER: Only use categories that have products
    categories_with_products = [
        cat for cat in categories 
        if str(cat.get('id', '')) in category_product_map and 
        category_product_map[str(cat.get('id', ''))]['example_products']
    ]
    
    logger.info(f"Filtered to {len(categories_with_products)} categories with products (from {len(categories)} total)")
    
    # Load or generate category embeddings (one-time cost) - ONLY for categories with products
    category_embeddings = load_or_generate_category_embeddings(
        categories_with_products,  # Use filtered list
        category_product_map,
        client,
        cache_dir,
        logger
    )
    
    # Get fallback model for logging
    model_config = get_model_config(step="categorization")
    fallback_model = model_config["fallback_model"]
    
    logger.info(f"Processing {len(products)} products with embedding-based categorization...")
    logger.info(f"Confidence threshold: {confidence_threshold}%, LLM fallback: {fallback_model}")
    
    categorized_products = []
    stats = {
        "total": len(products),
        "categorized": 0,
        "llm_fallback": 0,
        "errors": 0,
        "low_confidence": 0
    }
    
    # Track costs
    cost_tracking = {
        "total_cost": 0.0,
        "embedding_cost": 0.0,
        "llm_fallback_cost": 0.0,
        "embedding_calls": 0,
        "llm_calls": 0
    }
    
    for i, product in enumerate(products, 1):
        prod_name = product.get('ORIGINAL_PROD_NAME', product.get('PROD_NAME', f'Product {i}'))
        
        logger.info(f"[{i}/{len(products)}] Categorizing: {prod_name[:60]}...")
        
        # Try embedding-based matching first
        cat_id, confidence, reasoning = find_best_category_by_embedding(
            product,
            categories,
            category_embeddings,
            client,
            logger,
            include_details=False
        )
        
        result = {
            "category_id": cat_id,
            "confidence": confidence,
            "reasoning": reasoning,
            "method": "embedding"
        }
        
        # If low confidence, retry with more details
        if cat_id and confidence < 80:
            logger.info(f"  Low confidence ({confidence}%), retrying with product details...")
            cat_id2, confidence2, reasoning2 = find_best_category_by_embedding(
                product,
                categories,
                category_embeddings,
                client,
                logger,
                include_details=True
            )
            
            if confidence2 > confidence:
                result = {
                    "category_id": cat_id2,
                    "confidence": confidence2,
                    "reasoning": reasoning2,
                    "method": "embedding_detailed"
                }
        
        # If still low confidence (< 70%), use LLM fallback
        if result.get('confidence', 0) < confidence_threshold:
            logger.warning(f"  Very low confidence ({result.get('confidence')}%), using LLM fallback...")
            llm_result = categorize_with_llm_fallback(
                product,
                categories,
                category_product_map,
                client,
                logger
            )
            
            # Use LLM result if it's better
            if llm_result.get('confidence', 0) > result.get('confidence', 0):
                result = llm_result
                stats['llm_fallback'] += 1
        
        # Add categorization to product
        product['ai_categorization'] = result
        
        # IMPORTANT: Also set primaryCategoryId (required by Dandomain API)
        # Convert category_id to category_number
        if result.get('category_id'):
            cat_id = result['category_id']
            cat_number = category_id_to_number.get(cat_id) or category_id_to_number.get(str(cat_id))
            
            if cat_number:
                product['primaryCategoryId'] = cat_number
                logger.debug(f"  Set primaryCategoryId = {cat_number} (from category_id {cat_id})")
            else:
                logger.warning(f"  Could not find category number for category_id {cat_id}")
        
        # Track stats
        if result.get('error'):
            stats['errors'] += 1
            logger.warning(f"  [ERROR] {result.get('reasoning', 'Unknown error')}")
        elif result.get('category_id'):
            conf = result.get('confidence', 0)
            if conf >= confidence_threshold:
                stats['categorized'] += 1
                method = result.get('method', 'unknown')
                logger.info(f"  [OK] Category: {result['category_id']} (confidence: {conf}%, method: {method})")
            else:
                stats['low_confidence'] += 1
                logger.warning(f"  [WARN] Low confidence ({conf}%): Category {result['category_id']}")
        
        # Add categorization result to product
        product['ai_categorization'] = result
        product['primaryCategoryId'] = result.get('category_id')
        categorized_products.append(product)
        
        # Rate limiting
        if i < len(products):
            time.sleep(0.1)
    
    # Print summary
    logger.info("\n" + "="*60)
    logger.info("CATEGORIZATION SUMMARY (EMBEDDING-BASED)")
    logger.info("="*60)
    logger.info(f"Total products:        {stats['total']}")
    logger.info(f"Successfully assigned: {stats['categorized']} ({stats['categorized']/stats['total']*100:.1f}%)")
    logger.info(f"Low confidence:        {stats['low_confidence']}")
    logger.info(f"LLM fallback used:     {stats['llm_fallback']}")
    logger.info(f"Errors:                {stats['errors']}")
    logger.info("="*60)
    
    # Estimate costs (embeddings are extremely cheap)
    # Approximate: 1 embedding per product @ $0.02 per 1M tokens
    # Average product text ~200 tokens = $0.000004 per product
    estimated_embedding_cost = stats['total'] * 0.000004
    estimated_llm_cost = stats['llm_fallback'] * 0.0001  # Rough estimate for LLM calls
    total_cost = estimated_embedding_cost + estimated_llm_cost
    
    cost_tracking["total_cost"] = total_cost
    cost_tracking["embedding_cost"] = estimated_embedding_cost
    cost_tracking["llm_fallback_cost"] = estimated_llm_cost
    cost_tracking["embedding_calls"] = stats['total']
    cost_tracking["llm_calls"] = stats['llm_fallback']
    
    return categorized_products, cost_tracking


def main():
    """Main execution function."""
    print("\n" + "="*60)
    print("Step 3.5: Embedding-Based Product Categorization")
    print("="*60 + "\n")
    
    # Load config
    config = load_config()
    log_dir = Path(config["paths"]["logs"])
    output_dir = Path(config["paths"]["output"])
    
    # Setup logging
    logger = setup_logging(log_dir)
    logger.info("Starting embedding-based product categorization...")
    
    # Get API key
    api_key = get_api_key(logger, config)
    if not api_key:
        print("\n[ERROR] No OpenAI API key found!")
        print("   Set OPENAI_API_KEY in .env or config.yaml")
        return 1
    
    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)
    logger.info("OpenAI client initialized")
    
    # Load enriched products
    input_file = output_dir / "enriched_products.json"
    if not input_file.exists():
        logger.error(f"Input file not found: {input_file}")
        print(f"\n[ERROR] {input_file} not found!")
        print("   Run Step 3 (3_process_images.py) first")
        return 1
    
    logger.info(f"Loading products from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        products = json.load(f)
    logger.info(f"Loaded {len(products)} products")
    
    # Load categories from API
    logger.info("Fetching categories from Dandomain API...")
    try:
        # Load RAW categories from cache (has 'id' and 'number' fields)
        categories_cache_file = PROJECT_ROOT / "cache" / "categories_cache.json"
        if not categories_cache_file.exists():
            logger.error("categories_cache.json not found. Run API sync first.")
            print("\n[ERROR] categories_cache.json not found")
            print("   Run 'Opdater Cache' in Streamlit first")
            return 1
        
        with open(categories_cache_file, 'r', encoding='utf-8') as f:
            categories = json.load(f)
        
        logger.info(f"Loaded {len(categories)} categories from cache")
        
        # Show cache status
        cache_status = get_cache_status()
        if cache_status.get('categories_cache.json', {}).get('exists'):
            cache_age = cache_status['categories_cache.json']['age_hours']
            logger.info(f"Using cached category data ({cache_age:.1f} hours old)")
    except Exception as e:
        logger.error(f"Failed to load categories: {e}")
        print(f"\n[ERROR] Error loading categories: {e}")
        print("   Check API_KEY in .env and run 'Opdater Cache' in Streamlit")
        return 1
    
    # Load existing products from API (for category examples)
    logger.info("Fetching existing products from Dandomain API...")
    try:
        # Load RAW products from cache (has 'id', 'number', 'primaryCategoryId', etc.)
        products_cache_file = PROJECT_ROOT / "cache" / "products_cache.json"
        if not products_cache_file.exists():
            logger.warning("products_cache.json not found. Will continue without product examples.")
            api_products = []
        else:
            with open(products_cache_file, 'r', encoding='utf-8') as f:
                api_products = json.load(f)
            
            logger.info(f"Loaded {len(api_products)} existing products from cache")
            
            if cache_status.get('products_cache.json', {}).get('exists'):
                cache_age = cache_status['products_cache.json']['age_hours']
                logger.info(f"Using cached product data ({cache_age:.1f} hours old)")
    except Exception as e:
        logger.warning(f"Failed to load products (will continue without examples): {e}")
        api_products = []
    
    # Process products
    try:
        categorized_products, cost_tracking = process_products(
            products,
            categories,
            api_products,
            client,
            config,
            logger
        )
    except KeyboardInterrupt:
        logger.warning("\n[WARN] Interrupted by user")
        print("\n[WARN] Categorization interrupted!")
        return 1
    except Exception as e:
        logger.error(f"Processing error: {e}", exc_info=True)
        print(f"\n[ERROR] Error during processing: {e}")
        return 1
    
    # Save results
    output_file = output_dir / "categorized_products.json"
    logger.info(f"Saving categorized products to {output_file}...")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(categorized_products, f, ensure_ascii=False, indent=2)
    
    # Save or update cost information
    cost_summary = {
        "step": "Step 3.5 (Categorization)",
        "total_cost_usd": round(cost_tracking["total_cost"], 6),
        "products_processed": len(categorized_products),
        "cost_by_model": {
            "text-embedding-3-small": round(cost_tracking["embedding_cost"], 6),
            "gpt-3.5-turbo-fallback": round(cost_tracking["llm_fallback_cost"], 6)
        },
        "embedding_calls": cost_tracking["embedding_calls"],
        "llm_fallback_calls": cost_tracking["llm_calls"],
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        cost_file = output_dir / "ai_costs.json"
        # If file exists, load it to accumulate costs
        if cost_file.exists():
            with open(cost_file, 'r', encoding='utf-8') as f:
                existing_costs = json.load(f)
            # Accumulate total cost
            total_cost_accumulated = existing_costs.get("total_cost_usd", 0.0) + cost_summary["total_cost_usd"]
            cost_summary["total_cost_usd"] = round(total_cost_accumulated, 6)
            # Merge model costs
            existing_by_model = existing_costs.get("cost_by_model", {})
            for model, cost in cost_summary["cost_by_model"].items():
                existing_by_model[model] = round(existing_by_model.get(model, 0.0) + cost, 6)
            cost_summary["cost_by_model"] = existing_by_model
            # Add step-specific metadata
            cost_summary["products_processed"] = existing_costs.get("products_processed", 0) + len(categorized_products)
        
        with open(cost_file, 'w', encoding='utf-8') as f:
            json.dump(cost_summary, f, ensure_ascii=False, indent=2)
        logger.info(f"✓ Cost summary saved: {cost_file}")
        logger.info(f"  Total cost: ${cost_summary['total_cost_usd']:.6f}")
    except Exception as e:
        logger.warning(f"Could not save cost summary: {e}")
    
    logger.info("Categorization complete!")
    print(f"\n[SUCCESS] Categorized products saved to:")
    print(f"   {output_file}")
    print(f"\nEstimated cost: ${cost_tracking['total_cost']:.6f}")
    print(f"Cost savings: ~75x cheaper than pure LLM approach!")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
