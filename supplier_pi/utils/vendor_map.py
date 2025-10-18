import json
import os

# Load vendor module map from JSON file
VENDOR_MAP_FILE = os.path.join(os.path.dirname(__file__), 'vendor_map.json')

with open(VENDOR_MAP_FILE, 'r', encoding='utf-8') as file:
    vendor_module_map = json.load(file)