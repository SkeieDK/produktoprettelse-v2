# Produktoprettelse-v2 Scripts

## Overview
Lean local-first pipeline. Each step is a standalone Python script.

## Quick Start

### 1. Sanitize CSV
```powershell
python scripts\1_sanitize.py data\input\your-file.csv
```
**Output:**
- `data/output/<filename>_sanitized.csv`
- `data/cache/processed_products.json`

### 2. Scrape Suppliers
```powershell
python scripts\2_scrape.py
```
**Output:**
- `data/output/supplier_info.json` (incremental updates)
- `data/output/run_summary.json` (status per product)

### 3. Process Images (TODO)
```powershell
python scripts\3_process_images.py
```

### 4. Generate AI Descriptions (TODO)
```powershell
python scripts\4_generate_ai.py
```

### Run All Steps
```powershell
python scripts\run_all.py
```

## Configuration

Edit `config.yaml` to customize:
- Paths (input/output/cache directories)
- Chrome binary location
- Selenium settings (headless, timeout)
- AI API keys

## Logs

Each script logs to `logs/<step>.log`:
- `logs/1_sanitize.log`
- `logs/2_scrape.log`
- etc.

## Vendor Modules

Supplier-specific scraping logic is in `supplier_pi/supplier_modules/`:
- `vikan.py`
- `pluspack.py`
- `duni.py`
- `greenway.py`
- `nordiskmicrofiber.py`

Mapping in `supplier_pi/utils/vendor_map.json`

## Requirements

```powershell
pip install -r requirements.txt
```

Key dependencies:
- pandas
- selenium + webdriver-manager
- PyYAML
- Pillow
- requests

## Architecture

### Old (removed):
- FastAPI backend (async jobs, REST API)
- React frontend (Vite, polling, state management)
- Background workers, job queues

### New:
- Simple Python scripts
- Clear inputs/outputs
- File-based state
- Run locally, no server

### Benefits:
- ✓ Fast (<1s for sanitize)
- ✓ Easy to debug (one script = one step)
- ✓ No deployment complexity
- ✓ Works offline (except scraping)
- ✓ Logs to files (no console encoding issues)

## Next Steps

1. Extract image processing to `scripts/3_process_images.py`
2. Build AI enrichment in `scripts/4_generate_ai.py`
3. Create `scripts/run_all.py` orchestrator
4. Add Streamlit app for UI (optional)
5. Dockerize for reproducible runs

## Migration from Old Structure

### What was kept:
- `supplier_pi/supplier_modules/` - vendor scraping logic
- `supplier_pi/utils/` - PDF, image, vendor map helpers
- `csv_data_transformation/` - sanitization logic

### What was removed:
- `backend/` - FastAPI server
- `frontend/` - React app
- Job polling, async workers, REST endpoints

### What was added:
- `scripts/` - Standalone pipeline steps
- `config.yaml` - Central configuration
- `data/input/`, `data/output/` - Clear I/O folders
