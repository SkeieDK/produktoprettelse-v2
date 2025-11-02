# AI Configuration Guide

## Overview

The AI prompt and model configuration is centralized in `scripts/ai_config.py`. This allows you to customize the AI behavior without editing the main script.

## Quick Customization

### 1. Change the AI Model

Edit `scripts/ai_config.py`:

```python
DEFAULT_MODEL = "gpt-4o-mini"        # Current primary model
FALLBACK_MODEL = "gpt-5-mini"             # Backup if primary fails
```

**Available OpenAI models:**
- `gpt-4o-mini` — Fast, cheap, recommended ⭐
- `gpt-5-mini` — Latest mini model with better reasoning
- `gpt-4` — More expensive, better reasoning
- `gpt-3.5-turbo` — Very fast, cheapest

### 2. Adjust Output Quality

```python
DEFAULT_TEMPERATURE = 0.7   # 0.0 = deterministic, 1.0 = creative

MAX_TOKENS = 1000          # Increase for longer descriptions
```

**Temperature guidance:**
- `0.3` → Very consistent, repetitive
- `0.7` → Good balance (current) ✓
- `0.9` → Creative, varied results

### 3. Modify the Prompt

The prompt is split into two parts in `ai_config.py`:

**System Prompt** (`SYSTEM_PROMPT`):
- Sets the AI's role and overall approach
- Controls tone: professional, B2B-focused, etc.

**User Prompt Template** (`USER_PROMPT_TEMPLATE`):
- Defines what fields to generate
- Controls instructions for each field
- Includes sustainability guidelines

**Example: Want longer descriptions?**

Edit `USER_PROMPT_TEMPLATE`:
```python
"DESC_LONG": "Professional 100-400 word description..."
             # Change to: 200-600 word description
```

**Example: Change sustainability guidelines?**

Find the sustainability section and modify:
```python
# Current: Only mention if certified
# New: Mention any eco-friendly material
```

### 4. Handle API Issues

```python
MAX_RETRIES = 3                      # How many times to retry
RETRY_DELAY_SECONDS = 2              # Wait time between retries
RATE_LIMIT_WAIT_SECONDS = 60         # Wait if rate-limited
MAX_REQUESTS_PER_MINUTE = None       # Set to limit requests
```

## Usage in Scripts

The main script `scripts/4_generate_ai.py` imports from `ai_config`:

```python
from ai_config import (
    get_system_prompt,
    get_user_prompt,
    get_model_config,
)

# Get current model and settings
config = get_model_config()
model = config["model"]

# Build a prompt for a product
user_prompt = get_user_prompt(
    product_name="E146220",
    supplier_info="...",
    # ... other fields
)

# Use the prompts with OpenAI API
response = client.chat.completions.create(
    model=model,
    messages=[
        {"role": "system", "content": get_system_prompt()},
        {"role": "user", "content": user_prompt}
    ]
)
```

## Example: A/B Testing Different Prompts

To test a new prompt without changing the main version:

1. Create a copy: `ai_config_experimental.py`
2. Modify the prompts
3. Update `4_generate_ai.py` to import from the experimental version
4. Run and compare results

## Monitoring Costs

With `gpt-4o-mini`:
- ~$0.01-0.02 per product (ballpark)
- 100 products = ~$1-2

To reduce costs:
- Use `gpt-3.5-turbo` instead
- Reduce `MAX_TOKENS`
- Use cheaper model for drafts, `gpt-4` for final review

## API Key

The OpenAI API key is loaded from `.env` file in root directory.

If `4_generate_ai.py` prints "DRY-RUN mode", check:
1. `.env` file exists
2. Contains: `OPENAI_API_KEY=sk-...`
3. Run: `python scripts/4_generate_ai.py` again

## Advanced: Multi-Step Enrichment

If you want to call AI multiple times:

1. Create separate functions in `ai_config.py`:
   ```python
   def get_category_classification_prompt(...): ...
   def get_seo_keywords_prompt(...): ...
   def get_product_description_prompt(...): ...
   ```

2. Update `4_generate_ai.py` to call multiple times
3. Combine results into final JSON

This allows specialized AI agents for different tasks while keeping config centralized.

## File Structure

```
scripts/
├── 4_generate_ai.py       # Main script (unchanged most of the time)
├── ai_config.py           # ⭐ Edit this for customization
└── ai_config_examples.py  # (Optional) Example configs for reference
```

---

**Questions?** Check the docstrings in `ai_config.py` or the comments in the prompts.
