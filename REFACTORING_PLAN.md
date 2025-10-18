# Refactoring Plan: Produktoprettelse Pipeline Integration

## Overview
The current system has two disconnected workflows:
1. **CSV Data Transformation** (`sanitering.py`) - Processes and transforms CSV product data
2. **Supplier Scraping** (`supplier_pi/main.py`) - Scrapes supplier websites for product information using Excel input

**Goal**: Connect these workflows and centralize repetitive scraping logic for scalability.

---

## Current State Analysis

### Sanitering.py (CSV Data Transformation)
- ✅ Reads raw CSV product data
- ✅ Transforms and cleans data (type conversion, column renaming, pricing calculations)
- ✅ Outputs processed DataFrame with columns: `PROD_NUM`, `ORIGINAL_PROD_NAME`, `PROD_BARCODE_NUMBER`, etc.
- ❌ **No output mechanism** - Currently only returns DataFrame in memory
- ❌ **Not integrated** with supplier scraping pipeline

### Supplier Modules (duni.py, vikan.py, greenway.py, etc.)
Each module contains repetitive logic:
- ✅ Vendor-specific scraping functions
- ✅ Image downloading and processing
- ✅ PDF extraction logic
- ❌ **Duplicated code**: Cookie handling, image resizing, PDF extraction, error handling
- ❌ **Inconsistent interfaces**: Different function signatures and return formats
- ❌ **Tightly coupled**: Image resizing, PDF extraction, and vendor-specific logic mixed together
- ❌ **Hard to scale**: Adding new vendors requires copy-pasting large amounts of code

### Main.py Issues
- Reads from Excel instead of sanitering.py output
- Has fallback PDF/image download logic (should be centralized)
- Hard-coded folder paths
- Inconsistent vendor module interfaces (vikan uses `scrape()`, others use `extract_supplier_info()`)

---

## Proposed Architecture

### Phase 1: Data Output & Integration
**Goal**: Enable `sanitering.py` to output data that the scraper can consume

```
sanitering.py
    │
    ├─ process() returns DataFrame
    └─ output_products(filepath, format='csv'|'json')
           │
           └─ saves to: data/processed_products.csv or .json
                │
                ├─ product_scraper.py
                └─ reads from this output
```

**Changes**:
- Add `output_products()` method to `CSVSanitering` class
- Create intermediate CSV/JSON cache file that contains:
  - `PROD_NUM`, `ORIGINAL_VENDOR_NUM`, `ORIGINAL_PROD_NAME`, `PROD_BARCODE_NUMBER`
  - `PrimaryVendorName`, `PrimaryVendorItemID` (parsed or mapped)
  - `ImageURL` (if available from source data)
  - Image dimensions/requirements

**Output file location**: `data/processed_products.csv` or `cache/processed_products.json`

---

### Phase 2: Centralize Common Utilities
**Goal**: Extract repetitive code into reusable service classes

**New file**: `supplier_pi/utils/scraper_core.py`

```python
class ImageDownloadService:
    """Handles all image downloading and resizing logic"""
    - download_image(url, output_path, timeout=10)
    - download_multiple_images(urls, output_folder, img_name, max_images=4)
    - resize_images(original_folder, image_folder, img_name)

class PDFHandlingService:
    """Centralizes PDF download and text extraction"""
    - download_pdf(url, output_path, timeout=15)
    - find_pdfs_by_pattern(folder, product_number)
    - extract_text_safely(pdf_path)

class SeleniumUtilsService:
    """Common Selenium operations"""
    - setup_driver(headless=True, proxy=None)
    - handle_cookie_consent(driver, button_id)
    - wait_for_navigation(driver, timeout=10)
    - js_click(driver, element)
    - get_text_safe(element, default="")

class VendorScrapeBase:
    """Abstract base class for vendor implementations"""
    - __init__(vendor_name, config)
    - scrape_product(product_data, driver, folders)
    - extract_product_info() [abstract - implement in subclass]
    - validate_output()
```

**New file**: `supplier_pi/utils/product_data_models.py`

```python
@dataclass
class ProductInput:
    """Standardized input data for scraping"""
    prod_num: str
    product_name: str
    vendor_name: str
    vendor_item_id: str
    image_url: Optional[str] = None

@dataclass
class ScrapedProductData:
    """Standardized output from any vendor"""
    prod_num: str
    product_name: str
    supplier_information: str
    product_url: str
    images: List[str]  # paths to saved images
    pdfs: List[str]    # paths to downloaded PDFs
    metadata: Dict[str, Any]  # vendor-specific data

class ScrapingConfig:
    """Centralized configuration"""
    - image_formats: List[str]
    - max_images: int
    - pdf_columns: List[str]
    - priority_pdf_column: str
    - timeouts: Dict[str, int]
    - output_folders: Dict[str, str]
```

---

### Phase 3: Refactor Supplier Modules
**Goal**: Reduce each vendor module to ~50 lines of vendor-specific logic

