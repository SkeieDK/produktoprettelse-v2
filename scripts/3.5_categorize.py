#!/usr/bin/env python3
"""
Step 3.5: AI-Powered Product Categorization
Assigns products to best-suited categories using Dandomain API + OpenAI.

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
from typing import Optional, Dict, Any, List
import yaml
from dotenv import load_dotenv
from openai import OpenAI, RateLimitError, APIError

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from api_manager import get_categories, get_products, get_cache_status

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
                        "cache": paths.get("cache_dir", "data/cache"),
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
            "cache": str(PROJECT_ROOT / "data" / "cache"),
            "logs": str(PROJECT_ROOT / "logs"),
        },
        "ai": {"provider": "openai", "model": "gpt-4o-mini", "temperature": 0.3},
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


def build_category_with_products_map(categories: List[Dict], products: List[Dict], logger) -> Dict[str, Dict]:
    """
    Build a map of categories with example products from each.
    
    Returns:
        Dict mapping category_id to {category_info, example_products}
    """
    logger.info("Building category-to-products map...")
    
    # Create category map
    cat_map = {}
    for cat in categories:
        cat_id = str(cat['PROD_CAT_ID'])
        cat_map[cat_id] = {
            'category_info': cat,
            'example_products': []
        }
    
    # Map products to categories
    for product in products:
        # Check Categories field
        product_cats = product.get('Categories', [])
        
        # Also check DefaultCategoryId and PrimaryCategoryId
        default_cat = str(product.get('DefaultCategoryId', ''))
        primary_cat = str(product.get('PrimaryCategoryId', ''))
        
        category_ids = set()
        
        # Collect all category IDs
        for cat in product_cats:
            cat_id = str(cat.get('id', ''))
            if cat_id:
                category_ids.add(cat_id)
        
        if default_cat:
            category_ids.add(default_cat)
        if primary_cat:
            category_ids.add(primary_cat)
        
        # Add product to relevant categories (limit 3 examples per category)
        for cat_id in category_ids:
            if cat_id in cat_map and len(cat_map[cat_id]['example_products']) < 3:
                cat_map[cat_id]['example_products'].append({
                    'name': product.get('ItemName', product.get('ItemID', 'Unknown')),
                    'vendor': product.get('VendorNumber', ''),
                    'item_id': product.get('ItemID', '')
                })
    
    logger.info(f"Mapped products to {len([c for c in cat_map.values() if c['example_products']])} categories")
    return cat_map


def build_category_tree(categories: List[Dict], category_product_map: Dict[str, Dict]) -> str:
    """
    Build a formatted category tree for the AI prompt with example products.
    Groups by hovedkategori (top level) for readability.
    """
    # Group by hovedkategori
    tree_dict = {}
    for cat in categories:
        hovedkat = cat.get('hovedkategori', 'Ingen hovedkategori')
        if hovedkat not in tree_dict:
            tree_dict[hovedkat] = []
        tree_dict[hovedkat].append(cat)
    
    # Build formatted tree with products
    tree_lines = []
    for hovedkat, cats in sorted(tree_dict.items()):
        tree_lines.append(f"\n[{hovedkat}]")
        for cat in cats:
            cat_id = str(cat['PROD_CAT_ID'])
            path = cat.get('kategori_sti', cat.get('nederste_kategori', 'Unknown'))
            tree_lines.append(f"  - ID: {cat_id} | {path}")
            
            # Add example products if available
            if cat_id in category_product_map:
                examples = category_product_map[cat_id]['example_products']
                if examples:
                    tree_lines.append(f"    Eksempler: {', '.join([p['name'] for p in examples[:3]])}")
    
    return "\n".join(tree_lines)


def get_category_system_prompt() -> str:
    """System prompt for category classification."""
    return """You are a product categorization expert for a B2B cleaning and maintenance supplies webshop.

Your task: Analyze product details and assign the most appropriate category from the provided hierarchy.

Guidelines:
- Consider product type, vendor, intended use, and specifications
- Look at example products already in each category to understand what belongs there
- Prefer specific categories over general ones (e.g., "Børster > Industribørster" over just "Børster")
- Match similar products to categories with similar existing products
- Use vendor patterns (e.g., if Vikan products are in a category, similar Vikan items likely belong there)
- B2B focus: prioritize professional/industrial categories over consumer ones
- If no good fit exists (confidence < 70%), suggest creating a new category

