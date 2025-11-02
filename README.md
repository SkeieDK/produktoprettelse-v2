# Produktoprettelse-v2

> Lean local-first pipeline for CSV sanitization, supplier scraping, image processing, and AI-powered product enrichment.

## Quick Start

### 1. Setup
```powershell
# Clone and navigate
cd Produktoprettelse-v2

# Install dependencies
pip install -r requirements.txt

# Copy and configure
cp config.yaml.example config.yaml
# Edit config.yaml with your paths and settings
```

### 2. Run Pipeline

#### Step 1: Sanitize CSV
```powershell
python scripts\1_sanitize.py data\input\your-file.csv
```
**Output:** `data/output/<file>_sanitized.csv` + `data/cache/processed_products.json`

#### Step 2: Scrape Suppliers
```powershell
python scripts\2_scrape.py
```
**Output:** `data/output/supplier_info.json` + `data/output/run_summary.json`

#### Step 3-4: Coming Soon
- Image processing
- AI enrichment

## Project Structure

```
produktoprettelse-v2/
├── config.yaml              # Configuration (paths, Chrome, API keys)
├── scripts/                 # Pipeline steps
│   ├── 1_sanitize.py       # CSV cleaning
│   ├── 2_scrape.py         # Supplier scraping
│   ├── 3_process_images.py # (TODO) Image resize/organize
│   ├── 4_generate_ai.py    # (TODO) AI descriptions
│   └── run_all.py          # (TODO) Orchestrator
├── data/
│   ├── input/              # Drop CSV files here
│   ├── output/             # Results
│   └── cache/              # Temp files
├── logs/                    # One log per script
├── supplier_pi/
│   ├── supplier_modules/   # Vendor-specific scrapers
│   └── utils/              # PDF, image, vendor map
├── csv_data_transformation/ # CSV sanitization logic
└── requirements.txt
```

## Configuration

Edit `config.yaml`:

```yaml
paths:
  input_dir: "data/input"
  output_dir: "data/output"
  
chrome:
  binary_path: ""  # Auto-detect or specify
  headless: true
  
ai:
  api_key: ""  # Or set AI_API_KEY env var
```

## Supported Vendors

- Vikan
- Pluspack
- Duni
- Greenway
- Nordisk Microfiber

Add more in `supplier_pi/supplier_modules/` + `supplier_pi/utils/vendor_map.json`

## Logs

Each script logs to `logs/<step>.log`:
- `logs/1_sanitize.log`
- `logs/2_scrape.log`
- etc.

UTF-8 safe, no emoji crashes.

## Development

### Add a new vendor

1. Create `supplier_pi/supplier_modules/your_vendor.py`
2. Implement `extract_supplier_info(row, original_folder, driver, download_folder)`
3. Add mapping in `supplier_pi/utils/vendor_map.json`

### Run tests
```powershell
pytest tests/
```

## Roadmap

See [`TASKS.md`](TASKS.md) for full plan.

**Current Status:**
- ✅ Step 1: CSV Sanitization
- ✅ Step 2: Supplier Scraping
- ⏳ Step 3: Image Processing
- ⏳ Step 4: AI Enrichment
- ⏳ Streamlit UI
- ⏳ Docker image

## Architecture

### Design Principles
- **Local-first:** No server required
- **One script = one step:** Clear, debuggable
- **Config-driven:** Paths and settings in one place
- **Incremental writes:** Progress preserved on crash
- **Observable:** Logs show everything

### What Changed (v2 Refactor)
**Removed:**
- FastAPI backend (async jobs, REST API)
- React frontend (Vite, state management)
- Background workers, job queues

**Added:**
- Standalone Python scripts
- `config.yaml` central config
- Clear `data/input` → `data/output` flow

**Result:**
- Startup: seconds (was minutes)
- Debug: one file (was distributed state)
- Deploy: `pip install` (was Docker + nginx + …)

## Requirements

- Python 3.10+
- Chrome (for Selenium)
- OneDrive folders configured (for images/PDFs)

## Contributing

1. Check [`TASKS.md`](TASKS.md) for open work
2. Create feature branch
3. Add tests for new functionality
4. Submit PR

## License

Internal Bunzl project.

## Contact

Konsulent Daniel / Anton