**New file structure**:
```
supplier_pi/
├── supplier_modules/
│   ├── __init__.py
│   ├── base_vendor.py           # VendorScrapeBase implementation
│   ├── duni.py                  # vendor-specific logic only
│   ├── vikan.py                 # vendor-specific logic only
│   ├── greenway.py              # vendor-specific logic only
│   ├── pluspack.py
│   └── nordiskmicrofiber.py
```

**Example refactored vendor module** (`duni.py`):
```python
from .base_vendor import VendorScrapeBase

class DuniScraper(VendorScrapeBase):
    VENDOR_NAME = "Duni A/S Tyskland"
    BASE_URL = "https://dk.duni.com"
    
    def search_for_product(self, product_number):
        """Duni-specific search logic"""
        search_url = f"{self.BASE_URL}/en/search/?text={product_number}"
        return self.driver.get(search_url)
    
    def extract_product_info(self, soup):
        """Extract only Duni-specific info (description, specs)"""
        desc_tag = soup.select_one("div.description div.summary")
        return desc_tag.get_text() if desc_tag else ""
    
    def find_datasheet_link(self, soup):
        """Find Duni's specific datasheet link structure"""
        # Duni-specific PDF selector
        return soup.select_one("a.download-datasheet")
```

**Each module only implements**:
- Search/navigation logic
- Data extraction selectors (CSS, XPath)
- Vendor-specific quirks (cookie buttons, pagination, etc.)

**All else is handled by base class and utilities**:
- Image downloading, resizing, naming
- PDF downloading, extraction
- Error logging
- Result formatting

---

### Phase 4: Refactor Main Script
**Goal**: Simplify orchestration and connect to sanitering output

**New file**: `product_scraper.py` (rename from `supplier_pi/main.py`)

```python
class ProductScraper:
    """Main orchestration class"""
    
    def __init__(self, config_path=None):
        - Load config
        - Initialize all vendor scrapers
        - Setup Selenium driver
        - Initialize logging
    
    def load_products_from_sanitering(self, csv_or_df):
        """Read output from sanitering.py"""
        - Load CSV/JSON from sanitering
        - Convert to ProductInput dataclass
        - Validate required fields
    
    def scrape_product(self, product_input):
        """Process a single product"""
        - Get vendor scraper
        - Run scrape_product()
        - Handle fallback logic
        - Log results
        - Return ScrapedProductData
    
    def scrape_all_products(self, products):
        """Batch processing with progress tracking"""
        - Loop through products
        - Call scrape_product()
        - Collect results
        - Generate summary report
    
    def export_results(self, results, output_format='csv'):
        """Save results to CSV/JSON/etc"""
```

---

## Implementation Roadmap

### Task 1: Add Output to Sanitering.py
- [ ] Add `output_products(filepath, format='csv')` method
- [ ] Test output format
- [ ] Document required columns
- [ ] Create sample output file

**Files to modify**: `csv_data_transformation/sanitering.py`

**Acceptance criteria**: 
- Can run sanitering and output CSV with columns: PROD_NUM, ORIGINAL_PROD_NAME, PrimaryVendorName, PrimaryVendorItemID, ImageURL
- Output file is readable and valid CSV

---

### Task 2: Create Centralized Utilities
- [ ] Create `product_data_models.py` with dataclasses
- [ ] Create `scraper_core.py` with service classes
- [ ] Move image resizing from `image_processor.py` into `ImageDownloadService`
- [ ] Move PDF extraction into `PDFHandlingService`
- [ ] Test utilities independently

**Files to create**: 
- `supplier_pi/utils/product_data_models.py`
- `supplier_pi/utils/scraper_core.py`

**Acceptance criteria**:
- Image service can download, resize, and name images correctly
- PDF service can extract text from any vendor PDF
- Selenium utils can initialize driver and handle common patterns
- All utilities have unit tests

---

### Task 3: Create Base Vendor Class
- [ ] Implement `VendorScrapeBase` with full lifecycle
- [ ] Handle common error scenarios
- [ ] Implement retry logic
- [ ] Add logging throughout
- [ ] Document interface for vendors

**Files to create**: 
- `supplier_pi/supplier_modules/base_vendor.py`

**Acceptance criteria**:
- Base class provides image/PDF download, error handling, logging
- Vendor subclasses only implement 3-4 methods
- Each vendor module is <100 lines

---

### Task 4: Refactor Each Vendor Module
- [ ] Refactor `duni.py` → `DuniScraper(VendorScrapeBase)`
- [ ] Refactor `vikan.py` → `VicanScraper(VendorScrapeBase)`
- [ ] Refactor `greenway.py` → `GreenwayScaper(VendorScrapeBase)`
- [ ] Refactor `pluspack.py` → `PlusPackScraper(VendorScrapeBase)`
- [ ] Refactor `nordiskmicrofiber.py` → `NordiskMicroFiberScraper(VendorScrapeBase)`
- [ ] Test each vendor module independently

**Files to modify**: All vendor modules in `supplier_pi/supplier_modules/`

**Acceptance criteria**:
- Each module < 100 lines
- Each vendor can scrape their test products
- Output format is consistent across all vendors

