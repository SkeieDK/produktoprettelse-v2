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

