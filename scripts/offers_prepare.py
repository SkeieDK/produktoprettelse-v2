"""
Prepare offer operations for a list of products without calling the Dandomain API.

Usage:
  python scripts/offers_prepare.py --input data/output/final_products.json --output ops.json --action create --product E138450 --price 80

Arguments:
  --input   Path to JSON file with products
  --output  Path to write operations JSON
  --action  create|remove
  --product Optional product number(s) to prepare; comma-separated
  --price   New offer price (required for create)
"""
from pathlib import Path
import argparse
import json
import importlib.util

def load_ui_module():
    module_path = Path(__file__).resolve().parent.parent / "app" / "app.py"
    spec = importlib.util.spec_from_file_location("ui_module", str(module_path))
    ui_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ui_module)
    return ui_module

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--action", choices=["create","remove"], required=True)
    parser.add_argument("--product", help="Comma-separated product numbers to prepare")
    parser.add_argument("--price", type=float, help="Offer price (for create)")
    args = parser.parse_args()

    ui = load_ui_module()

    # Load products
    input_file = Path(args.input)
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    with open(input_file, 'r', encoding='utf-8') as f:
        products = json.load(f)

    selected = set()
    if args.product:
        for p in args.product.split(','):
            selected.add(p.strip())

    ops_list = []
    for product in products:
        number = product.get('PROD_NUM') or product.get('number')
        if selected and number not in selected:
            continue
        ops, ctx, err = ui.prepare_offer_operations(product, args.action, args.price)
        if err:
            print(f"Skipping {number}: {err}")
            continue
        if not ops:
            print(f"No operations generated for {number}")
            continue
        ops_list.append({"product": number, "action": args.action, "operations": ops, "context": ctx})

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(ops_list, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(ops_list)} product operations to {args.output}")

if __name__ == '__main__':
    main()
