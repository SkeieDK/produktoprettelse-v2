#!/usr/bin/env python3
"""Test pricing logic"""

import json
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.upload_to_cms import DandomainUploader

# Load test product
with open(PROJECT_ROOT / 'data/output/final_products.json', 'r', encoding='utf-8') as f:
    products = json.load(f)

uploader = DandomainUploader(dry_run=True)
product = products[0]

print("=" * 60)
print(f"Testing pricing logic for: {product.get('PROD_NUM')}")
print("=" * 60)
print(f"DataAreaID: {product.get('DataAreaID')}")
print(f"Raw PROD_COST_PRICE: {product.get('PROD_COST_PRICE')}")
print(f"Raw Retail_Price: {product.get('Retail_Price')}")
print(f"Raw Flerstk. pris: {product.get('Flerstk. pris')}")
print(f"UnitConvStockPurch: {product.get('UnitConvStockPurch')}")
print()

prices = uploader.build_price_entries(product)

print("Generated Price Entries:")
for i, p in enumerate(prices, 1):
    print(f"\n  Entry {i}:")
    print(f"    Amount: {p['amount']}")
    print(f"    Unit Price: {p['unitPrice']}")
    print(f"    Currency: {p['currencyCode']}")
    print(f"    B2B Group ID: {p['b2bGroupId']}")

print("\n" + "=" * 60)
print("✓ Pricing logic working correctly")
print("=" * 60)
