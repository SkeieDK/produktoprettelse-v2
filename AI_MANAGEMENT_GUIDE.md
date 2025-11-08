# AI Management UI - User Guide

## Overview

The **AI Management** tab in the Streamlit UI provides complete control over the AI enrichment system. You can edit prompts, curate golden examples, and review/improve AI-generated descriptions.

## Features

### 1. ✏️ Prompt Editor

**Purpose:** Edit the prompts that guide AI behavior in Step 4 (AI Enrichment)

**What you can edit:**
- **System Prompt**: Defines the AI's role and expertise (e.g., "You are an expert product description writer...")
- **User Prompt Template**: The template used to generate descriptions (contains placeholders like `{product_info}` and `{example_json}`)

**How to use:**
1. Navigate to **AI Management** → **Prompt Editor**
2. Edit the text in the text areas
3. Click **💾 Gem Prompts** to save changes to `scripts/ai_config.py`
4. Changes take effect on next Step 4 run

**Tips:**
- Keep the JSON format requirements in the user prompt
- Don't remove placeholder variables like `{product_info}`
- Test changes on a small batch first

---

### 2. ⭐ Golden Examples Manager

**Purpose:** Select the best product descriptions to use as examples for each category

**How golden examples work:**
- When generating descriptions, Step 4 searches for similar products to use as examples
- Golden examples are **always prioritized** over automatic similarity search
- Multiple golden examples per category are supported

**How to use:**
1. Navigate to **AI Management** → **Golden Examples**
2. Select a category from the dropdown
3. Review products in that category (quality scores shown)
4. Check the boxes for products you want to mark as golden
5. Click **💾 Gem Golden Examples**

**Storage:**
- Golden examples saved to: `data/cache/golden_examples.json`
- Format: `{"category_id": ["product_num1", "product_num2"]}`
- Products also get `approved_example: true` flag in `final_products.json`

**Example workflow:**
```
Category: 5539 - Børster/Skrubber
  ☑ Premium Cleaning Brush (E146223) - Quality: 1.0 ⭐ Golden
  ☐ Standard Brush (E146233) - Quality: 0.85
  ☑ Professional Scrubber (E146243) - Quality: 0.9 ⭐ Golden
```

---

### 3. 📝 Review AI Outputs

**Purpose:** Review, approve, reject, or regenerate AI-generated descriptions

**Features:**

#### Quality Filtering
- **Quality Score**: 0-1 score based on:
  - Completeness (30%): All fields present
  - Optimal lengths (50%): DESC_SHORT 30-100 chars, DESC_LONG 200-1000, META 120-160
  - No placeholders (20%): No TODO, N/A, test, etc.
- **Filter by quality**: Show only products above certain quality threshold
- **Filter by approval status**: Godkendt, Afvist, Ikke godkendt

#### Product Review Cards
Each product shows:
- Title and product number
- Quality score
- Approval status (✅ Godkendt / ❌ Afvist / ⏸️ Ikke vurderet)
- Tabs for:
  - 📄 **Kort Beskrivelse** (DESC_SHORT)
  - 📖 **Lang Beskrivelse** (DESC_LONG)
  - 🔍 **Søgeord** (PROD_SEARCHWORD)
  - 🎯 **Meta** (META_DESCRIPTION)

#### Actions

**✅ Godkend:**
- Marks product as high-quality
- Sets `approved_example: true` in final_products.json
- Product can be used as example for other products

**❌ Afvis:**
- Marks product as low-quality
- Sets `approved_example: false`
- Product will **not** be used as example

**🔄 Regenerer:**
- Opens feedback interface
- Add instructions like:
  - "Gør det mere teknisk"
  - "Tilføj mere om bæredygtighed"
  - "Forkorte beskrivelsen"
  - "Fokuser på B2B anvendelser"
- Regenerates description with feedback
- Keeps same example product

---

## Integration with Pipeline

### Example Selection Priority (Step 4)

When generating descriptions, Step 4 searches for examples in this order:

1. **Golden Examples** (from UI) → Highest priority
   - Checks `data/cache/golden_examples.json` for current category
   - Uses first available golden example
   
2. **Manual Approval** (from UI)
   - Products with `approved_example: true` flag
   - Weighted higher than automatic selection
   
3. **Quality Filter**
   - Only products with quality_score ≥ 0.7
   
4. **Category Match**
   - Prioritizes same category_id
   
5. **Embedding Similarity**
   - Uses cosine similarity of product name + supplier info
   - Ranks by `quality_score * similarity`

### Workflow Example

```
Current product: Cleaning Brush (Category: 5539)

Step 1: Check golden examples
  → Found: E146223 (marked golden in UI) ✓ USE THIS

Step 2: (Skipped - golden found)
Step 3: (Skipped - golden found)
Step 4: (Skipped - golden found)
Step 5: (Skipped - golden found)

Result: Using E146223 as example
```

