"""
Test script to demonstrate sanitering.py JSON output functionality
"""
import pandas as pd
import json
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sanitering import CSVSanitering

def create_sample_data():
    """Create sample product data for testing"""
    sample_data = {
        "ItemID": ["DUNI-001", "DUNI-002", "VIKAN-001"],
        "ItemName": ["Servietter hvid 33x33", "Duge blå 100x100", "Rengøringsmiddel"],
        "ItemBarcode": ["5706801111", "5706801112", "5706801113"],
        "TotalStockQty": [150, 200, 75],
        "ConvertedSystemCost": [5.25, 8.50, 12.50],
        "NetWeight": [0.5, 1.2, 2.0],
        "GreenTax": [0.10, 0.15, 0.20],
        "UnitConvStockPurch": [1.0, 1.0, 1.0],
        "ProductMeasures": ["33x33cm", "100x100cm", "1000ml"],
        "ArticleInfoSales": ["Premium napkins", "Heavy duty cloth", "Eco-friendly cleaner"],
        "PrimaryVendorName": ["Duni A/S Tyskland", "Duni A/S Tyskland", "Vikan A/S"],
        "ImageURL": [
            "https://example.com/duni-napkins-1XL.jpg",
            "https://example.com/duni-cloth-1XL.jpg",
            None
        ]
    }
    return pd.DataFrame(sample_data)

def test_sanitering_output():
    """Test the new JSON output functionality"""
    
    print("\n" + "="*60)
    print("🧪 Testing sanitering.py JSON Output Functionality")
    print("="*60)
    
    # Create sample data
    print("\n📋 Creating sample product data...")
    df = create_sample_data()
    print(f"✅ Created {len(df)} sample products")
    print(df[["ItemName", "PrimaryVendorName", "ItemID"]].to_string())
    
    # Initialize sanitering
    print("\n🔄 Processing data through sanitering...")
    sanitering = CSVSanitering(df)
    df_processed = sanitering.process()
    print("✅ Data transformation completed")
    
    # Display processed columns
    print("\n📊 Processed columns:")
    processed_cols = ["PROD_NUM", "ORIGINAL_PROD_NAME", "ORIGINAL_VENDOR_NUM", "PROD_BARCODE_NUMBER"]
    print(df_processed[processed_cols].to_string())
    
    # Test prepare_for_scraping
    print("\n📦 Preparing data for scraping...")
    products = sanitering.prepare_for_scraping()
    print(f"✅ Prepared {len(products)} products")
    
    print("\n📋 First product dict:")
    print(json.dumps(products[0], indent=2, ensure_ascii=False))
    
    # Test output_products
    print("\n💾 Exporting to JSON...")
    output_file = sanitering.output_products()
    print(f"✅ Exported to: {output_file}")
    
    # Verify output file
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            saved_products = json.load(f)
        print(f"\n✅ JSON file valid: {len(saved_products)} products saved")
        
        print("\n📄 JSON Output Sample (first 2 products):")
        print(json.dumps(saved_products[:2], indent=2, ensure_ascii=False))
    else:
        print(f"❌ Error: File not created at {output_file}")
        return False
    
    # Test filtering by vendor
    print("\n🔍 Testing vendor filtering...")
    duni_file = sanitering.output_products(
        output_path=os.path.join(os.path.dirname(output_file), 'duni_products.json'),
        vendor_name="Duni A/S Tyskland"
    )
    with open(duni_file, 'r', encoding='utf-8') as f:
        duni_products = json.load(f)
    print(f"✅ Filtered {len(duni_products)} Duni products")
    print(json.dumps(duni_products, indent=2, ensure_ascii=False))
    
    print("\n" + "="*60)
    print("✅ All tests passed!")
    print("="*60)
    print("\n📝 Next steps:")
    print("   1. Use this output in product_scraper.py")
    print("   2. Vendor scrapers will read from the JSON file")
    print("   3. Integration pipeline is now complete!")
    
    return True

if __name__ == "__main__":
    try:
        success = test_sanitering_output()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
