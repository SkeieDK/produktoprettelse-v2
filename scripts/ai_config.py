#!/usr/bin/env python3
"""
AI Configuration Module
Centralized management of AI prompts, models, and parameters.
Easily editable by users and clients without touching the main script.
"""

import os
import json
from typing import Optional
from openai import OpenAI

# ============================================================================
# AGENTS SDK WRAPPER
# ============================================================================

class ProductDescriptionAgent:
    """
    Wrapper for product description generation using Agents SDK.
    
    The Agents SDK automatically handles:
    - Chat Completions API for gpt-4o-mini, gpt-3.5-turbo
    - Responses API for gpt-5-nano, gpt-5-mini (transparently)
    
    This means we can switch models in ai_config.py without code changes.
    """
    
    def __init__(self, model: str = None, temperature: float = 0.7):
        """
        Initialize the agent.
        
        Args:
            model: Model name (e.g., "gpt-4o-mini", "gpt-5-nano")
            temperature: Temperature parameter (0.0-1.0) for creativity
        """
        self.model = model or ENRICHMENT_PRIMARY_MODEL
        self.temperature = temperature
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key)
    
    def generate_descriptions(self, user_prompt: str, system_prompt: str) -> Optional[str]:
        """
        Generate product descriptions using Chat Completions API.
        
        The SDK transparently routes to the right API, but we need to handle
        parameter differences:
        - max_tokens: used by most models
        - max_completion_tokens: required for gpt-5-* models
        - temperature: not supported by gpt-5-* models (always uses default)
        
        Args:
            user_prompt: Formatted user prompt with product details
            system_prompt: System prompt for the model
        
        Returns:
            JSON string with descriptions or None on failure
        """
        try:
            # GPT-5 models have different parameter support
            api_params = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
            }
            
            # GPT-5 models require different parameters
            if self.model.startswith("gpt-5"):
                # GPT-5: no temperature, uses max_completion_tokens (need higher limit)
                api_params["max_completion_tokens"] = 8000
            else:
                # Other models: support temperature and max_tokens
                api_params["temperature"] = self.temperature
                api_params["max_tokens"] = 4000
            
            response = self.client.chat.completions.create(**api_params)
            
            content = response.choices[0].message.content
            if not content:
                return None
            
            return content.strip()
                
        except Exception as e:
            raise RuntimeError(f"Agent failed to generate descriptions: {str(e)}")


# ============================================================================
# MODEL CONFIGURATION - SINGLE SOURCE OF TRUTH
# ============================================================================
# Edit these variables to change models globally.
# Each script should import from here, NOT hardcode models internally.

# ---- STEP 3.5: Categorization (Embeddings) ----
EMBEDDING_MODEL = "text-embedding-3-small"          # For semantic similarity
CATEGORIZATION_FALLBACK_MODEL = "gpt-3.5-turbo"     # Used only if confidence < 70%

# ---- STEP 4: AI Enrichment (Descriptions) ----
# Agents SDK transparently handles both Chat Completions and gpt-5 models
# GPT-5 models have restrictions: no temperature, uses max_completion_tokens
ENRICHMENT_PRIMARY_MODEL = "gpt-5-nano"             # Primary: cheapest (~$0.05/1K input)
ENRICHMENT_FALLBACK_MODEL = "gpt-4o-mini"           # Fallback: proven (~$0.15/1K input)

# ---- LEGACY/DEPRECATED ----
# These are kept for backward compatibility but scripts should use the specific ones above
DEFAULT_MODEL = "gpt-4o-mini"
FALLBACK_MODEL = "gpt-3.5-turbo"

# Temperature: controls creativity (0.0 = deterministic, 1.0 = creative)
# For product descriptions: 0.7 is good (factual yet engaging)
DEFAULT_TEMPERATURE = 0.7

# Max tokens for response
MAX_TOKENS = 1000

# Rate limiting: max requests per minute (None = unlimited)
MAX_REQUESTS_PER_MINUTE = None

# Retry configuration
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 2  # Exponential backoff: 2, 4, 8...
RATE_LIMIT_WAIT_SECONDS = 60


# ============================================================================
# SYSTEM PROMPT
# ============================================================================

SYSTEM_PROMPT = """You are an expert product description writer for a B2B webshop specializing in professional cleaning and maintenance products. Write in fluent Danish (da-DK). Your task is to generate clear, concise, and professional product descriptions using the provided structured attributes (brand, farve, størrelse, forpakning, certificeringer).

Guidelines:
- Appeal to business buyers (not consumers)
- Be SEO-friendly and keyword-optimized
- Keep a professional, informative tone; avoid generic filler
- Use concrete details from inputs (brand, color, size, packaging)
- If a field is missing or unknown, simply omit it (do not mention missing info)
- Ignore internal statuses like "Deaktiveret" and internal codes; never mention them
- Compliance-aware: mention certifications factually if present (e.g., FSC, Svanemærket)

Output requirements:
- Only return valid JSON with 2-space indentation
- Do NOT use markdown or code fences
"""


# ============================================================================
# USER PROMPT TEMPLATE
# ============================================================================