---

## Best Practices

### Setting Up Golden Examples

1. **Run Step 4 first** on all products (generates baseline descriptions)
2. **Review quality scores** in the Review tab
3. **Identify best products per category** (quality ≥ 0.8)
4. **Mark 1-3 golden examples per category**
5. **Re-run Step 4** on new products (will use golden examples)

### Improving Prompts

1. **Test changes incrementally**
   - Edit one prompt at a time
   - Run on 5-10 products
   - Review results
   
2. **Use specific instructions**
   - ❌ "Make it better"
   - ✅ "Include sustainability certifications prominently"
   
3. **Keep JSON format**
   - Don't remove required fields
   - Don't change placeholder syntax

### Regenerating with Feedback

**Good feedback examples:**
- ✅ "Emphasize B2B use cases instead of consumer use"
- ✅ "Add technical specifications like material composition"
- ✅ "Reduce DESC_LONG to 150 words maximum"
- ✅ "Focus on hygiene and food safety aspects"

**Poor feedback examples:**
- ❌ "Better" (too vague)
- ❌ "Fix it" (no direction)
- ❌ "Like the example" (AI already uses examples)

---

## Files Modified

### UI Files
- `app/app.py`: Added 5th tab "🤖 AI Management" with 3 sub-tabs

### Backend Files
- `scripts/4_generate_ai.py`: Updated to support golden examples
- `scripts/regenerate_product.py`: New script for single product regeneration
- `scripts/ai_config.py`: Contains editable prompts

### Data Files
- `data/cache/golden_examples.json`: Golden examples per category
- `data/cache/example_quality_cache.json`: Quality scores and embeddings
- `data/output/final_products.json`: Products with `approved_example` flag

---

## Command Line Usage

### Regenerate Single Product
```bash
# Basic regeneration
python scripts/regenerate_product.py "E146223 - Deaktiveret"

# With feedback
python scripts/regenerate_product.py "E146223 - Deaktiveret" --feedback "Make it more technical and include material specifications"
```

### Run Step 4 with Golden Examples
```bash
# Normal run (automatically uses golden examples if available)
python scripts/4_generate_ai.py

# With custom input
python scripts/4_generate_ai.py data/output/categorized_products.json
```

---

## Quality Scoring Details

### Formula

```python
quality_score = (
    completeness_score * 0.30 +
    optimal_length_score * 0.50 +
    no_placeholders_score * 0.20
)
```

### Scoring Components

**Completeness (30%):**
- DESC_SHORT present and non-empty
- DESC_LONG present and non-empty
- META_DESCRIPTION present and non-empty
- Score: 1.0 if all present, proportional if partial

**Optimal Lengths (50%):**
- DESC_SHORT: 30-100 characters (optimal)
- DESC_LONG: 200-1000 characters (optimal)
- META_DESCRIPTION: 120-160 characters (optimal)
- Score: 1.0 if all optimal, proportional based on deviation

**No Placeholders (20%):**
- Excludes: TODO, N/A, test, placeholder, unknown, coming soon
- Case-insensitive check across all description fields
- Score: 1.0 if no placeholders, 0.0 if found

### Example Scores

```
Product A:
  DESC_SHORT: "Premium brush" (13 chars) → ✓
  DESC_LONG: "This is a professional..." (450 chars) → ✓
  META: "Buy premium brushes..." (142 chars) → ✓
  No placeholders → ✓
  Quality: 1.0

Product B:
  DESC_SHORT: "TODO" (4 chars) → ✗ too short + placeholder
  DESC_LONG: "N/A" (3 chars) → ✗ too short + placeholder
  META: Missing → ✗
  Quality: 0.2
```

---

## Troubleshooting

### "No golden examples configured yet"
- **Cause**: `golden_examples.json` doesn't exist
- **Solution**: Use Golden Examples Manager to create it

### "Product not found" during regeneration
- **Cause**: Product number doesn't match exactly
- **Solution**: Check product number format (e.g., "E146223 - Deaktiveret" not "E146223")

### Prompts not saving
- **Cause**: File permissions or regex parsing error
- **Solution**: Check `scripts/ai_config.py` has write permissions, verify triple-quote syntax

### Quality scores not updating
- **Cause**: Cache not invalidated
- **Solution**: Delete `data/cache/example_quality_cache.json` and re-run Step 4

---

## Future Enhancements

Potential additions (not yet implemented):
- [ ] Bulk regeneration (regenerate all products in category)
- [ ] A/B testing (compare two prompt versions)
- [ ] Quality score history tracking
- [ ] Export golden examples to share across environments
- [ ] Prompt version control (save/load prompt presets)

---

**Last Updated:** 2025-01-XX  
**Version:** 1.0  
**Compatible with:** Produktoprettelse-v2 pipeline