---

### Task 5: Refactor Main Script
- [ ] Rename `supplier_pi/main.py` → `product_scraper.py` (at workspace root)
- [ ] Create `ProductScraper` orchestration class
- [ ] Integrate sanitering output loading
- [ ] Implement fallback logic as methods
- [ ] Add configuration file support
- [ ] Improve error handling and logging
- [ ] Test full pipeline

**Files to create**: 
- `product_scraper.py` (root level)

**Files to modify/delete**: 
- Remove `supplier_pi/main.py`

**Acceptance criteria**:
- Can run: `python product_scraper.py`
- Reads from sanitering output
- Scrapes all products successfully
- Exports results to CSV
- Full error logging

---

### Task 6: Create Configuration System
- [ ] Design config schema (YAML/JSON)
- [ ] Move hard-coded paths to config
- [ ] Create config file template
- [ ] Document all configuration options

**Files to create**: 
- `config/scraper_config.yaml` (template)
- `config/scraper_config.example.yaml`

**Acceptance criteria**:
- All paths are configurable
- Timeouts, retries, image settings are configurable
- Config can be overridden via CLI arguments

---

### Task 7: Documentation & Testing
- [ ] Write README for the refactored system
- [ ] Add docstrings to all classes
- [ ] Create unit tests for utilities
- [ ] Create integration tests for vendor modules
- [ ] Create end-to-end test workflow

**Files to create**: 
- `tests/test_utilities.py`
- `tests/test_vendor_modules.py`
- `README_SCRAPER.md`

**Acceptance criteria**:
- All public methods have docstrings
- Core utilities have >80% test coverage
- README explains the architecture

---

## File Structure After Refactoring

```
.
├── csv_data_transformation/
│   └── sanitering.py                    # Enhanced: adds output_products()
│
├── supplier_pi/
│   ├── supplier_modules/
│   │   ├── __init__.py                  # Registers all vendor scrapers
│   │   ├── base_vendor.py               # [NEW] Abstract base class
│   │   ├── duni.py                      # [REFACTORED] Vendor-specific only
│   │   ├── vikan.py                     # [REFACTORED]
│   │   ├── greenway.py                  # [REFACTORED]
│   │   ├── pluspack.py                  # [REFACTORED]
│   │   └── nordiskmicrofiber.py         # [REFACTORED]
│   │
│   └── utils/
│       ├── image_processor.py           # Keep (slightly refactored)
│       ├── pdf_extractor.py             # Keep
│       ├── web_scraper.py               # Keep (or deprecated)
│       ├── product_data_models.py       # [NEW] Dataclasses
│       ├── scraper_core.py              # [NEW] Service classes
│       └── vendor_map.json              # Keep
│
├── product_scraper.py                   # [NEW] Main entry point
├── config/
│   ├── scraper_config.yaml              # [NEW] Configuration
│   └── scraper_config.example.yaml      # [NEW] Example config
│
├── tests/
│   ├── test_utilities.py                # [NEW] Unit tests
│   ├── test_vendor_modules.py           # [NEW] Integration tests
│   └── test_end_to_end.py               # [NEW] E2E tests
│
├── data/
│   └── processed_products.csv           # Output from sanitering
│
└── README_SCRAPER.md                    # [NEW] Architecture docs
```

---

## Benefits of This Refactoring

| Before | After |
|--------|-------|
| Hard to add new vendors (copy-paste 200+ lines) | Add vendor in ~50 lines |
| Image download code in 5 places | Centralized `ImageDownloadService` |
| Inconsistent error handling | Standard error handling in base class |
| PDF extraction logic duplicated | Single `PDFHandlingService` |
| No data flow from sanitering to scraper | Explicit integration point |
| Hard-coded paths everywhere | Centralized configuration |
| No tests | Unit & integration tests |
| Main.py reads Excel (outdated) | Reads sanitering output |
| Each vendor has different interface | Standard `VendorScrapeBase` interface |

---

## Migration Timeline

**Estimated**: 2-3 days of work

1. **Day 1**: Tasks 1-2 (Output + Utilities)
2. **Day 2**: Tasks 3-4 (Base class + Vendor refactoring)
3. **Day 3**: Tasks 5-7 (Main script + Config + Tests)

---

## Questions for Clarification

1. **Sanitering Output Format**: Should `sanitering.py` output a CSV file automatically, or on-demand?
2. **Vendor Configuration**: Should vendor-specific settings (timeouts, retry counts) be in YAML or hardcoded?
3. **Image Requirements**: What are the exact image dimensions/formats needed?
4. **PDF Priority**: Should we always prefer datasheet PDFs or try all available types?
5. **Logging Level**: Where should logs be saved? (file, console, remote?)
6. **Parallel Processing**: Should we scrape multiple products in parallel (multi-threaded)?

---

## Next Steps

1. Review this plan with the team
2. Prioritize tasks
3. Start with Task 1 (Sanitering output)
4. Iteratively build and test each layer
5. Keep old code as backup during transition