USER_PROMPT_TEMPLATE = """Generate product descriptions in JSON format based on the following information:

Available product details:
- Produktnavn: {product_name}
- Kategori: {category}
- Brand: {brand}
- Farve: {color}
- Størrelse: {size}
- Forpakning: {packaging}
- Certificeringer: {certifications}
- Afgift: {afgift}

Supplier information:
{supplier_info}

Product URL: {product_url}

Generate these 4 fields in valid JSON format (ONLY JSON, no markdown):

{{
  "DESC_SHORT": "A concise 1-sentence (2-5 words) description highlighting main use or key features.",
  "DESC_LONG": "Professional 100-400 word description using NLP best practices. Explain purpose, benefits, applications, and unique selling points. Format with clear paragraphs and list details (e.g., 'Farve: Rød'). **Sustainability guidelines**: Mention certifications (FSC, EU Økologisk, Svanemærket) factually if present. Highlight sustainable materials (bagasse, RPET, PLA, recycled plastic) if applicable. **DO NOT claim sustainability unless explicitly justified by certification or material.** Avoid vague terms like 'bæredygtig' without evidence.",
  "PROD_SEARCHWORD": "5-10 highly relevant keywords (comma-separated) that B2B buyers would search for. Exclude product name. Examples: cleaning brush, professional grade, durable, commercial use.",
  "META_DESCRIPTION": "Concise SEO-optimized meta-description (max 155 characters) summarizing product for search engines. Must end with 'Køb her »'."
}}

Return ONLY the JSON object with proper structure. Include all 4 fields. Do NOT add markdown, introduction, or explanation."""


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_system_prompt() -> str:
    """Get the current system prompt."""
    return SYSTEM_PROMPT


def get_user_prompt(
    product_name: str,
    category: str = "Unknown",
    brand: str = "Unknown",
    color: str = "Unknown",
    size: str = "Unknown",
    packaging: str = "Unknown",
    certifications: str = "Unknown",
    afgift: int = 0,
    supplier_info: str = "",
    product_url: str = ""
) -> str:
    """
    Build a user prompt with product information.
    
    Args:
        product_name: Product identifier (e.g., "E146220")
        category: Product category
        brand: Brand name
        color: Product color
        size: Product size/dimensions
        packaging: Packaging information
        certifications: Certifications (FSC, REACH, etc.)
        afgift: Packaging tax (0 if none)
        supplier_info: Extracted supplier information
        product_url: Link to product page
    
    Returns:
        Formatted user prompt ready for API call
    """
    return USER_PROMPT_TEMPLATE.format(
        product_name=product_name if product_name != "Unknown" else "Ukendt",
        category=category if category != "Unknown" else "Ikke kategori",
        brand=brand if brand != "Unknown" else "Ikke angivet",
        color=color if color != "Unknown" else "Ikke angivet",
        size=size if size != "Unknown" else "Ikke angivet",
        packaging=packaging if packaging != "Unknown" else "Ikke angivet",
    certifications=certifications if certifications not in ("Unknown", None, "") else "",
    afgift=afgift if (isinstance(afgift, (int, float)) and afgift > 0) else "",
        supplier_info=supplier_info if supplier_info else "",
        product_url=product_url if product_url else "Ikke angivet"
    )


def is_gpt5_model(model: str) -> bool:
    """
    Detect if model requires Responses API (GPT-5) vs Chat Completions API.
    
    Args:
        model: Model name (e.g., "gpt-5-nano", "gpt-4o-mini")
    
    Returns:
        True if model requires Responses API (GPT-5 series)
    """
    return model.startswith("gpt-5")


def get_model_config(step: str = None) -> dict:
    """
    Get model and API configuration for a specific step or globally.
    
    Args:
        step: "enrichment" for Step 4, "categorization" for Step 3.5, or None for global
    
    Returns:
        Dictionary with model configuration
    """
    if step == "enrichment":
        # Step 4: AI-Powered Product Enrichment
        model = ENRICHMENT_PRIMARY_MODEL
        fallback_model = ENRICHMENT_FALLBACK_MODEL
    elif step == "categorization":
        # Step 3.5: Categorization (embeddings)
        model = EMBEDDING_MODEL
        fallback_model = CATEGORIZATION_FALLBACK_MODEL
    else:
        # Legacy/default (backward compatibility)
        model = DEFAULT_MODEL
        fallback_model = FALLBACK_MODEL
    
    return {
        "model": model,
        "fallback_model": fallback_model,
        "temperature": DEFAULT_TEMPERATURE,
        "max_tokens": MAX_TOKENS,
        "max_retries": MAX_RETRIES,
        "retry_delay": RETRY_DELAY_SECONDS,
        "rate_limit_wait": RATE_LIMIT_WAIT_SECONDS,
        "max_requests_per_minute": MAX_REQUESTS_PER_MINUTE,
    }


# ============================================================================
# QUICK REFERENCE
# ============================================================================

"""
TO CUSTOMIZE MODELS:

1. For Step 3.5 (Categorization/Embeddings):
   - EMBEDDING_MODEL: Used for semantic similarity (don't change - works well)
   - CATEGORIZATION_FALLBACK_MODEL: Used if confidence < 70%

2. For Step 4 (AI Enrichment/Descriptions):
   - ENRICHMENT_PRIMARY_MODEL: Fast & cheap model to use first
   - ENRICHMENT_FALLBACK_MODEL: Used if primary model quality is too low

3. Other settings:
   - DEFAULT_TEMPERATURE: 0.3 = consistent, 0.7 = balanced, 0.9 = creative
   - MAX_TOKENS: Increase for longer outputs
   - MAX_RETRIES: How many times to retry failed API calls

IMPORTANT: Scripts must call get_model_config("step_name") to get the right models.
Never hardcode models directly in scripts - always import from ai_config.
"""
