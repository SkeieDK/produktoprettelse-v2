import importlib.util
from pathlib import Path
import json

# Dynamically import the uploader module (filename starts with a digit)
module_path = Path(__file__).resolve().parent / "5_upload_to_cms.py"
spec = importlib.util.spec_from_file_location("upload_module", str(module_path))
upload_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(upload_module)
DandomainUploader = upload_module.DandomainUploader

def main():
    sample_product = {
        'PROD_NUM': 'TEST123',
        'ORIGINAL_VENDOR_NUM': 'VENDOR1',
        'PROD_NAME': 'Test Product',
        'FIELD_1': 'CF1',
        'FIELD_2': 'CF2',
        'FIELD_17': 'CF17',
        'FIELD_18': 'CF18',
        'FIELD_20': 'CF20',
        'ACTIVE_UNIT_ID': 6,
        'primaryCategoryId': '1001001000000',
    }

    uploader = DandomainUploader(dry_run=True)
    product, settings = uploader.map_to_dandomain_schema(sample_product, image_urls=[], pdf_url=None)
    print("Product payload:")
    print(json.dumps(product, indent=2, ensure_ascii=False))
    print("Settings payload:")
    print(json.dumps(settings, indent=2, ensure_ascii=False))
    # Simple assertions
    assert settings.get('customField1') == 'CF1'
    assert settings.get('customField2') == 'CF2'
    assert settings.get('customField17') == 'CF17'
    assert settings.get('customField18') == 'CF18'
    assert settings.get('customField20') == 'CF20'
    assert settings.get('unitNumber') == 6
    print('Settings payload is correct')

if __name__ == '__main__':
    main()
