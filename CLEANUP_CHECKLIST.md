# Cleanup Checklist

## Files to DELETE (obsolete/redundant)

### Old UI/Server files
- [x] `backend/` - DELETED by user
- [x] `frontend/` - DELETED by user
- [ ] `csv_dashboard.py` - Old Streamlit prototype (will be replaced by `app/app.py`)
- [ ] `csv_manager.py` - Simple CSV reader (now handled by `scripts/1_sanitize.py`)

### Old documentation (outdated)
- [ ] `CODE_FLOW.md` - Describes old backend/frontend flow
- [ ] `DETAILED_WALKTHROUGH.md` - Old architecture walkthrough
- [ ] `VISUAL_SUMMARY.md` - Old system diagram
- [ ] `QUICK_REFERENCE.md` - Old API reference
- [ ] `INTEGRATION_EXAMPLE.py` - Backend integration example
- [ ] `TASK_1_COMPLETE.md` - Old task tracking
- [ ] `TASK_1_SUMMARY.md` - Old task summary
- [ ] `REFACTORING_PLAN.md` - Superseded by TASKS.md

### Logs (can be cleaned periodically)
- [ ] `logs/job_*.log` - Old backend job logs
- [ ] `logs/upload*.log` - Old backend upload logs
- [ ] `logs/uvicorn*.log` - Old server logs
- [ ] `logs/progress_requests.log` - Old backend API logs
- [ ] `main.log` - Old root-level log (scripts now use logs/ folder)

## Files to KEEP

### Core functionality
- ✓ `supplier_pi/` - Vendor scraping modules (used by 2_scrape.py)
- ✓ `csv_data_transformation/` - CSV sanitization logic (used by 1_sanitize.py)
- ✓ `cache/` - Cache directory (used by scripts)
- ✓ `test_files/` - Sample CSVs for testing

### New structure
- ✓ `scripts/` - New pipeline scripts
- ✓ `config.yaml` - Central configuration
- ✓ `data/` - Input/output folders
- ✓ `TASKS.md` - Current roadmap
- ✓ `REFACTOR_SUMMARY.md` - Progress tracking

### Infrastructure
- ✓ `.gitignore`
- ✓ `.dockerignore`
- ✓ `Dockerfile`
- ✓ `.env`
- ✓ `requirements.txt` (needs updating)

### Mixed (needs review)
- ? `api_manager.py` - API calls to product database (might be needed for Step 4: AI enrichment)

## Updates Required

### 1. requirements.txt
**Remove:**
- fastapi
- uvicorn[standard]
- python-multipart (FastAPI dependency)

**Add (for future Streamlit app):**
- streamlit (already present ✓)
- rich (for CLI progress bars)

**Keep:**
- pandas, PyYAML, Pillow, requests
- selenium, webdriver-manager
- PyMuPDF (PDF extraction)
- openai (for Step 4)
- beautifulsoup4, lxml

### 2. README.md
**Complete rewrite needed:**
- Remove backend/frontend setup instructions
- Add scripts usage guide
- Add config.yaml documentation
- Add folder structure explanation

### 3. .gitignore
**Add:**
```
# New structure
data/input/*.csv
data/output/*
data/cache/*.json
logs/*.log
!logs/.gitkeep

# Old
main.log
```

### 4. Dockerfile (optional - for Milestone 3)
**Needs update:**
- Remove FastAPI/React setup
- Add scripts execution
- Keep Chrome + Selenium

## Path References to Check

### In scripts/
- ✓ `1_sanitize.py` - Uses config.yaml paths
- ✓ `2_scrape.py` - Uses config.yaml paths
- All paths are relative to PROJECT_ROOT or from config ✓

### In supplier_pi/
- Check if any modules reference old backend/ or frontend/
- Verify all imports still work

## Actions Summary

**High Priority (do now):**
1. Update requirements.txt (remove FastAPI deps)
2. Delete old docs (CODE_FLOW.md, etc.)
3. Rewrite README.md
4. Update .gitignore

**Medium Priority:**
5. Delete csv_dashboard.py and csv_manager.py
6. Review api_manager.py (keep if needed for AI step)
7. Clean old logs

**Low Priority:**
8. Update Dockerfile for new structure
9. Add scripts/run_all.py orchestrator
