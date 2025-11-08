#!/usr/bin/env python3
"""
Step 4: AI-Powered Product Enrichment
Generates product descriptions using OpenAI with Agents SDK.

The Agents SDK transparently handles:
- Chat Completions API for gpt-4o-mini, gpt-3.5-turbo
- Responses API for gpt-5-nano, gpt-5-mini (no manual API switching needed)

Hybrid Strategy:
1. Primary model (configurable in ai_config.py): Fast, cost-effective
2. Fallback model (configurable in ai_config.py): Better reasoning - used if:
   - Confidence score < 70% (configurable)
   - Description too short (< 50 chars)

Model selection: Edit ai_config.py ENRICHMENT_PRIMARY_MODEL and ENRICHMENT_FALLBACK_MODEL
Do NOT hardcode models here - always use ai_config.py as single source of truth.

Input:  data/output/categorized_products.json (from Step 3.5)
Output: data/output/final_products.json (with AI fields)

Logs to: logs/4_generate_ai.log
"""

import json
import sys
import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any
import yaml
from dotenv import load_dotenv

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from ai_config import (
    get_system_prompt,
    get_user_prompt,
    get_model_config,
    ProductDescriptionAgent,
)

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
        "ai": {},
        "logging": {"level": "INFO"}
    }


def setup_logging(log_dir: Path, log_file_name: str = "4_generate_ai.log"):
    """Configure logging to file and console"""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / log_file_name
    
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='a')
    file_handler.setFormatter(formatter)
    
    console_handler = SafeStreamHandler(SafeStream())
    console_handler.setFormatter(formatter)
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def get_api_key(logger, config):
    """Get OpenAI API key from .env, environment, or config."""
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logger.debug(f"Loaded .env from {env_path}")
    
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("AI_API_KEY")
    if api_key:
        logger.info("Using OpenAI API key from environment (.env or system)")
        return api_key
    
    if config.get("ai", {}).get("api_key"):
        logger.info("Using OpenAI API key from config")
        return config["ai"]["api_key"]
    
    logger.warning("No OpenAI API key found. Set OPENAI_API_KEY in .env file.")
    return None


def call_agent_api(logger, product: Dict[str, Any], agent: ProductDescriptionAgent, system_prompt: str, fallback_agent: Optional[ProductDescriptionAgent] = None, quality_threshold: float = 0.70) -> Optional[Dict[str, Any]]:
    """
    Call AI agent (Agents SDK handles both Chat Completions and Responses API).
    """
    try:
        # Extract fields from product
        product_name = (
            product.get("ORIGINAL_PROD_NAME")
            or product.get("PROD_NUM_old")
            or product.get("product_number")
            or product.get("PROD_NUM")
            or "Unknown"
        )
        if isinstance(product_name, str) and " - Deaktiveret" in product_name:
            product_name = product_name.replace(" - Deaktiveret", "").strip()
        
        supplier_info = product.get("supplier_info", "")
        product_url = product.get("product_url", "")
        brand = product.get("brand") or product.get("BrandID", "Unknown")
        color = product.get("color") or product.get("Color", "Unknown")
        size = product.get("size") or product.get("FIELD_20", "Unknown")
        
        category = (
            product.get("recommended_category")
            or product.get("recommendedCategory")
            or product.get("category")
            or product.get("BunzlItemSubGroup")
            or product.get("BunzlItemMainGroup")
            or "Unknown"
        )
        
        packaging = product.get("packaging")
        if not packaging:
            data_area = product.get("DataAreaID", "cc")
            if data_area == "mln":
                packaging = product.get("PackingInfoInStockUnit", "Unknown")
            else:
                packaging = product.get("SalesUnit_PackingInfo", "Unknown")
        
        certifications = product.get("certifications") or product.get("Certifications", "Unknown")
        afgift = product.get("afgift") or product.get("FIELD_18") or 0
        try:
            afgift = float(afgift) if afgift else 0
        except (ValueError, TypeError):
            afgift = 0
        
        prod_notes = product.get("PROD_NOTES", "")
        if prod_notes:
            supplier_info = f"{supplier_info}\n\nProdukt noter: {prod_notes}".strip()
        
        # Build user prompt
        user_prompt = get_user_prompt(
            product_name=product_name,
            category=category,
            brand=brand,
            color=color,
            size=size,
            packaging=packaging,
            certifications=certifications,
            afgift=afgift,
            supplier_info=supplier_info,
            product_url=product_url
        )
        
        logger.debug(f"  Calling agent ({agent.model})...")
        
        # Call agent (Agents SDK handles Chat Completions vs Responses API automatically)
        response_text = agent.generate_descriptions(user_prompt, system_prompt)
        
        if not response_text:
            logger.error(f"  Empty response from agent")
            return None
        
        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            response_text = response_text.strip("`").replace("```json", "").replace("```", "").strip()
        
        # Parse JSON
        ai_data = json.loads(response_text)
        logger.debug(f"  ✓ Agent response parsed successfully")
        
        # Check quality for fallback decision
        confidence = ai_data.get("confidence", 0.95)
        description = ai_data.get("DESC_LONG", "").strip()
        
        should_retry = (
            confidence < quality_threshold or 
            len(description) < 50
        )
        
        if should_retry and fallback_agent:
            logger.debug(f"  Quality check failed (confidence: {confidence}, desc_len: {len(description)})")
            logger.info(f"  Retrying with fallback agent ({fallback_agent.model})...")
            return call_agent_api(logger, product, fallback_agent, system_prompt, fallback_agent=None, quality_threshold=quality_threshold)
        
        return ai_data
        
    except json.JSONDecodeError as e:
        logger.error(f"  JSON parse error: {e}")
        return None
    except Exception as e:
        logger.error(f"  Agent error: {e}")
        return None


