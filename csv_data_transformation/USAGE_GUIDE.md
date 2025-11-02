# CSV Sanitering & Scraping Pipeline Integration Guide

## Overview
`sanitering.py` now outputs processed product data as JSON, ready for the supplier scraping pipeline.

## New Methods

### `prepare_for_scraping(vendor_name=None) -> List[Dict]`
Prepares processed DataFrame rows as a list of product dictionaries.

**Returns**: List of products with fields:
- `PROD_NUM`: Generated unique product number
- `product_name`: Original product name
- `vendor_name`: Supplier name
- `vendor_item_id`: Vendor's product ID
- `image_url`: Product image URL (if available)
- `barcode`: Product barcode
- `stock_count`: Stock quantity
- `cost_price`: Cost price

### `output_products(output_path=None, vendor_name=None) -> str`
Exports processed products to a JSON file.

**Parameters**:
- `output_path`: Custom output path. Default: `cache/processed_products.json`
- `vendor_name`: Optional filter by vendor name

**Returns**: Path to the saved JSON file

## Usage Examples

### Basic Usage
```python
import pandas as pd
from sanitering import CSVSanitering

# Load raw data
df = pd.read_csv("raw_products.csv")

# Process data
sanitering = CSVSanitering(df)
df_processed = sanitering.process()

# Export to JSON for scraping
output_file = sanitering.output_products()
print(f"Exported to: {output_file}")
```

### Filter by Vendor
```python
# Only export Duni products
output_file = sanitering.output_products(vendor_name="Duni A/S Tyskland")
```

### Custom Output Path
```python
# Save to custom location
output_file = sanitering.output_products(
    output_path="data/my_products.json",
    vendor_name="Vikan A/S"
)
```

### Command Line Usage
```bash
python sanitering.py path/to/raw_data.csv
```

This will:
1. ✅ Load and transform the CSV
2. ✅ Display transformation summary
3. ✅ Export to `cache/processed_products.json`
4. ✅ Show sample product data

## Output Format

**Example JSON output** (`cache/processed_products.json`):

```json
[
  {
    "PROD_NUM": "E100010 - Deaktiveret",
    "product_name": "Papirprodukter - Servietter",
    "vendor_name": "Duni A/S Tyskland",
    "vendor_item_id": "DUNI-1234",
    "image_url": "https://example.com/image-processed.jpg",
    "barcode": "5706801001234",
    "stock_count": 150,
    "cost_price": 5.25
  },
  {
    "PROD_NUM": "E100020 - Deaktiveret",
    "product_name": "Rengøringsmidler",
    "vendor_name": "Vikan A/S",
    "vendor_item_id": "VIKAN-5678",
    "image_url": null,
    "barcode": "5706801005678",
    "stock_count": 200,
    "cost_price": 12.50
  }
]
```

## Integration with Scraper

The scraper (`product_scraper.py`) will read this JSON output and use it to:
1. Look up the correct vendor module
2. Scrape product information from the vendor website
3. Download product images
4. Extract product data
5. Combine with existing product information

### Example: Loading products in scraper
```python
import json

# Load processed products
with open('cache/processed_products.json', 'r', encoding='utf-8') as f:
    products = json.load(f)

# Process each product
for product in products:
    print(f"Processing: {product['product_name']}")
    print(f"  Vendor: {product['vendor_name']}")
    print(f"  Vendor ID: {product['vendor_item_id']}")
    # ... scraping logic here
```

## Data Flow

```
Raw CSV Data (supplier products)
        ↓
    sanitering.py
   (transformation)
        ↓
process() - transforms data
        ↓
output_products() - exports JSON
        ↓
cache/processed_products.json
        ↓
product_scraper.py
  (scraping pipeline)
```

## DataAreaID-Specific Rules

The sanitization process handles different business logic based on **DataAreaID**, which identifies the data source or sales channel.

### Supported DataAreaIDs

#### **'cc' (Continental Europe)**
- **Barcode Cleaning**: Remove leading 'C' from `PROD_BARCODE_NUMBER`
  - Example: `C5705023742184` → `5705023742184`
- **Unit ID Usage**: Use `SalesUnitID` for all unit-based calculations
  - Affects: Price calculations, conversions, packaging info
- **Price Markup**: No additional markup applied
- **Output Field**: `ACTIVE_UNIT_ID` = SalesUnitID

#### **'mln' (MLN)**
- **Barcode Cleaning**: No changes (keep as-is)
- **Unit ID Usage**: Use `StockUnitID` for all unit-based calculations
  - Affects: Price calculations, conversions, packaging info
- **Price Markup**: Apply **10% markup** to cost prices
  - Applied to: `PROD_COST_PRICE` (before Flerstk. pris and Retail_Price calculation)
  - Cascades to: `Flerstk. pris` and `Retail_Price` automatically
- **Output Field**: `ACTIVE_UNIT_ID` = StockUnitID

### Implementation Details

The `apply_dataarea_rules()` method in `sanitering.py` handles all DataAreaID-specific transformations:

```python
def apply_dataarea_rules(self):
    """Apply all DataAreaID-specific business rules."""
    # Rules by DataAreaID:
    # - 'cc': Remove barcode prefix, use SalesUnitID
    # - 'mln': Apply 10% cost markup, use StockUnitID
```

**Processing Order** (ensures rules work correctly):
1. change_types()
2. replace_value()
3. rename_columns()
4. **apply_dataarea_rules()** ← DataAreaID rules applied HERE
5. add_flerstk_pris() ← Uses ACTIVE_UNIT_ID and cost prices
6. add_besparelse()
7. add_retail_price()
8. add_prod_num()
9. add_img_name()

### Using ACTIVE_UNIT_ID

After sanitization, use the `ACTIVE_UNIT_ID` field for any calculations:

```python
# After sanitization
for product in products:
    unit_id = product["ACTIVE_UNIT_ID"]  # Already set to correct value
    # Use unit_id for conversions, pricing, etc.
```

### Adding New DataAreaIDs

To support a new DataAreaID, add rules to `apply_dataarea_rules()`:

```python
if area_id == "new_area":
    # Add any specific logic here
    if "PROD_COST_PRICE" in row:
        row["PROD_COST_PRICE"] = row["PROD_COST_PRICE"] * 1.05  # Example: 5% markup
    row["ACTIVE_UNIT_ID"] = row.get("SalesUnitID", "")
```

## Fields Mapping

| sanitering.py (after rename) | JSON output | Purpose |
|-----|-----|-----|
| PROD_NUM | PROD_NUM | Unique internal product number |
| ORIGINAL_PROD_NAME | product_name | Product display name |
| ORIGINAL_VENDOR_NUM | vendor_item_id | Vendor's product ID (used for search) |
| PROD_BARCODE_NUMBER | barcode | Product barcode |
| PrimaryVendorName | vendor_name | Supplier name (used for module lookup) |
| ImageURL | image_url | URL to product image |
| STOCK_COUNT | stock_count | Current stock quantity |
| PROD_COST_PRICE | cost_price | Product cost |

## Notes

- Only products with `PROD_NUM` and `product_name` are included
- `image_url` can be `null` for products without images
- The JSON file uses UTF-8 encoding for international characters
- Output is formatted with 2-space indentation for readability

