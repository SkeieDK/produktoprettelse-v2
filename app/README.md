# Produktoprettelse-v2 — Streamlit UI

A beautiful, user-friendly interface for the complete product enrichment pipeline.

## Features

✨ **Upload & Process**
- Drag-and-drop CSV upload
- Pipeline execution with live progress
- Step-by-step or run-all options
- Verbose logging available

⚙️ **Process Monitoring**
- Real-time status for all 4 steps
- Live log viewing
- Error and warning counts

📊 **Results Gallery**
- Product cards inspired by client's design
- Search and filter capabilities
- Pagination for large datasets
- Image preview
- Full descriptions and keywords
- SEO meta descriptions

📥 **Export**
- JSON export (preserves all data)
- CSV export (flatten for spreadsheets)
- Timestamped filenames

📋 **Logs**
- Live log viewer
- Log download capability
- Error/warning metrics

## Getting Started

### Prerequisites

- Python 3.10+
- Dependencies installed: `pip install -r requirements.txt`
- OpenAI API key in `.env` file

### Quick Start

**Option 1: Using launcher script**
```bash
python app/launch.py
```

**Option 2: Direct Streamlit**
```bash
streamlit run app/app.py
```

The app will open at **http://localhost:8501**

## Usage

### Step 1: Upload CSV
1. Go to tab **"📤 Upload & Pipeline"**
2. Click **"Browse files"** and select your CSV
3. Preview the data to confirm it's correct

### Step 2: Run Pipeline
1. Choose execution method:
   - **"▶️ Kør Alt"** - Run all 4 steps
   - **"▶️ Kør til Trin X"** - Run specific steps
2. Optional: Check **"Detaljeret output"** for verbose logging
3. Click the button and wait for completion

### Step 3: View Progress
1. Go to tab **"⚙️ Processer"**
2. See status of all 4 steps
3. Expand each step to view logs

### Step 4: View Results
1. Go to tab **"📊 Resultater"**
2. Browse the product gallery
3. Search for specific products
4. Expand sections to see:
   - Full descriptions
   - Keywords
   - Supplier information
5. Download results as JSON or CSV

## Interface Overview

### Tab 1: Upload & Pipeline
```
┌─────────────────────────────────┐
│ 📤 Trin 1: Upload CSV-fil       │
│ [File Uploader]                 │
│ ✓ Fil uploadet: products.csv    │
│ 📊 22 produkter i filen         │
│                                 │
│ ⚙️ Trin 2: Kør Pipeline         │
│ [▶️ Kør Alt] [Trin 3] [Details] │
│ ⏳ Kører pipeline (trin 1-4)... │
│ ✅ Pipeline fuldført!           │
└─────────────────────────────────┘
```

### Tab 2: Process Status
Shows real-time status of each pipeline step:
- ✅ Complete (green)
- ⏳ Running (yellow)
- ⏸️ Pending (gray)

Each step displays:
- Status indicator
- Recent log lines (last 20)
- Timestamps

### Tab 3: Results Gallery

Product cards display:
```
┌────────────┬─────────────────────────┐
│   IMAGE    │  PRODUCT DETAILS        │
│            │  E146220                │
│            │  Komposit MoppefremfØrer│
│            │  [Source Link]          │
│            │  [Description Expander] │
│            │  [Keywords Expander]    │
│            │  🎯 SEO: Meta desc...   │
└────────────┴─────────────────────────┘
```

### Tab 4: Logs
Browse and download log files:
- File selector
- Statistics (lines, errors, warnings)
- Full log content
- Download button

## Customization

### Change Styling
Edit the CSS in `app.py`:
```python
st.markdown("""
<style>
    .main-header { ... }
    .product-card { ... }
    /* etc */
</style>
""")
```

### Modify Product Card Layout
Edit `display_product_card()` function:
- Add/remove fields
- Change column layout (col1, col2, etc.)
- Adjust expanders and styling

### Configure Page Settings
Edit the top of `app.py`:
```python
st.set_page_config(
    page_title="...",
    layout="wide",  # or "centered"
    initial_sidebar_state="expanded",
)
```

## Troubleshooting

### "Module not found: streamlit"
```bash
pip install streamlit
```

### "Could not connect to localhost:8501"
Port 8501 is already in use. Streamlit will try 8502, 8503, etc.
Or specify a port:
```bash
streamlit run app/app.py --server.port 8505
```

### "No final_products.json found"
Run the pipeline first:
1. Upload CSV in tab 1
2. Click "Kør Alt"
3. Wait for completion

### Images not showing in results
Check that image paths are relative:
- Should be: `images/e146220-xxx.jpg`
- Not: `/absolute/path/to/images/...`

If paths are absolute, re-run step 3 (Image Processing).

## Performance Notes

- **First run:** ~7 minutes for 22 products (includes AI API calls)
- **Large datasets (100+ products):** Run via CLI (`python scripts/run_all.py`) for better control
- **Image loading:** May be slow if thousands of images; consider pagination

## File Structure

```
app/
├── app.py              # Main Streamlit application
├── launch.py           # Launcher script
└── README.md           # This file
```

## Tips & Tricks

### 💡 Batch Processing
For large CSV files:
1. Split into smaller batches (10-20 products each)
2. Process each batch separately
3. Combine results manually if needed

### 💡 API Cost Optimization
- Use `gpt-3.5-turbo` instead of `gpt-4o-mini` in `scripts/ai_config.py`
- Saves ~50% on AI costs

### 💡 Custom Prompts
Edit `scripts/ai_config.py` to change:
- Product description style
- Keywords extraction
- SEO meta descriptions

### 💡 Export Workflow
1. Generate results in Streamlit
2. Download JSON
3. Send to client or import to e-commerce system
4. Review and edit if needed

## Development

### Adding New Sections
1. Add a new tab in the main UI
2. Create display functions for new components
3. Update styles in the CSS section

### Custom Filters
Add to Tab 3 (Results):
```python
filter_by_category = st.selectbox("Kategori:", ["All", "Cat1", "Cat2"])
filtered = [p for p in products if filter_matches(p, filter_by_category)]
```

### Integration with E-Commerce
Export JSON and import to your system:
```python
import json
with open("products.json") as f:
    products = json.load(f)
# Upload to your e-commerce API
```

## Support

For issues:
1. Check logs in Tab 4
2. See `scripts/README.md` for pipeline help
3. See `scripts/AI_CONFIG_GUIDE.md` for AI customization

---

**Built with ❤️ using Streamlit**

Questions? Check the main project README: `../README.md`