Output requirements:
- Return ONLY valid JSON (no markdown, no code fences)
- Include confidence score (0-100)
- Provide brief reasoning (mention similar products if relevant)
- If suggesting new category, specify parent and rationale"""


def get_category_user_prompt(product: Dict, category_tree: str) -> str:
    """Build user prompt for categorization."""
    # Extract product details
    prod_name = product.get('ORIGINAL_PROD_NAME', product.get('PROD_NAME', 'Unknown'))
    vendor = product.get('PrimaryVendorName', 'Unknown')
    
    # Get supplier info if available
    supplier_info = product.get('supplier_info', {})
    description = supplier_info.get('description', '')
    specifications = supplier_info.get('specifications', '')
    
    # Get any existing category hints
    existing_cat = product.get('DefaultCategoryId', '')
    
    prompt = f"""Product to categorize:
- Name: {prod_name}
- Vendor: {vendor}
- Existing Category ID (if any): {existing_cat}

"""
    
    if description:
        prompt += f"- Description: {description[:300]}...\n"
    
    if specifications:
        prompt += f"- Specifications: {specifications[:200]}...\n"
    
    prompt += f"""
Available categories (hierarchy):
{category_tree}

Return ONLY this JSON format:

{{
  "category_id": "123",
  "confidence": 85,
  "reasoning": "Brief explanation why this category fits"
}}

OR if no good fit (confidence < 70%):

{{
  "category_id": null,
  "confidence": 45,
  "reasoning": "Why no existing category fits",
  "suggest_new": true,
  "new_category": {{
    "name": "Suggested category name",
    "parent_id": "123",
    "description": "Why this new category is needed"
  }}
}}

