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
from datetime import datetime
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
    EMBEDDING_MODEL,
)
from openai import OpenAI
import numpy as np

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


def call_agent_api(logger, product: Dict[str, Any], agent: ProductDescriptionAgent, system_prompt: str, fallback_agent: Optional[ProductDescriptionAgent] = None, quality_threshold: float = 0.70, example_product: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Call AI agent (Agents SDK handles both Chat Completions and Responses API).
    
    Args:
        example_product: Optional similar product to use as reference example
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
        
        # Add example if provided
        if example_product:
            example_desc_short = example_product.get("DESC_SHORT", "")
            example_desc_long = example_product.get("DESC_LONG", "")
            example_meta = example_product.get("META_DESCRIPTION", "")
            example_name = example_product.get("ORIGINAL_PROD_NAME", "Similar product")
            
            example_text = f"""
Here is a similar high-quality product description for reference (follow this style and format):

Product: {example_name}
DESC_SHORT: {example_desc_short}
DESC_LONG: {example_desc_long}
META_DESCRIPTION: {example_meta}

Use this example as a guide for tone, structure, and formatting. Adapt it to the current product's specific details.
"""
            user_prompt = example_text + "\n\n" + user_prompt
            logger.debug(f"  Using example: {example_name[:50]}...")
        
        logger.debug(f"  Calling agent ({agent.model})...")
        
        # Call agent (Agents SDK handles Chat Completions vs Responses API automatically)
        response_text = agent.generate_descriptions(user_prompt, system_prompt)
        
        if not response_text:
            logger.error(f"  Empty response from agent")
            return None
        
        # Log cost information if available
        cost = agent.get_last_cost()
        usage = agent.get_last_usage()
        if cost:
            logger.debug(f"  API cost: ${cost:.6f} ({usage['input_tokens']} input + {usage['output_tokens']} output tokens)")
        
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
            return call_agent_api(logger, product, fallback_agent, system_prompt, fallback_agent=None, quality_threshold=quality_threshold, example_product=example_product)
        
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


# ============================================================================
# QUALITY SCORING & EXAMPLE SELECTION
# ============================================================================

def calculate_quality_score(product: Dict[str, Any]) -> float:
    """
    Calculate quality score (0-1) for product descriptions.
    
    Scoring criteria (excluding PROD_SEARCHWORD as requested):
    - Completeness: All required fields present (0.3 weight)
    - Optimal lengths: DESC_SHORT, DESC_LONG, META_DESCRIPTION (0.5 weight)
    - No placeholders: Avoid TODO, N/A, empty strings (0.2 weight)
    
    Args:
        product: Product dictionary with AI-generated fields
    
    Returns:
        Quality score between 0.0 and 1.0
    """
    score = 0.0
    
    # Completeness check (0.3 weight)
    required_fields = ['DESC_SHORT', 'DESC_LONG', 'META_DESCRIPTION']
    has_all_fields = all(
        product.get(field) and isinstance(product.get(field), str) and len(product.get(field).strip()) > 0
        for field in required_fields
    )
    if has_all_fields:
        score += 0.3
    
    # Length optimization (0.5 weight total)
    desc_short = product.get('DESC_SHORT', '').strip()
    desc_short_len = len(desc_short)
    if 30 <= desc_short_len <= 100:
        score += 0.15
    elif 20 <= desc_short_len < 30 or 100 < desc_short_len <= 120:
        score += 0.10  # Partial credit for close-enough
    
    desc_long = product.get('DESC_LONG', '').strip()
    desc_long_len = len(desc_long)
    if 200 <= desc_long_len <= 1000:
        score += 0.20
    elif 150 <= desc_long_len < 200 or 1000 < desc_long_len <= 1200:
        score += 0.10  # Partial credit
    
    meta_desc = product.get('META_DESCRIPTION', '').strip()
    meta_desc_len = len(meta_desc)
    if 120 <= meta_desc_len <= 160:
        score += 0.15
    elif 100 <= meta_desc_len < 120 or 160 < meta_desc_len <= 180:
        score += 0.10  # Partial credit
    
    # Content quality - no placeholders (0.2 weight)
    bad_indicators = ['todo', 'n/a', 'xxx', 'unknown', 'test', 'placeholder']
    desc_long_lower = desc_long.lower()
    has_no_placeholders = not any(bad in desc_long_lower for bad in bad_indicators)
    
    # Also check DESC_LONG isn't just empty or too generic
    has_substance = desc_long_len >= 150 and ' ' in desc_long  # Has multiple words
    
    if has_no_placeholders and has_substance:
        score += 0.2
    elif has_no_placeholders or has_substance:
        score += 0.1  # Partial credit
    
    return min(score, 1.0)  # Cap at 1.0


def load_example_cache(cache_dir: Path) -> Dict[str, Any]:
    """Load cached quality scores and embeddings."""
    cache_file = cache_dir / "example_quality_cache.json"
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {"quality_scores": {}, "embeddings": {}}
    return {"quality_scores": {}, "embeddings": {}}


def save_example_cache(cache_dir: Path, cache_data: Dict[str, Any]):
    """Save quality scores and embeddings to cache."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "example_quality_cache.json"
    atomic_write_json(cache_file, cache_data)


def get_embedding(client: OpenAI, text: str, model: str = EMBEDDING_MODEL) -> Optional[list]:
    """Generate embedding for text using OpenAI API."""
    try:
        response = client.embeddings.create(
            input=text,
            model=model
        )
        return response.data[0].embedding
    except Exception as e:
        return None


def cosine_similarity(vec1: list, vec2: list) -> float:
    """Calculate cosine similarity between two vectors."""
    a = np.array(vec1)
    b = np.array(vec2)
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def find_similar_example(
    logger,
    current_product: Dict[str, Any],
    existing_products: list,
    cache_data: Dict[str, Any],
    client: OpenAI,
    min_quality_score: float = 0.7,
    golden_examples: Optional[Dict[str, list]] = None
) -> Optional[Dict[str, Any]]:
    """
    Find the best similar product to use as an example.
    
    Strategy:
    1. Check for golden examples in the current category (from UI)
    2. Filter existing products by quality_score >= min_quality_score
    3. Check for manual approval override (approved_example field)
    4. Prioritize same category_id
    5. Use embedding similarity to find closest match
    
    Args:
        logger: Logger instance
        current_product: Product being enriched
        existing_products: List of already enriched products from final_products.json
        cache_data: Cached quality scores and embeddings
        client: OpenAI client for generating embeddings
        min_quality_score: Minimum quality threshold (default 0.7)
        golden_examples: Dict mapping category_id to list of golden product_numbers
    
    Returns:
        Best matching product dict or None if no good match found
    """
    if not existing_products:
        return None
    
    current_category = current_product.get("ai_categorization", {}).get("category_id")
    current_name = current_product.get("ORIGINAL_PROD_NAME", "")
    current_supplier = current_product.get("supplier_info", "")[:500]  # Truncate for embedding
    
    # Check for golden examples in this category (set from UI)
    if golden_examples and current_category:
        golden_nums = golden_examples.get(str(current_category), [])
        if golden_nums:
            logger.debug(f"  Found {len(golden_nums)} golden examples for category {current_category}")
            # Find first available golden example from this category
            for prod in existing_products:
                if prod.get("product_number", "") in golden_nums:
                    logger.debug(f"  Using golden example: {prod.get('product_number', '')}")
                    return prod
    
    # Build search text for current product
    current_search_text = f"{current_name} {current_supplier}"
    
    # Get or generate embedding for current product
    current_prod_key = current_product.get("product_number", "")
    cached_embedding = cache_data.get("embeddings", {}).get(current_prod_key)
    
    if cached_embedding:
        current_embedding = cached_embedding
    else:
        current_embedding = get_embedding(client, current_search_text)
        if not current_embedding:
            logger.debug("  Failed to generate embedding for current product")
            return None
        cache_data.setdefault("embeddings", {})[current_prod_key] = current_embedding
    
    # Filter candidates by quality score
    quality_scores = cache_data.get("quality_scores", {})
    candidates = []
    
    for prod in existing_products:
        prod_num = prod.get("product_number", "")
        
        # Skip if same product
        if prod_num == current_prod_key:
            continue
        
        # Check manual approval override
        if prod.get("approved_example") is False:
            continue  # Blacklisted
        
        if prod.get("approved_example") is True:
            # Force include manually approved examples
            candidates.append({
                "product": prod,
                "quality_score": 1.0,  # Max score for approved
                "is_approved": True
            })
            continue
        
        # Calculate or retrieve quality score
        if prod_num in quality_scores:
            q_score = quality_scores[prod_num]
        else:
            q_score = calculate_quality_score(prod)
            quality_scores[prod_num] = q_score
        
        # Filter by minimum quality
        if q_score >= min_quality_score:
            candidates.append({
                "product": prod,
                "quality_score": q_score,
                "is_approved": False
            })
    
    if not candidates:
        logger.debug(f"  No quality examples found (min_quality={min_quality_score})")
        return None
    
    logger.debug(f"  Found {len(candidates)} quality candidates (score >= {min_quality_score})")
    
    # Prioritize same category
    same_category_candidates = [
        c for c in candidates
        if c["product"].get("ai_categorization", {}).get("category_id") == current_category
    ]
    
    if same_category_candidates:
        logger.debug(f"  {len(same_category_candidates)} candidates in same category ({current_category})")
        search_pool = same_category_candidates
    else:
        logger.debug(f"  No same-category candidates, using all {len(candidates)} quality products")
        search_pool = candidates
    
    # Calculate similarity scores using embeddings
    similarities = []
    for candidate in search_pool:
        prod = candidate["product"]
        prod_num = prod.get("product_number", "")
        
        # Get or generate embedding
        cached_emb = cache_data.get("embeddings", {}).get(prod_num)
        if cached_emb:
            prod_embedding = cached_emb
        else:
            prod_name = prod.get("ORIGINAL_PROD_NAME", "")
            prod_supplier = prod.get("supplier_info", "")[:500]
            prod_search_text = f"{prod_name} {prod_supplier}"
            
            prod_embedding = get_embedding(client, prod_search_text)
            if not prod_embedding:
                continue
            cache_data.setdefault("embeddings", {})[prod_num] = prod_embedding
        
        # Calculate cosine similarity
        sim_score = cosine_similarity(current_embedding, prod_embedding)
        
        similarities.append({
            "product": prod,
            "similarity": sim_score,
            "quality_score": candidate["quality_score"],
            "is_approved": candidate["is_approved"]
        })
    
    if not similarities:
        logger.debug("  No valid similarity scores calculated")
        return None
    
    # Sort by: manual approval first, then quality * similarity
    similarities.sort(
        key=lambda x: (
            x["is_approved"],  # Approved examples first
            x["quality_score"] * x["similarity"]  # Then by combined score
        ),
        reverse=True
    )
    
    best_match = similarities[0]
    logger.debug(f"  Best match: similarity={best_match['similarity']:.3f}, quality={best_match['quality_score']:.2f}")
    
    return best_match["product"]


def generate_ai_descriptions(logger, config, input_file: Optional[str] = None):
    """
    Read categorized_products.json, enrich with AI descriptions, write final_products.json
    
    Uses Agents SDK which handles Chat Completions and Responses API transparently.
    Includes quality-aware example selection from existing products.
    """
    output_dir = Path(config["paths"]["output"])
    cache_dir = Path(config["paths"]["cache"])
    
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
        openai_client = None
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
            
            # Initialize OpenAI client for embeddings
            openai_client = OpenAI(api_key=api_key)
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
    
    # Load existing products for examples
    final_products_path = output_dir / "final_products.json"
    existing_products = []
    if final_products_path.exists():
        try:
            with open(final_products_path, 'r', encoding='utf-8') as f:
                existing_products = json.load(f)
                if isinstance(existing_products, dict):
                    existing_products = [existing_products]
            logger.info(f"  Loaded {len(existing_products)} existing products for examples")
        except Exception as e:
            logger.warning(f"  Could not load existing products: {e}")
            existing_products = []
    else:
        logger.info(f"  No existing products found (first run)")
    
    # Load quality/embedding cache
    cache_data = load_example_cache(cache_dir)
    logger.info(f"  Loaded cache: {len(cache_data.get('quality_scores', {}))} quality scores, {len(cache_data.get('embeddings', {}))} embeddings")
    
    # Load golden examples from UI (if available)
    golden_examples_path = cache_dir / "golden_examples.json"
    golden_examples = {}
    if golden_examples_path.exists():
        try:
            with open(golden_examples_path, 'r', encoding='utf-8') as f:
                golden_examples = json.load(f)
            logger.info(f"  Loaded golden examples: {sum(len(v) for v in golden_examples.values())} examples across {len(golden_examples)} categories")
        except Exception as e:
            logger.warning(f"  Could not load golden examples: {e}")
            golden_examples = {}
    else:
        logger.debug(f"  No golden examples configured yet")
    
    logger.info(f"Loading products: {enriched_path}")
    with open(enriched_path, 'r', encoding='utf-8') as f:
        products = json.load(f)
    
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
        
        # Find similar example (if we have existing products)
        example_product = None
        if existing_products and openai_client:
            try:
                example_product = find_similar_example(
                    logger=logger,
                    current_product=product,
                    existing_products=existing_products,
                    cache_data=cache_data,
                    client=openai_client,
                    min_quality_score=0.7,
                    golden_examples=golden_examples
                )
                if example_product:
                    example_name = example_product.get("ORIGINAL_PROD_NAME", "Unknown")[:40]
                    logger.info(f"  Found example: {example_name}...")
                else:
                    logger.debug(f"  No suitable example found")
            except Exception as e:
                logger.warning(f"  Example search failed: {e}")
                example_product = None
        
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
                    quality_threshold=quality_threshold,
                    example_product=example_product
                )
                if not ai_data:
                    logger.warning(f"  Skipping product due to agent failure")
                    error_count += 1
                    continue
                
                # Track API costs
                agent_cost = agent.get_last_cost()
                agent_model = agent.model
                total_cost += agent_cost
                
                if agent_model not in cost_by_model:
                    cost_by_model[agent_model] = 0.0
                cost_by_model[agent_model] += agent_cost
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
    
    # Save updated cache
    if not dry_run and openai_client:
        save_example_cache(cache_dir, cache_data)
        logger.info(f"✓ Saved cache: {len(cache_data.get('quality_scores', {}))} quality scores, {len(cache_data.get('embeddings', {}))} embeddings")
    
    # Write final output
    final_path = output_dir / "final_products.json"
    atomic_write_json(final_path, products)
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
        if cost_file.exists():
            with open(cost_file, 'r', encoding='utf-8') as f:
                existing_costs = json.load(f)
            # Accumulate total cost
            total_cost_accumulated = existing_costs.get("total_cost_usd", 0.0) + cost_summary["total_cost_usd"]
            cost_summary["total_cost_usd"] = round(total_cost_accumulated, 6)
            # Merge model costs
            existing_by_model = existing_costs.get("cost_by_model", {})
            for model, cost in cost_by_model.items():
                existing_by_model[model] = round(existing_by_model.get(model, 0.0) + cost, 6)
            cost_summary["cost_by_model"] = existing_by_model
        
        with open(cost_file, 'w', encoding='utf-8') as f:
            json.dump(cost_summary, f, ensure_ascii=False, indent=2)
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
