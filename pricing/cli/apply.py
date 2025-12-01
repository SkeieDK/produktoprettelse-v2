#!/usr/bin/env python3
"""
Apply operations produced by `pricing.cli.prepare` against Dandomain API.

Refactored from: scripts/offers_apply.py
Now uses core utilities and proper imports.

Usage:
    python -m pricing.cli.apply --ops ops.json
    python -m pricing.cli.apply --ops ops.json --dry-run
    python -m pricing.cli.apply --ops ops.json --yes  # Skip confirmation

Arguments:
    --ops      Path to operations JSON produced by prepare
    --dry-run  Print operations without executing
    --yes      Skip confirmation prompt
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from core import load_json, save_json


def main():
    parser = argparse.ArgumentParser(
        description="Apply offer operations from JSON file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--ops",
        required=True,
        help="Operations JSON produced by pricing.cli.prepare",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print operations without executing",
    )
    parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip confirmation prompt",
    )
    args = parser.parse_args()

    # Load operations
    ops_file = Path(args.ops)
    if not ops_file.exists():
        print(f"ERROR: Operations file not found: {ops_file}")
        return 1

    payloads = load_json(ops_file, default=[])
    if not payloads:
        print(f"ERROR: No operations found in {ops_file}")
        return 1

    print(f"Loaded {len(payloads)} product operations from {ops_file}")

    # Dry run mode
    if args.dry_run:
        print("\n=== DRY RUN MODE ===")
        import json
        for item in payloads:
            print(f"\nProduct: {item.get('product')}")
            print(f"Action: {item.get('action')}")
            print(f"Operations: {len(item.get('operations', []))}")
            print(json.dumps(item, indent=2, ensure_ascii=False))
        print("\n=== END DRY RUN ===")
        return 0

    # Confirmation
    if not args.yes:
        print(f"\nAbout to apply {len(payloads)} operations.")
        confirm = input("Continue? [y/N]: ").strip().lower()
        if confirm != "y":
            print("Aborted.")
            return 0

    # Initialize API
    try:
        from api_manager import get_api_manager
        api = get_api_manager()
    except Exception as e:
        print(f"ERROR: Failed to initialize API manager: {e}")
        print("Set DANDOMAIN_API_KEY environment variable.")
        return 1

    # Execute operations
    results = []
    success_count = 0
    fail_count = 0

    for item in payloads:
        prod = item.get("product")
        action = item.get("action")
        operations = item.get("operations", [])
        ctx = item.get("context", {})

        print(f"Applying {action} for {prod} ({len(operations)} operations)...", end=" ")

        # Apply price updates
        if not api.update_product_prices(prod, operations):
            results.append({"product": prod, "status": "failed_prices"})
            print("FAILED (prices)")
            fail_count += 1
            continue

        # Update customField3 if present
        language_id = 26
        cf3 = ctx.get("custom_field3")
        if cf3 is not None:
            api.update_product_custom_field3(prod, language_id, cf3)

        # Update categories if present
        if "categories" in ctx:
            api.update_product_categories(prod, ctx["categories"])

        results.append({"product": prod, "status": "applied"})
        print("OK")
        success_count += 1

    # Write results
    out_file = ops_file.with_name(ops_file.stem + "_result.json")
    save_json(out_file, results)

    print(f"\n=== SUMMARY ===")
    print(f"Success: {success_count}")
    print(f"Failed: {fail_count}")
    print(f"Results written to: {out_file}")

    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
