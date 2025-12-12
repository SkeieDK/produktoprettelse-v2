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
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# Use core utilities (consolidated from multiple implementations)
from core.config import load_config, get_api_key, get_project_root
from core.logging import get_logger, setup_logging
from core.file_utils import load_json, save_json, atomic_write_json

from ai_config import (
    get_model_config,
    WRITER_SYSTEM_PROMPT,
    WRITER_TASK_PROMPT,
    REVIEWER_SYSTEM_PROMPT,
    REVIEWER_MODEL
)
import ai_config as ai_config_module
from scripts.ai_agents import WriterAgent, ReviewerAgent

# get_api_key is now imported from core.config


def call_agent_pipeline(
    logger, 
    product: Dict[str, Any], 
    writer: WriterAgent, 
    reviewer: ReviewerAgent
) -> Optional[Dict[str, Any]]:
    """
    Execute the Writer -> Reviewer pipeline.
    Examples are provided directly in the system prompt (few-shot style).
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
        
        # Prepare data for template
        product_data = {
            "product_name": product_name,
            "category": category,
            "brand": brand,
            "color": color,
            "size": size,
            "packaging": packaging,
            "certifications": certifications,
            "afgift": afgift,
            "supplier_info": supplier_info,
            "product_url": product_url
        }

        # 1. Writer Step
        logger.debug(f"  Writer ({writer.model}) generating draft...")
        draft_json_str = writer.generate(product_data)
        
        if not draft_json_str:
            logger.error("  Writer failed to generate content")
            # Surface agent last usage/cost if available
            try:
                logger.error(f"  Writer last usage: {writer._last_usage}")
                logger.error(f"  Writer last cost: ${writer._last_cost:.6f}")
            except Exception:
                pass
            return None
            
        # 2. Reviewer Step
        logger.debug(f"  Reviewer ({reviewer.model}) validating...")
        final_json_str = reviewer.review(draft_json_str)
        
        if not final_json_str:
            logger.error("  Reviewer failed to validate content")
            return None

        # Parse Final JSON
        ai_data = json.loads(final_json_str)
        
        # Fallback: ensure HTML formatting if model didn't follow instructions
        desc_long = ai_data.get("DESC_LONG", "")
        if "\n" in desc_long and "<br" not in desc_long:
            logger.warning("  DESC_LONG has newlines without HTML breaks, converting...")
            desc_long = desc_long.replace("\n\n", "<br /><br />").replace("\n", "<br />")
            ai_data["DESC_LONG"] = desc_long
        
        logger.debug(f"  ✓ Pipeline completed successfully")
        
        return ai_data
        
    except json.JSONDecodeError as e:
        logger.error(f"  JSON parse error: {e}")
        return None
    except Exception as e:
        logger.error(f"  Pipeline error: {e}")
        return None


def generate_ai_descriptions(logger, config, input_file: Optional[str] = None):
    """
    Read categorized_products.json, enrich with AI descriptions, write final_products.json
    
    Uses Agents SDK which handles Chat Completions and Responses API transparently.
    Examples are provided directly in the system prompt (few-shot style).
    """
    output_dir = config.paths.output_dir
    
    if input_file:
        enriched_path = Path(input_file)
        if not enriched_path.exists() and not enriched_path.is_absolute():
            enriched_path = output_dir / input_file
    else:
        enriched_path = output_dir / "categorized_products.json"
    
    if not enriched_path.exists():
        logger.error(f"Input file not found: {enriched_path}")
        return False
    
    api_key = get_api_key(required=False)
    if not api_key:
        logger.warning("Running in DRY-RUN mode (no API key). Showing mock AI fields.")
        dry_run = True
        writer_agent = None
        reviewer_agent = None
    else:
        dry_run = False
        try:
            # Debug: show which ai_config is in use
            try:
                logger.debug(f"ai_config loaded from: {ai_config_module.__file__}")
            except Exception:
                logger.debug("ai_config module path not available")
            model_config = get_model_config(step="enrichment")
            primary_model = model_config["model"]
            logger.debug(f"Model config (enrichment): {model_config}")
            
            logger.debug(f"Initializing agents: {primary_model} (Writer), {REVIEWER_MODEL} (Reviewer)")
            
            writer_agent = WriterAgent(
                model=primary_model,
                system_prompt_path=Path(WRITER_SYSTEM_PROMPT),
                task_prompt_path=Path(WRITER_TASK_PROMPT)
            )
            
            reviewer_agent = ReviewerAgent(
                model=REVIEWER_MODEL,
                system_prompt_path=Path(REVIEWER_SYSTEM_PROMPT)
            )
        except Exception as e:
            logger.error(f"Failed to initialize agents: {e}")
            return False
    
    model_config = get_model_config(step="enrichment")
    primary_model = model_config["model"]
    
    logger.info(f"AI Enrichment Setup (Modular Agents):")
    logger.info(f"  Writer model: {primary_model}")
    logger.info(f"  Reviewer model: {REVIEWER_MODEL}")
    
    logger.info(f"Loading products: {enriched_path}")
    products = load_json(enriched_path, default=[])
    
    if isinstance(products, dict):
        products = [products]
    
    logger.info(f"Processing {len(products)} products for AI enrichment")
    
    processed_count = 0
    success_count = 0
    error_count = 0
    total_cost = 0.0  # Track total API cost
    cost_by_model = {}  # Track costs per model
    
    for i, product in enumerate(products, 1):
        product_num = product.get("product_number", f"product_{i}")
        logger.info(f"[{i}/{len(products)}] {product_num}")
        
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
            if writer_agent and reviewer_agent:
                ai_data = call_agent_pipeline(
                    logger, 
                    product,
                    writer=writer_agent,
                    reviewer=reviewer_agent
                )
                if not ai_data:
                    logger.warning(f"  Skipping product due to pipeline failure")
                    error_count += 1
                    continue
                
                # Track API costs
                writer_cost = writer_agent.last_cost
                reviewer_cost = reviewer_agent.last_cost
                total_cost += (writer_cost + reviewer_cost)
                
                if writer_agent.model not in cost_by_model:
                    cost_by_model[writer_agent.model] = 0.0
                cost_by_model[writer_agent.model] += writer_cost
                
                if reviewer_agent.model not in cost_by_model:
                    cost_by_model[reviewer_agent.model] = 0.0
                cost_by_model[reviewer_agent.model] += reviewer_cost
            else:
                logger.warning(f"  Agents not available")
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
    atomic_write_json(products, final_path)
    logger.info(f"✓ Final products JSON: {final_path}")
    
    # Save cost information
    cost_summary = {
        "step": "Step 4 (AI Enrichment)",
        "total_cost_usd": round(total_cost, 6),
        "products_processed": success_count,
        "cost_by_model": {model: round(cost, 6) for model, cost in cost_by_model.items()},
        "timestamp": datetime.now().isoformat()
    }
    
    try:
        cost_file = output_dir / "ai_costs.json"
        # If file exists, load it to accumulate costs
        existing_costs = load_json(cost_file, default={})
        if existing_costs:
            # Accumulate total cost
            total_cost_accumulated = existing_costs.get("total_cost_usd", 0.0) + cost_summary["total_cost_usd"]
            cost_summary["total_cost_usd"] = round(total_cost_accumulated, 6)
            # Merge model costs
            existing_by_model = existing_costs.get("cost_by_model", {})
            for model, cost in cost_by_model.items():
                existing_by_model[model] = round(existing_by_model.get(model, 0.0) + cost, 6)
            cost_summary["cost_by_model"] = existing_by_model
        
        save_json(cost_file, cost_summary, atomic=True)
        logger.info(f"✓ Cost summary saved: {cost_file}")
        logger.info(f"  Total cost: ${cost_summary['total_cost_usd']:.6f}")
    except Exception as e:
        logger.warning(f"Could not save cost summary: {e}")
    
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
    log_dir = config.paths.logs_dir
    
    logger = setup_logging(log_dir, "4_generate_ai")
    
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
