#!/usr/bin/env python3
"""
Review Categorization Results
Interactive review tool for AI-generated category assignments.

Usage:
  python scripts/review_categories.py                    # Review all
  python scripts/review_categories.py --low-confidence   # Only low confidence
  python scripts/review_categories.py --new-categories   # Only new category suggestions
  python scripts/review_categories.py --export report.json  # Export to file
"""

import json
import sys
import argparse
from pathlib import Path
from typing import List, Dict
from collections import Counter

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_OUTPUT = PROJECT_ROOT / "data" / "output"


def load_categorized_products() -> List[Dict]:
    """Load categorized products from JSON."""
    input_file = DATA_OUTPUT / "categorized_products.json"
    
    if not input_file.exists():
        print(f"❌ Error: {input_file} not found!")
        print("   Run Step 3.5 (3.5_categorize.py) first")
        sys.exit(1)
    
    with open(input_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def analyze_results(products: List[Dict]) -> Dict:
    """Analyze categorization results."""
    stats = {
        "total": len(products),
        "categorized": 0,
        "needs_new_category": 0,
        "errors": 0,
        "low_confidence": 0,
        "confidence_distribution": Counter(),
        "category_distribution": Counter(),
        "new_category_suggestions": []
    }
    
    for product in products:
        cat = product.get('ai_categorization', {})
        
        if cat.get('error'):
            stats['errors'] += 1
        elif cat.get('suggest_new'):
            stats['needs_new_category'] += 1
            stats['new_category_suggestions'].append({
                'product': product.get('ORIGINAL_PROD_NAME', product.get('PROD_NAME', 'Unknown')),
                'suggestion': cat.get('new_category', {}),
                'reasoning': cat.get('reasoning', '')
            })
        elif cat.get('category_id'):
            confidence = cat.get('confidence', 0)
            
            if confidence >= 70:
                stats['categorized'] += 1
            else:
                stats['low_confidence'] += 1
            
            # Track distribution
            confidence_bucket = (confidence // 10) * 10
            stats['confidence_distribution'][confidence_bucket] += 1
            stats['category_distribution'][cat['category_id']] += 1
    
    return stats


def print_summary(stats: Dict):
    """Print analysis summary."""
    print("\n" + "="*70)
    print("CATEGORIZATION ANALYSIS")
    print("="*70)
    print(f"\nTotal products:           {stats['total']}")
    print(f"✅ Successfully assigned:  {stats['categorized']} ({stats['categorized']/stats['total']*100:.1f}%)")
    print(f"⚠️  Low confidence (<70%):  {stats['low_confidence']}")
    print(f"🆕 Need new category:      {stats['needs_new_category']}")
    print(f"❌ Errors:                 {stats['errors']}")
    
    print("\n" + "-"*70)
    print("CONFIDENCE DISTRIBUTION")
    print("-"*70)
    for bucket in sorted(stats['confidence_distribution'].keys(), reverse=True):
        count = stats['confidence_distribution'][bucket]
        bar = "█" * (count // 2) if count > 0 else ""
        print(f"{bucket:3d}-{bucket+9:3d}%: {count:3d} {bar}")
    
    if stats['category_distribution']:
        print("\n" + "-"*70)
        print("TOP 10 ASSIGNED CATEGORIES")
        print("-"*70)
        for cat_id, count in stats['category_distribution'].most_common(10):
            print(f"  {cat_id}: {count} products")
    
    print("="*70 + "\n")


def print_low_confidence(products: List[Dict], threshold: int = 70):
    """Print low confidence assignments."""
    print(f"\n{'='*70}")
    print(f"LOW CONFIDENCE ASSIGNMENTS (<{threshold}%)")
    print("="*70 + "\n")
    
    low_conf = []
    for product in products:
        cat = product.get('ai_categorization', {})
        if cat.get('category_id') and cat.get('confidence', 0) < threshold:
            low_conf.append((product, cat))
    
    if not low_conf:
        print("✅ No low confidence assignments found!")
        return
    
    for i, (product, cat) in enumerate(low_conf, 1):
        prod_name = product.get('ORIGINAL_PROD_NAME', product.get('PROD_NAME', 'Unknown'))
        vendor = product.get('PrimaryVendorName', 'Unknown')
        
        print(f"[{i}/{len(low_conf)}] {prod_name[:50]}")
        print(f"  Vendor: {vendor}")
        print(f"  Category: {cat['category_id']}")
        print(f"  Confidence: {cat['confidence']}%")
        print(f"  Reasoning: {cat.get('reasoning', 'N/A')}")
        print()


def print_new_category_suggestions(products: List[Dict]):
    """Print new category suggestions."""
    print(f"\n{'='*70}")
    print("NEW CATEGORY SUGGESTIONS")
    print("="*70 + "\n")
    
    suggestions = []
    for product in products:
        cat = product.get('ai_categorization', {})
        if cat.get('suggest_new'):
            suggestions.append((product, cat))
    
    if not suggestions:
        print("✅ No new category suggestions!")
        return
    
    for i, (product, cat) in enumerate(suggestions, 1):
        prod_name = product.get('ORIGINAL_PROD_NAME', product.get('PROD_NAME', 'Unknown'))
        vendor = product.get('PrimaryVendorName', 'Unknown')
        new_cat = cat.get('new_category', {})
        
        print(f"[{i}/{len(suggestions)}] {prod_name[:50]}")
        print(f"  Vendor: {vendor}")
        print(f"  Confidence: {cat.get('confidence', 0)}%")
        print(f"  Reasoning: {cat.get('reasoning', 'N/A')}")
        print(f"  🆕 Suggested Category:")
        print(f"     Name: {new_cat.get('name', 'N/A')}")
        print(f"     Parent ID: {new_cat.get('parent_id', 'N/A')}")
        print(f"     Description: {new_cat.get('description', 'N/A')}")
        print()


def print_errors(products: List[Dict]):
    """Print errors."""
    print(f"\n{'='*70}")
    print("CATEGORIZATION ERRORS")
    print("="*70 + "\n")
    
    errors = []
    for product in products:
        cat = product.get('ai_categorization', {})
        if cat.get('error'):
            errors.append((product, cat))
    
    if not errors:
        print("✅ No errors found!")
        return
    
    for i, (product, cat) in enumerate(errors, 1):
        prod_name = product.get('ORIGINAL_PROD_NAME', product.get('PROD_NAME', 'Unknown'))
        print(f"[{i}/{len(errors)}] {prod_name[:50]}")
        print(f"  Error: {cat.get('reasoning', 'Unknown error')}")
        print()


def export_report(products: List[Dict], stats: Dict, output_file: Path):
    """Export analysis report to JSON."""
    report = {
        "summary": {
            "total": stats['total'],
            "categorized": stats['categorized'],
            "low_confidence": stats['low_confidence'],
            "needs_new_category": stats['needs_new_category'],
            "errors": stats['errors']
        },
        "new_category_suggestions": stats['new_category_suggestions'],
        "low_confidence_products": [],
        "errors": []
    }
    
    # Add low confidence products
    for product in products:
        cat = product.get('ai_categorization', {})
        if cat.get('category_id') and cat.get('confidence', 0) < 70:
            report['low_confidence_products'].append({
                'product_name': product.get('ORIGINAL_PROD_NAME', product.get('PROD_NAME', 'Unknown')),
                'vendor': product.get('PrimaryVendorName', 'Unknown'),
                'category_id': cat['category_id'],
                'confidence': cat['confidence'],
                'reasoning': cat.get('reasoning', '')
            })
    
    # Add errors
    for product in products:
        cat = product.get('ai_categorization', {})
        if cat.get('error'):
            report['errors'].append({
                'product_name': product.get('ORIGINAL_PROD_NAME', product.get('PROD_NAME', 'Unknown')),
                'error': cat.get('reasoning', 'Unknown error')
            })
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Report exported to: {output_file}")


def main():
    """Main execution."""
    parser = argparse.ArgumentParser(
        description="Review AI-generated category assignments",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--low-confidence",
        action="store_true",
        help="Show only low confidence assignments (<70%%)"
    )
    
    parser.add_argument(
        "--new-categories",
        action="store_true",
        help="Show only new category suggestions"
    )
    
    parser.add_argument(
        "--errors",
        action="store_true",
        help="Show only errors"
    )
    
    parser.add_argument(
        "--export",
        type=str,
        metavar="FILE",
        help="Export analysis report to JSON file"
    )
    
    parser.add_argument(
        "--threshold",
        type=int,
        default=70,
        help="Confidence threshold for low confidence filter (default: 70)"
    )
    
    args = parser.parse_args()
    
    # Load products
    print("Loading categorized products...")
    products = load_categorized_products()
    
    # Analyze results
    stats = analyze_results(products)
    
    # Show requested view
    if args.low_confidence:
        print_low_confidence(products, args.threshold)
    elif args.new_categories:
        print_new_category_suggestions(products)
    elif args.errors:
        print_errors(products)
    else:
        # Show full summary
        print_summary(stats)
        
        if stats['low_confidence'] > 0:
            print(f"\n💡 Tip: Run with --low-confidence to review {stats['low_confidence']} assignments")
        
        if stats['needs_new_category'] > 0:
            print(f"💡 Tip: Run with --new-categories to review {stats['needs_new_category']} suggestions")
        
        if stats['errors'] > 0:
            print(f"⚠️  Warning: Run with --errors to review {stats['errors']} errors")
    
    # Export if requested
    if args.export:
        export_path = Path(args.export)
        export_report(products, stats, export_path)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
