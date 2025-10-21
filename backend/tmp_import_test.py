import importlib, traceback
try:
    importlib.import_module('main')
    print('IMPORT_OK')
except Exception:
    traceback.print_exc()