def atomic_write_json(file_path, data):
    """Write JSON atomically: write to .tmp, then rename."""
    tmp_path = str(file_path) + ".tmp"
    with open(tmp_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    Path(tmp_path).replace(file_path)


def generate_ai_descriptions(logger, config, input_file: Optional[str] = None):
    """
    Read categorized_products.json, enrich with AI descriptions, write final_products.json
    
    Uses Agents SDK which handles Chat Completions and Responses API transparently.
    """
    output_dir = Path(config["paths"]["output"])
    
    if input_file:
        enriched_path = Path(input_file)
        if not enriched_path.exists() and not enriched_path.is_absolute():
            enriched_path = output_dir / input_file
    else:
        enriched_path = output_dir / "categorized_products.json"
    
    if not enriched_path.exists():
        logger.error(f"Input file not found: {enriched_path}")
        return False
    
    api_key = get_api_key(logger, config)
    if not api_key:
        logger.warning("Running in DRY-RUN mode (no API key). Showing mock AI fields.")
        dry_run = True
        agent = None
        fallback_agent = None
    else:
        dry_run = False
        try:
            model_config = get_model_config(step="enrichment")
            primary_model = model_config["model"]
            fallback_model = model_config["fallback_model"]
            temperature = model_config["temperature"]
            
            logger.debug(f"Initializing agents: {primary_model} (primary), {fallback_model} (fallback)")
            agent = ProductDescriptionAgent(model=primary_model, temperature=temperature)
            fallback_agent = ProductDescriptionAgent(model=fallback_model, temperature=temperature)
        except Exception as e:
            logger.error(f"Failed to initialize agents: {e}")
            return False
    
    ai_config = config.get("ai", {})
    model_config = get_model_config(step="enrichment")
    
    primary_model = model_config["model"]
    fallback_model = model_config["fallback_model"]
    quality_threshold = ai_config.get("quality_threshold", 0.70)
    system_prompt = get_system_prompt()
    
    logger.info(f"AI Enrichment Setup (Using Agents SDK):")
    logger.info(f"  Primary model: {primary_model}")
    logger.info(f"  Fallback model: {fallback_model}")
    logger.info(f"  Quality threshold: {quality_threshold}")
    
    logger.info(f"Loading products: {enriched_path}")
    with open(enriched_path, 'r', encoding='utf-8') as f:
        products = json.load(f)
    
    if isinstance(products, dict):
        products = [products]
    
    logger.info(f"Processing {len(products)} products for AI enrichment")
    
    processed_count = 0
    success_count = 0
    error_count = 0
    
    for idx, product in enumerate(products, 1):
        product_num = product.get("product_number", f"product_{idx}")
        logger.info(f"[{idx}/{len(products)}] {product_num}")
        
        if dry_run:
            logger.debug(f"  (dry-run) Generating mock AI fields...")
            ai_data = {
                "DESC_SHORT": "Premium cleaning brush",
                "DESC_LONG": "This is a professional-grade cleaning brush designed for commercial and industrial use. The brush features high-quality materials and durable construction, making it ideal for tough cleaning tasks.",
                "PROD_SEARCHWORD": "cleaning brush, professional brush, industrial cleaner, floor brush, commercial cleaning",
                "META_DESCRIPTION": "Professional cleaning brush for B2B use. Durable, high-quality design. Køb her »",
            }
            logger.info(f"  ✓ Mock AI fields generated")
        else:
            if agent:
                ai_data = call_agent_api(
                    logger, product,
                    agent=agent,
                    system_prompt=system_prompt,
                    fallback_agent=fallback_agent,
                    quality_threshold=quality_threshold
                )
                if not ai_data:
                    logger.warning(f"  Skipping product due to agent failure")
                    error_count += 1
                    continue
            else:
                logger.warning(f"  Agent not available")
                error_count += 1
                continue
        
        # Merge AI data into product
        product["DESC_SHORT"] = ai_data.get("DESC_SHORT", "")
        product["DESC_LONG"] = ai_data.get("DESC_LONG", "")
        product["PROD_SEARCHWORD"] = ai_data.get("PROD_SEARCHWORD", "")
        product["META_DESCRIPTION"] = ai_data.get("META_DESCRIPTION", "")
        
        processed_count += 1
        success_count += 1
    
    # Write final output
    final_path = output_dir / "final_products.json"
    atomic_write_json(final_path, products)
    logger.info(f"✓ Final products JSON: {final_path}")
    
    logger.info("=" * 60)
    logger.info("✓ Step 4 complete")
    logger.info(f"  Processed: {processed_count} products")
    logger.info(f"  Successful: {success_count}")
    if error_count > 0:
        logger.info(f"  Errors: {error_count}")
    if dry_run:
        logger.info(f"  Mode: DRY-RUN (set OPENAI_API_KEY to use real API)")
    logger.info(f"  Output: {final_path}")
    logger.info("=" * 60)
    
    return True


def main():
    """Main entry point."""
    config = load_config()
    logger = setup_logging(Path(config["paths"]["logs"]))
    
    logger.info("=" * 60)
    logger.info("Step 4: AI-Powered Product Enrichment")
    logger.info("=" * 60)
    
    input_file = None
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        logger.info(f"Using custom input file: {input_file}")
    
    success = generate_ai_descriptions(logger, config, input_file)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
