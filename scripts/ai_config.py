#!/usr/bin/env python3
"""
AI Configuration Module
Centralized management of AI prompts, models, and parameters.
Easily editable by users and clients without touching the main script.
"""

# ============================================================================
# MODEL CONFIGURATION
# ============================================================================

# Default model for product descriptions
DEFAULT_MODEL = "gpt-4o-mini"

# Fallback model if primary fails (optional)
FALLBACK_MODEL = "gpt-5-mini"

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

SYSTEM_PROMPT = """You are an expert product description writer for a B2B webshop specializing in professional cleaning and maintenance products. Your task is to generate clear, concise, and professional product descriptions in Danish using natural language processing best practices. Create descriptions that are:
- Appeal to business buyers (not consumers)
- SEO-friendly and keyword-optimized
- Professional yet engaging in tone
- Factually accurate based on provided information
- Compliance-aware (certifications, regulations)

Always generate ONLY valid JSON output with 2-space indentation. Do NOT use markdown syntax or code blocks."""


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
        certifications=certifications if certifications != "Unknown" else "Ingen",
        afgift=afgift if afgift > 0 else "Ingen",
        supplier_info=supplier_info if supplier_info else "Ingen leverandørinformation tilgængelig",
        product_url=product_url if product_url else "Ikke angivet"
    )


def get_model_config() -> dict:
    """Get current model and API configuration."""
    return {
        "model": DEFAULT_MODEL,
        "fallback_model": FALLBACK_MODEL,
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
TO CUSTOMIZE:

1. Change the AI model:
   - Modify DEFAULT_MODEL (e.g., "gpt-4", "gpt-3.5-turbo")
   - Update FALLBACK_MODEL if using a backup strategy

2. Adjust description style:
   - Edit USER_PROMPT_TEMPLATE to change what we ask the AI
   - Modify SYSTEM_PROMPT for overall tone/approach

3. Control output quality:
   - DEFAULT_TEMPERATURE: Lower (0.3) = more consistent, Higher (0.9) = more creative
   - MAX_TOKENS: Increase for longer descriptions, decrease for shorter
   
4. Handle API issues:
   - MAX_RETRIES: How many times to retry failed API calls
   - RETRY_DELAY_SECONDS: Wait time between retries
   - MAX_REQUESTS_PER_MINUTE: Set a rate limit if needed

5. In production:
   - Import this module in 4_generate_ai.py
   - Call get_user_prompt() to build prompts
   - Call get_model_config() to get current settings
"""
