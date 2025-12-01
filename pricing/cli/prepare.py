#!/usr/bin/env python3
"""
Prepare offer operations for a list of products without calling the Dandomain API.

Refactored from: scripts/offers_prepare.py
Now uses pricing.offer_service instead of importing from app.py.

Usage:
    python -m pricing.cli.prepare --input data/output/final_products.json --output ops.json --action create --price 80
    python -m pricing.cli.prepare --input products.json --output ops.json --action remove --product E138450,E138451

Arguments:
    --input   Path to JSON file with products
    --output  Path to write operations JSON
    --action  create|remove
    --product Optional product number(s) to prepare; comma-separated
    --price   New offer price (required for create)
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from core import load_json, save_json
from pricing import prepare_offer_operations


def main():
    parser = argparse.ArgumentParser(
        description="Prepare offer operations JSON for batch processing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--input", required=True, help="Path to JSON file with products")
    parser.add_argument("--output", required=True, help="Path to write operations JSON")
    parser.add_argument(
        "--action",
        choices=["create", "remove"],
        required=True,
        help="Action to prepare: create or remove offers",
    )
    parser.add_argument(
        "--product",
        help="Comma-separated product numbers to prepare (optional, default: all)",
    )
    parser.add_argument(
        "--price",
        type=float,
        help="Offer price (required for create action)",
    )
    args = parser.parse_args()

    # Validate arguments
    if args.action == "create" and (args.price is None or args.price <= 0):
        print("ERROR: --price is required for create action and must be > 0")
        return 1

    # Load products
    input_file = Path(args.input)
    if not input_file.exists():
        print(f"ERROR: Input file not found: {input_file}")
        return 1

    products = load_json(input_file, default=[])
    if not products:
        print(f"ERROR: No products found in {input_file}")
        return 1

    print(f"Loaded {len(products)} products from {input_file}")

    # Filter by product numbers if specified
    selected = set()
    if args.product:
        for p in args.product.split(","):
            selected.add(p.strip())
        print(f"Filtering to {len(selected)} selected products")

    # Prepare operations
    ops_list = []
    skipped = 0
    errors = 0

    for product in products:
        number = product.get("PROD_NUM") or product.get("number")
        if not number:
            skipped += 1
            continue

        if selected and number not in selected:
            continue

        ops, ctx, err = prepare_offer_operations(product, args.action, args.price)
        if err:
            print(f"Skipping {number}: {err}")
            errors += 1
            continue

        if not ops:
            print(f"No operations generated for {number}")
            skipped += 1
            continue

        ops_list.append({
            "product": number,
            "action": args.action,
            "operations": ops,
            "context": ctx,
        })

    # Write output
    output_file = Path(args.output)
    if save_json(output_file, ops_list):
        print(f"\n✓ Wrote {len(ops_list)} product operations to {output_file}")
        if skipped:
            print(f"  Skipped: {skipped}")
        if errors:
            print(f"  Errors: {errors}")
        return 0
    else:
        print(f"ERROR: Failed to write to {output_file}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
