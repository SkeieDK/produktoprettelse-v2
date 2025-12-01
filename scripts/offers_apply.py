"""
Apply operations produced by `offers_prepare.py` against Dandomain API.

Usage:
  python scripts/offers_apply.py --ops ops.json --dry-run
"""
from pathlib import Path
import argparse
import json
from api_manager import get_api_manager

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ops', required=True, help='Operations JSON produced by offers_prepare.py')
    parser.add_argument('--dry-run', action='store_true', help='Do not call API')
    args = parser.parse_args()

    ops_file = Path(args.ops)
    if not ops_file.exists():
        raise FileNotFoundError(f"Operations file not found: {ops_file}")

    with open(ops_file, 'r', encoding='utf-8') as f:
        payloads = json.load(f)

    api = None
    if not args.dry_run:
        # Only create the API client if we're actually applying operations
        try:
            api = get_api_manager()
        except Exception as e:
            print(f"Failed to initialize API manager: {e}")
            print("If you intended to run a dry-run, use --dry-run. Otherwise, set DANDOMAIN_API_KEY env var.")
            raise

    results = []
    for item in payloads:
        prod = item.get('product')
        action = item.get('action')
        operations = item.get('operations', [])
        ctx = item.get('context', {})
        print(f"Applying {action} for {prod} (ops: {len(operations)})")
        if args.dry_run:
            print(json.dumps(item, indent=2, ensure_ascii=False))
            results.append({'product': prod, 'status': 'dry-run'})
            continue

        success = api.update_product_prices(prod, operations)
        if not success:
            results.append({'product': prod, 'status': 'failed_prices'})
            print(f"Failed to apply prices for {prod}")
            continue

        # Update customField3 if present in ctx
        language_id = 26
        cf3 = ctx.get('custom_field3')
        if cf3 is not None:
            api.update_product_custom_field3(prod, language_id, cf3)

        # Update categories if present
        if 'categories' in ctx:
            api.update_product_categories(prod, ctx['categories'])

        results.append({'product': prod, 'status': 'applied'})

    out_file = ops_file.with_name(ops_file.stem + '_result.json')
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Results written to: {out_file}")

if __name__ == '__main__':
    main()