Return ONLY the JSON object. No markdown, no explanation."""
    
    return prompt


def categorize_product(
    product: Dict,
    categories: List[Dict],
    category_tree: str,
    category_product_map: Dict[str, Dict],
    client: OpenAI,
    model: str,
    temperature: float,
    logger
) -> Dict[str, Any]:
    """
    Use AI to categorize a single product.
    
    Returns:
        Dict with category assignment or suggestion
    """
    system_prompt = get_category_system_prompt()
    user_prompt = get_category_user_prompt(product, category_tree)
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=temperature,
            max_tokens=500
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Remove markdown code fences if present
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
            result_text = result_text.strip()
        
        # Parse JSON
        result = json.loads(result_text)
        
        # Validate result
        if "category_id" not in result and "suggest_new" not in result:
            logger.warning(f"Invalid AI response format: {result_text[:100]}")
            return {
                "category_id": None,
                "confidence": 0,
                "reasoning": "AI returned invalid format",
                "error": True
            }
        
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse AI response: {e}")
        logger.debug(f"Response was: {result_text[:200]}")
        return {
            "category_id": None,
            "confidence": 0,
            "reasoning": f"JSON parse error: {str(e)}",
            "error": True
        }
    except Exception as e:
        logger.error(f"AI categorization error: {e}")
        return {
            "category_id": None,
            "confidence": 0,
            "reasoning": f"Error: {str(e)}",
            "error": True
        }


def process_products(
    products: List[Dict],
    categories: List[Dict],
    api_products: List[Dict],
    client: OpenAI,
    config: Dict,
    logger
) -> List[Dict]:
    """
    Process all products and assign categories.
    """
    model = config.get("ai", {}).get("model", "gpt-4o-mini")
    temperature = config.get("ai", {}).get("temperature", 0.3)
    confidence_threshold = config.get("categorization", {}).get("confidence_threshold", 70)
    
    # Build category-to-products map
    logger.info(f"Mapping {len(api_products)} existing products to categories...")
    category_product_map = build_category_with_products_map(categories, api_products, logger)
    
    # Build category tree once
    logger.info(f"Building category tree from {len(categories)} categories...")
    category_tree = build_category_tree(categories, category_product_map)
    
    logger.info(f"Processing {len(products)} products with AI categorization...")
    logger.info(f"Model: {model}, Temperature: {temperature}, Confidence threshold: {confidence_threshold}%")
    
    categorized_products = []
    stats = {
        "total": len(products),
        "categorized": 0,
        "needs_new_category": 0,
        "errors": 0,
        "low_confidence": 0
    }
    
    for i, product in enumerate(products, 1):
        prod_name = product.get('ORIGINAL_PROD_NAME', product.get('PROD_NAME', f'Product {i}'))
        
        logger.info(f"[{i}/{len(products)}] Categorizing: {prod_name[:60]}...")
        
        # Get AI categorization
        result = categorize_product(
            product,
            categories,
            category_tree,
            category_product_map,
            client,
            model,
            temperature,
            logger
        )
        
        # Add categorization to product
        product['ai_categorization'] = result
        
        # Track stats
        if result.get('error'):
            stats['errors'] += 1
            logger.warning(f"  ❌ Error: {result.get('reasoning', 'Unknown error')}")
        elif result.get('suggest_new'):
            stats['needs_new_category'] += 1
            new_cat = result.get('new_category', {})
            logger.warning(f"  🆕 Suggests new category: {new_cat.get('name', 'N/A')}")
            logger.info(f"     Reasoning: {result.get('reasoning', 'N/A')}")
        elif result.get('category_id'):
            confidence = result.get('confidence', 0)
            if confidence >= confidence_threshold:
                stats['categorized'] += 1
                logger.info(f"  ✅ Category: {result['category_id']} (confidence: {confidence}%)")
            else:
                stats['low_confidence'] += 1
                logger.warning(f"  ⚠️ Low confidence ({confidence}%): Category {result['category_id']}")
            
            if result.get('reasoning'):
                logger.debug(f"     Reasoning: {result['reasoning']}")
        
        categorized_products.append(product)
        
        # Rate limiting (basic)
        if i < len(products):
            time.sleep(0.5)  # 2 requests/second
    
    # Print summary
    logger.info("\n" + "="*60)
    logger.info("CATEGORIZATION SUMMARY")
    logger.info("="*60)
    logger.info(f"Total products:        {stats['total']}")
    logger.info(f"Successfully assigned: {stats['categorized']} ({stats['categorized']/stats['total']*100:.1f}%)")
    logger.info(f"Low confidence:        {stats['low_confidence']}")
    logger.info(f"Need new category:     {stats['needs_new_category']}")
    logger.info(f"Errors:                {stats['errors']}")
    logger.info("="*60)
    
    return categorized_products


def main():
    """Main execution function."""
    print("\n" + "="*60)
    print("Step 3.5: AI-Powered Product Categorization")
    print("="*60 + "\n")
    
    # Load config
    config = load_config()
    log_dir = Path(config["paths"]["logs"])
    output_dir = Path(config["paths"]["output"])
    
    # Setup logging
    logger = setup_logging(log_dir)
    logger.info("Starting product categorization...")
    
    # Get API key
    api_key = get_api_key(logger, config)
    if not api_key:
        print("\n❌ Error: No OpenAI API key found!")
        print("   Set OPENAI_API_KEY in .env or config.yaml")
        return 1
    
    # Initialize OpenAI client
    client = OpenAI(api_key=api_key)
    logger.info("OpenAI client initialized")
    
    # Load enriched products
    input_file = output_dir / "enriched_products.json"
    if not input_file.exists():
        logger.error(f"Input file not found: {input_file}")
        print(f"\n❌ Error: {input_file} not found!")
        print("   Run Step 3 (3_process_images.py) first")
        return 1
    
    logger.info(f"Loading products from {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        products = json.load(f)
    logger.info(f"Loaded {len(products)} products")
    
    # Load categories from API
    logger.info("Fetching categories from Dandomain API...")
    try:
        categories = get_categories(use_cache=True)
        logger.info(f"Loaded {len(categories)} categories")
        
        # Show cache status
        cache_status = get_cache_status()
        if cache_status.get('categories_cache.json', {}).get('exists'):
            cache_age = cache_status['categories_cache.json']['age_hours']
            logger.info(f"Using cached category data ({cache_age:.1f} hours old)")
    except Exception as e:
        logger.error(f"Failed to load categories: {e}")
        print(f"\n❌ Error loading categories: {e}")
        print("   Check API_KEY in .env and api_manager.py configuration")
        return 1
    
    # Load existing products from API (for category examples)
    logger.info("Fetching existing products from Dandomain API...")
    try:
        api_products = get_products(use_cache=True)
        logger.info(f"Loaded {len(api_products)} existing products")
        
        if cache_status.get('products_cache.json', {}).get('exists'):
            cache_age = cache_status['products_cache.json']['age_hours']
            logger.info(f"Using cached product data ({cache_age:.1f} hours old)")
    except Exception as e:
        logger.warning(f"Failed to load products (will continue without examples): {e}")
        api_products = []
    
    # Process products
    try:
        categorized_products = process_products(
            products,
            categories,
            api_products,
            client,
            config,
            logger
        )
    except KeyboardInterrupt:
        logger.warning("\n⚠️ Interrupted by user")
        print("\n⚠️ Categorization interrupted!")
        return 1
    except Exception as e:
        logger.error(f"Processing error: {e}", exc_info=True)
        print(f"\n❌ Error during processing: {e}")
        return 1
    
    # Save results
    output_file = output_dir / "categorized_products.json"
    logger.info(f"Saving categorized products to {output_file}...")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(categorized_products, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✅ Categorization complete!")
    print(f"\n✅ Success! Categorized products saved to:")
    print(f"   {output_file}")
    print(f"\n💡 Next step: Review categorizations, then run Step 4 (4_generate_ai.py)")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
