"""
Example: How the scraper will consume the JSON output from sanitering.py

This shows the integration point between the two components.
"""

import json
from typing import List, Dict

def load_products_from_sanitering(json_file_path: str) -> List[Dict]:
    """
    Load processed products from sanitering.py JSON output.
    
    Args:
        json_file_path: Path to the JSON file (e.g., 'cache/processed_products.json')
    
    Returns:
        List of product dictionaries
    """
    with open(json_file_path, 'r', encoding='utf-8') as f:
        products = json.load(f)
    
    print(f"✅ Loaded {len(products)} products from sanitering output")
    return products


def process_product_for_scraping(product: Dict) -> Dict:
    """
    Prepare a single product for scraping.
    
    Example transformation before passing to vendor scraper.
    """
    return {
        # Essential fields for scraper
        "PROD_NUM": product["PROD_NUM"],
        "product_name": product["product_name"],
        "vendor_name": product["vendor_name"],
        "vendor_item_id": product["vendor_item_id"],  # Used for search
        "image_url": product["image_url"],
        
        # Metadata
        "barcode": product["barcode"],
        "stock_count": product["stock_count"],
        "cost_price": product["cost_price"],
    }


def example_scraping_pipeline():
    """
    Example of how product_scraper.py will use this data.
    """
    print("\n" + "="*60)
    print("🔗 Integration Example: Sanitering → Scraper Pipeline")
    print("="*60)
    
    # Step 1: Load processed products from sanitering
    # (In real usage, this would be the output from sanitering.py)
    sample_products = [
        {
            "PROD_NUM": "E146220 - Deaktiveret",
            "product_name": "Servietter hvid 33x33",
            "vendor_name": "Duni A/S Tyskland",
            "vendor_item_id": "DUNI-001",
            "image_url": "https://example.com/duni-napkins.jpg",
            "barcode": "5706801111",
            "stock_count": 150,
            "cost_price": 5.25
        },
        {
            "PROD_NUM": "E146230 - Deaktiveret",
            "product_name": "Rengøringsmiddel",
            "vendor_name": "Vikan A/S",
            "vendor_item_id": "VIKAN-001",
            "image_url": None,
            "barcode": "5706801112",
            "stock_count": 75,
            "cost_price": 12.50
        }
    ]
    
    print("\n📦 Products from sanitering.py:")
    for product in sample_products:
        print(f"\n  • {product['product_name']}")
        print(f"    Vendor: {product['vendor_name']}")
        print(f"    Vendor ID: {product['vendor_item_id']}")
        print(f"    Image: {product['image_url'] or '(no image)'}")
    
    # Step 2: The scraper would iterate through products
    print("\n\n🔄 Scraper Processing Pipeline:")
    print("-" * 60)
    
    results = []
    for i, product in enumerate(sample_products, 1):
        prepared = process_product_for_scraping(product)
        print(f"\n{i}. Processing: {prepared['product_name']}")
        print(f"   Vendor: {prepared['vendor_name']}")
        print(f"   Search term: {prepared['vendor_item_id']}")
        
        # This is where the scraper would:
        # 1. Get the correct vendor module (e.g., DuniScraper, VicanScraper)
        # 2. Search for the product using vendor_item_id
        # 3. Download images
        # 4. Extract product information
        # 5. Combine with metadata
        
        scraped_data = {
            **prepared,
            "scraper_status": "simulated_success",
            "downloaded_images": ["image1.jpg", "image2.jpg"] if prepared['image_url'] else [],
            "supplier_info": "Example: Product information extracted from vendor website",
            "product_url": "https://example.com/product-page"
        }
        results.append(scraped_data)
        print(f"   ✅ Scraping complete")
        print(f"      Images: {len(scraped_data['downloaded_images'])}")
    
    # Step 3: Export results
    print("\n\n📊 Final Results:")
    print("-" * 60)
    
    output_file = "cache/scraped_products.json"  # Would be the final output
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Exported {len(results)} scraped products to: {output_file}")
    print("\n📋 Sample result:")
    print(json.dumps(results[0], indent=2, ensure_ascii=False))
    
    print("\n" + "="*60)
    print("✅ Pipeline Complete!")
    print("="*60)
    print("""
    Summary of flow:
    1. sanitering.py reads raw CSV
    2. Transforms data (types, prices, etc.)
    3. Outputs to JSON: cache/processed_products.json ✅
    4. product_scraper.py loads this JSON
    5. Scraper gets vendor module for each product
    6. Vendor-specific scraping logic runs
    7. Results exported to cache/scraped_products.json
    """)


if __name__ == "__main__":
    example_scraping_pipeline()
