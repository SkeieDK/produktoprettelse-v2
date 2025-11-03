# AI-Powered Category Assignment

## Overview

Step 3.5 automatically assigns products to the most appropriate Dandomain categories using AI analysis of product details and the existing category hierarchy.

## How It Works

1. **Loads product data** from `data/output/enriched_products.json` (after image processing)
2. **Fetches category hierarchy** from Dandomain API via `api_manager.py`
3. **Fetches existing products** from Dandomain API to provide category examples
4. **Maps products to categories** - Shows up to 3 example products per category
5. **AI analysis** for each product:
   - Analyzes product name, vendor, description, specifications
   - Compares against full category tree with hierarchy AND example products
   - Identifies categories with similar existing products
   - Assigns best-fit category OR suggests creating new one
   - Provides confidence score (0-100%) and reasoning
6. **Saves results** to `data/output/categorized_products.json`

## Usage

### Run categorization

```bash
# Standalone
python scripts/3.5_categorize.py

# As part of full pipeline
python scripts/run_all.py --stop-after 3.5
```

### Review results

```bash
# Full summary with statistics
python scripts/review_categories.py

# Review low confidence assignments
python scripts/review_categories.py --low-confidence

# Review new category suggestions
python scripts/review_categories.py --new-categories

# Export detailed report
python scripts/review_categories.py --export report.json
```

## Configuration

In `config.yaml`:

```yaml
ai:
  model: "gpt-4o-mini"          # AI model to use
  temperature: 0.3               # Lower = more consistent (0.0-1.0)

categorization:
  confidence_threshold: 70       # Minimum confidence to consider "good"
  batch_size: 10                # Products per batch (future use)
```

## Output Format

Each product gets an `ai_categorization` field:

```json
{
  "PROD_NAME": "Vikan Børste 40cm",
  "PrimaryVendorName": "Vikan A/S",
  "ai_categorization": {
    "category_id": "1234",
    "confidence": 85,
    "reasoning": "Professional cleaning brush from Vikan fits in Cleaning Tools > Brushes"
  }
}
```

Or for new category suggestion:

```json
{
  "ai_categorization": {
    "category_id": null,
    "confidence": 45,
    "reasoning": "No existing category for disposable microfiber products",
    "suggest_new": true,
    "new_category": {
      "name": "Engangs Mikrofiberprodukter",
      "parent_id": "789",
      "description": "Separate category needed for disposable microfiber cleaning products"
    }
  }
}
```

## Confidence Scores

- **90-100%**: Excellent fit, high certainty
- **70-89%**: Good fit, recommended threshold
- **50-69%**: Uncertain, review recommended
- **<50%**: Poor fit, likely needs new category

## Review Workflow

1. **Run categorization**: `python scripts/3.5_categorize.py`
2. **Check summary**: `python scripts/review_categories.py`
3. **Review low confidence**: `python scripts/review_categories.py --low-confidence`
4. **Review new categories**: `python scripts/review_categories.py --new-categories`
5. **Manually adjust** if needed (edit `categorized_products.json`)
6. **Continue pipeline**: `python scripts/4_generate_ai.py`

## Integration with Dandomain API

The script uses `api_manager.py` to:
- **Fetch all categories** with hierarchy (cached for 24 hours)
  - Get category paths (hovedkategori > overkategori > nederste_kategori)
  - Filter categories by B2B group and parent rules
- **Fetch all existing products** (cached for 24 hours)
  - Extract product names and categories
  - Map products to their categories
  - Provide 3 example products per category to the AI

Cache locations:
- `cache/categories_cache.json` - Category hierarchy
- `cache/products_cache.json` - Existing products

To refresh cache:
```python
from api_manager import refresh_categories, refresh_products
categories = refresh_categories()
products = refresh_products()
```

**Why this helps:**
- AI can see "Vikan børster" are in category X, so similar brushes go there
- Prevents creating duplicate categories for similar products
- Learns from existing categorization patterns
- More accurate assignments with real-world examples

## Tips for Best Results

1. **Run after scraping**: Needs product descriptions from Step 2
2. **Review suggestions**: AI may suggest valid new categories
3. **Adjust temperature**: Lower (0.2) for consistency, higher (0.5) for creativity
4. **Vendor patterns**: AI learns vendor-to-category patterns (e.g., Vikan → Cleaning Tools)
5. **Manual overrides**: Edit `categorized_products.json` before Step 4

## Common Issues

**"No API key found"**
- Set `OPENAI_API_KEY` in `.env` file
- Or set in `config.yaml` under `ai.api_key`

**"Input file not found"**
- Run Step 3 first: `python scripts/3_process_images.py`

**"Failed to load categories"**
- Check `API_KEY` in `.env` for Dandomain API
- Verify `api_manager.py` configuration

**All low confidence**
- Product descriptions may be too generic
- Consider running Step 2 with more scraping
- Lower confidence threshold in config

## Files

- `scripts/3.5_categorize.py` - Main categorization script
- `scripts/review_categories.py` - Review and analysis tool
- `api_manager.py` - Category data fetching
- `cache/categories_cache.json` - Cached category hierarchy
- `data/output/categorized_products.json` - Results
- `logs/3.5_categorize.log` - Detailed logs
