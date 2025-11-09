"""
Helper functions for product categorization (shared between embedding and LLM approaches)
"""

from typing import Dict, List


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


def get_category_user_prompt(product: Dict, category_tree: str, include_details: bool = True) -> str:
    """
    Build user prompt for categorization.
    
    Args:
        product: Product details
        category_tree: Category hierarchy string
        include_details: If True, include full description/supplier_info
    """
    # Extract product details
    prod_name = product.get('ORIGINAL_PROD_NAME', product.get('PROD_NAME', 'Unknown'))
    vendor = product.get('PrimaryVendorName', 'Unknown')
    
    # Get supplier info if available (can be dict or string)
    supplier_info = product.get('supplier_info', {})
    if isinstance(supplier_info, dict):
        description = supplier_info.get('description', '')
        specifications = supplier_info.get('specifications', '')
    else:
        # If supplier_info is a string, use it as description
        description = str(supplier_info) if supplier_info else ''
        specifications = ''
    
    # Get any existing category hints
    existing_cat = product.get('DefaultCategoryId', '')
    
    prompt = f"""Product to categorize:
- Name: {prod_name}
- Vendor: {vendor}
- Existing Category ID (if any): {existing_cat}
"""
    
    # Include detailed info
    if include_details:
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


def build_category_tree(categories: List[Dict], category_product_map: Dict[str, Dict], compact: bool = False) -> str:
    """
    Build a formatted category tree for the AI prompt with example products.
    
    Args:
        categories: List of category dicts (RAW API format with 'id', 'number', 'texts')
        category_product_map: Map of category_id to products
        compact: If True, only show categories with products (to save tokens)
    """
    # Build simple list (no hovedkategori grouping since RAW API doesn't have that field)
    tree_lines = []
    
    for cat in categories:
        cat_id = str(cat.get('id', ''))
        if not cat_id:
            continue
        
        # Skip categories without products if compact mode
        if compact and cat_id in category_product_map:
            if not category_product_map[cat_id]['example_products']:
                continue
        
        # Extract category name from RAW API format
        cat_name = 'Unknown'
        texts = cat.get('texts', {})
        if isinstance(texts, dict):
            items = texts.get('items', [])
            if items and len(items) > 0:
                cat_name = items[0].get('name', 'Unknown')
        
        # Truncate name if too long
        if len(cat_name) > 60:
            cat_name = cat_name[:57] + "..."
        
        tree_lines.append(f"  - ID: {cat_id} | {cat_name}")
        
        # Add example products if available
        if cat_id in category_product_map:
            examples = category_product_map[cat_id]['example_products']
            if examples:
                # Truncate product names to save tokens
                short_names = [p['name'][:40] for p in examples[:3]]
                tree_lines.append(f"    Ex: {', '.join(short_names)}")
    
    return "\n".join(tree_lines)
