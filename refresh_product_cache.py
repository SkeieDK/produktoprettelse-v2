#!/usr/bin/env python3
"""
Refresh product cache with settings (descriptions) included.

This will fetch all products from the API with the 'settings' parameter
to get product names, descriptions, and metadata.
"""

from api_manager import get_api_manager
import sys

def main():
    print("=" * 60)
    print("Refresh Product Cache (with descriptions)")
    print("=" * 60)
    
    try:
        # Get API manager
        mgr = get_api_manager()
        
        print("\n🗑️  Clearing old cache...")
        mgr.clear_cache("products")
        
        print("\n📥 Fetching products from API (with settings)...")
        print("   This will include: name, descriptions, keywords, meta tags")
        print("   Expected time: ~2-5 minutes for 92,000 products\n")
        
        # Fetch with settings included
        products = mgr.get_all_products(
            use_cache=False,
            include_settings=True,
            include_categories=True,
        )
        
        print(f"\n✅ Successfully cached {len(products):,} products!")
        
        # Show example product with descriptions
        if products:
            print("\n" + "=" * 60)
            print("Example product with descriptions:")
            print("=" * 60)
            
            example = products[0]
            print(f"Number: {example.get('number', 'N/A')}")
            
            # Check if settings exist
            settings = example.get('settings', {})
            if settings and 'items' in settings and settings['items']:
                first_setting = settings['items'][0]
                print(f"Name: {first_setting.get('name', 'N/A')}")
                print(f"Short Desc: {first_setting.get('shortDescription', 'N/A')[:80]}...")
                print(f"Long Desc: {first_setting.get('longDescription', 'N/A')[:80]}...")
                print(f"Meta Desc: {first_setting.get('metaDescription', 'N/A')[:80]}...")
                print(f"Keywords: {first_setting.get('keyWords', 'N/A')[:80]}...")
            else:
                print("⚠️  No settings found in example product!")
                print("   API might not have returned 'settings' - check include parameter")
        
        print("\n" + "=" * 60)
        print("✅ Cache refresh complete!")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Launch Streamlit UI: python app/launch.py")
        print("  2. Go to AI Management → Golden Examples")
        print("  3. You should now see product names and descriptions!")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
