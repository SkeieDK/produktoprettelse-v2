#!/usr/bin/env python3
"""
Regenerate a single product's AI descriptions with custom feedback.

Usage:
  python scripts/regenerate_product.py <product_number> [--feedback "Make it more technical"]
"""

import sys
import json
import argparse
from pathlib import Path
from typing import Optional

# Add parent directory to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))

# Simple config function - replaces csv_manager.load_config()
def load_config():
    """Load configuration with project paths."""
    return {
        "paths": {
            "output": str(PROJECT_ROOT / "data" / "output"),
            "cache": str(PROJECT_ROOT / "cache"),
            "logs": str(PROJECT_ROOT / "logs")
        }
    }

# Now import directly from scripts (which is in sys.path)
from ai_config import (
    get_system_prompt,
    get_user_prompt,
    get_model_config,
    ProductDescriptionAgent,
)
import importlib.util
spec = importlib.util.spec_from_file_location(
    "generate_ai_module",
    SCRIPTS_DIR / "4_generate_ai.py"
)
generate_ai_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generate_ai_module)

# Extract functions from module
setup_logging = generate_ai_module.setup_logging
call_agent_api = generate_ai_module.call_agent_api
find_similar_example = generate_ai_module.find_similar_example
load_example_cache = generate_ai_module.load_example_cache
save_example_cache = generate_ai_module.save_example_cache
atomic_write_json = generate_ai_module.atomic_write_json

from openai import OpenAI


def regenerate_single_product(
    logger,
    config,
    product_number: str,
    feedback: Optional[str] = None
) -> bool:
    """
    Regenerate AI descriptions for a single product.
    
    Args:
        logger: Logger instance
        config: Application config
        product_number: Product number to regenerate
        feedback: Optional feedback to append to prompt
    
    Returns:
        True if successful, False otherwise
    """
    output_dir = Path(config["paths"]["output"])
    cache_dir = Path(config["paths"]["cache"])
    
    # Load final products
    final_path = output_dir / "final_products.json"
    if not final_path.exists():
        logger.error(f"Final products not found: {final_path}")
        return False
    
    with open(final_path, 'r', encoding='utf-8') as f:
        products = json.load(f)
    
    if isinstance(products, dict):
        products = [products]
    
    # Find the product to regenerate
    target_product = None
    product_index = None
    for idx, prod in enumerate(products):
        if prod.get("product_number", "") == product_number:
            target_product = prod
            product_index = idx
            break
    
    if not target_product:
        logger.error(f"Product not found: {product_number}")
        logger.error(f"Available products: {[p.get('product_number') for p in products]}")
        return False
    
    logger.info(f"Found product: {product_number}")
    logger.info(f"  Name: {target_product.get('ORIGINAL_PROD_NAME', 'Unknown')}")
    
    # Setup AI
    api_key = get_api_key(logger, config)
    if not api_key:
        logger.error("No API key available - cannot regenerate")
        return False
    
    try:
        model_config = get_model_config(step="enrichment")
        primary_model = model_config["model"]
        temperature = model_config["temperature"]
        
        logger.info(f"Using model: {primary_model}")
        agent = ProductDescriptionAgent(model=primary_model, temperature=temperature)
        openai_client = OpenAI(api_key=api_key)
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        return False
    
    # Load existing products for examples (exclude current product)
    other_products = [p for p in products if p.get("product_number") != product_number]
    
    # Load caches
    cache_data = load_example_cache(cache_dir)
    golden_examples_path = cache_dir / "golden_examples.json"
    golden_examples = {}
    if golden_examples_path.exists():
        with open(golden_examples_path, 'r', encoding='utf-8') as f:
            golden_examples = json.load(f)
    
    # Find example
    example_product = None
    if other_products:
        try:
            example_product = find_similar_example(
                logger=logger,
                current_product=target_product,
                existing_products=other_products,
                cache_data=cache_data,
                client=openai_client,
                min_quality_score=0.7,
                golden_examples=golden_examples
            )
            if example_product:
                logger.info(f"  Using example: {example_product.get('ORIGINAL_PROD_NAME', 'Unknown')[:40]}...")
        except Exception as e:
            logger.warning(f"  Example search failed: {e}")
    
    # Get system prompt
    system_prompt = get_system_prompt()
    
    # Add feedback to system prompt if provided
    if feedback:
        logger.info(f"  Feedback: {feedback}")
        system_prompt = f"""{system_prompt}

IMPORTANT USER FEEDBACK:
{feedback}

Please incorporate this feedback into your response while maintaining all required fields and format."""
    
    # Generate descriptions
    logger.info("Calling AI agent...")
    ai_data = call_agent_api(
        logger=logger,
        product=target_product,
        agent=agent,
        system_prompt=system_prompt,
        fallback_agent=None,
        quality_threshold=0.0,  # Don't use fallback for regeneration
        example_product=example_product
    )
    
    if not ai_data:
        logger.error("AI generation failed")
        return False
    
    # Update product
    target_product["DESC_SHORT"] = ai_data.get("DESC_SHORT", "")
    target_product["DESC_LONG"] = ai_data.get("DESC_LONG", "")
    target_product["PROD_SEARCHWORD"] = ai_data.get("PROD_SEARCHWORD", "")
    target_product["META_DESCRIPTION"] = ai_data.get("META_DESCRIPTION", "")
    
    # Mark as regenerated
    target_product["regenerated"] = True
    if feedback:
        target_product["regeneration_feedback"] = feedback
    
    # Update in list
    products[product_index] = target_product
    
    # Save updated products
    atomic_write_json(final_path, products)
    logger.info(f"✓ Product updated: {final_path}")
    
    # Save cache
    save_example_cache(cache_dir, cache_data)
    
    logger.info("=" * 60)
    logger.info("✓ Regeneration complete")
    logger.info(f"  Product: {product_number}")
    logger.info(f"  DESC_SHORT: {ai_data.get('DESC_SHORT', '')[:60]}...")
    logger.info(f"  DESC_LONG: {ai_data.get('DESC_LONG', '')[:80]}...")
    logger.info("=" * 60)
    
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Regenerate a single product's AI descriptions with custom feedback"
    )
    parser.add_argument("product_number", help="Product number to regenerate")
    parser.add_argument(
        "--feedback",
        help="Custom feedback to guide regeneration (e.g., 'Make it more technical')",
        default=None
    )
    
    args = parser.parse_args()
    
    config = load_config()
    logger = setup_logging(Path(config["paths"]["logs"]))
    
    logger.info("=" * 60)
    logger.info("Regenerate Product with Feedback")
    logger.info("=" * 60)
    
    success = regenerate_single_product(
        logger=logger,
        config=config,
        product_number=args.product_number,
        feedback=args.feedback
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
