# Project Cleanup Plan

**Date:** November 9, 2025  
**Purpose:** Remove obsolete files and streamline the project structure

## 🗑️ Files/Folders to Delete

### 1. Empty/Obsolete Folders
- [ ] `backend/` - Empty folder, FastAPI decommissioned
- [ ] `frontend/` - Old React app, replaced by Streamlit
  - Contains `node_modules/` - can safely delete entire folder

### 2. Duplicate/Old Code
- [ ] `supplier_pi/` - **VERIFY FIRST** - May be old scraper code
  - Check if still used by scripts/2_scrape.py
  - If unused, contains: main.log, supplier_modules/, utils/, __pycache__/
  - **Action:** Review before deletion

### 3. Outdated Documentation
- [ ] `MILESTONE_1_COMPLETE.md` - Superseded by current TASKS.md
- [ ] `REFACTOR_SUMMARY.md` - Outdated refactoring notes
- [ ] `ENCODING_FIX.md` - Specific bug fix, now resolved
- [ ] `csv_data_transformation/USAGE_GUIDE.md` - Old sanitizer docs (if unused)

### 4. Old Requirements
- [ ] `requirements-DanielB-0425.txt` - Outdated (already deleted in git)

### 5. Cache/Log Files (Git Ignore)
Add to `.gitignore` if not already:
- [ ] `__pycache__/` directories
- [ ] `*.pyc` files
- [ ] `main.log` files
- [ ] `.venv/` (if committed)

---

## 📝 Files to Keep (Important)

### Core Application
✅ `app/app.py` - Main Streamlit UI  
✅ `api_manager.py` - API client with caching  
✅ `config.yaml` - Configuration  
✅ `.env` - Secrets (not in Git)  

### Scripts (All Active)
✅ `scripts/1_sanitize.py` - Step 1  
✅ `scripts/2_scrape.py` - Step 2  
✅ `scripts/3_process_images.py` - Step 3  
✅ `scripts/3.5_categorize.py` - Step 3.5  
✅ `scripts/4_generate_ai.py` - Step 4  
✅ `scripts/run_all.py` - Orchestrator  
✅ `scripts/ai_config.py` - AI configuration  
✅ `scripts/categorize_helpers.py` - Category logic  
✅ `scripts/regenerate_product.py` - Product regeneration  
✅ `scripts/review_categories.py` - Category review tool  

### Documentation (Current)
✅ `README.md` - Main docs  
✅ `TASKS.md` - Project roadmap  
✅ `AI_MANAGEMENT_GUIDE.md` - AI features  
✅ `AI_MANAGEMENT_IMPLEMENTATION.md` - Technical details  
✅ `AI_MANAGEMENT_QUICKSTART.md` - Quick start  
✅ `CATEGORIZATION_GUIDE.md` - Category mapping  
✅ `app/README.md` - App docs  
✅ `scripts/README.md` - Scripts docs  
✅ `scripts/AI_CONFIG_GUIDE.md` - AI config  

### Data Folders (Content May Vary)
✅ `data/input/` - User uploads  
✅ `data/output/` - Pipeline results  
✅ `data/cache/` - API cache, golden examples  
✅ `cache/` - Product/category cache  
✅ `logs/` - Pipeline logs  
✅ `test_files/` - Sample CSVs  

### Other
✅ `requirements.txt` - Python deps  
✅ `Dockerfile` - Docker config  
✅ `.dockerignore` - Docker ignore  
✅ `.gitignore` - Git ignore  
✅ `refresh_product_cache.py` - Cache refresh utility  

---

## ⚠️ Verification Required

### `supplier_pi/` Folder
**Before deletion:**
1. Check if `scripts/2_scrape.py` imports from `supplier_pi/`
2. Search codebase: `grep -r "supplier_pi" *.py`
3. Check: `from supplier_pi.supplier_modules`

**Expected result:**
- If `2_scrape.py` has moved supplier modules to its own structure → DELETE
- If still importing from `supplier_pi/` → KEEP

**Command to check:**
```powershell
cd "c:\Users\anton\OneDrive - Bunzl Continental Europe\Konsulent Daniel\Produktoprettelse-v2"
grep -r "supplier_pi" scripts/*.py app/*.py
```

---

## 🔍 Dependency Audit Results

### Currently Used (Keep in requirements.txt)
✅ `pandas` - CSV processing  
✅ `requests` - HTTP requests  
✅ `Pillow` - Image processing  
✅ `PyYAML` - Config parsing  
✅ `python-dotenv` - Environment variables  
✅ `selenium` - Web scraping  
✅ `webdriver-manager` - Chrome driver  
✅ `beautifulsoup4` - HTML parsing  
✅ `lxml` - XML/HTML parsing  
✅ `PyMuPDF` - PDF extraction  
✅ `openai` - AI API  
✅ `openai-agents` - AI agents SDK  
✅ `numpy` - Embeddings  
✅ `streamlit` - UI  
✅ `rich` - CLI progress (run_all.py)  
✅ `tqdm` - Progress bars (api_manager.py)  
✅ `typing-extensions` - Type hints  

### Not Found in Code (Can Remove)
❌ `playwright` - Not imported anywhere  
❌ `aiohttp` - Not imported anywhere  

---

## 📋 Cleanup Steps

### Step 1: Safe Deletions (No Verification Needed)
```powershell
cd "c:\Users\anton\OneDrive - Bunzl Continental Europe\Konsulent Daniel\Produktoprettelse-v2"

# Delete empty/obsolete folders
Remove-Item -Recurse -Force backend
Remove-Item -Recurse -Force frontend

# Delete outdated docs
Remove-Item MILESTONE_1_COMPLETE.md
Remove-Item REFACTOR_SUMMARY.md
Remove-Item ENCODING_FIX.md
```

### Step 2: Verify Then Delete
```powershell
# Check if supplier_pi is used
grep -r "supplier_pi" scripts/*.py app/*.py

# If no results (not used), delete:
Remove-Item -Recurse -Force supplier_pi
```

### Step 3: Update .gitignore
Add these lines if not present:
```gitignore
# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python

# Environments
.venv/
venv/
ENV/

# Logs
*.log
main.log

# Cache
cache/
.cache/

# OS
.DS_Store
Thumbs.db
```

### Step 4: Clean Git History (Optional)
```powershell
# Remove pycache from git tracking
git rm -r --cached **/__pycache__
git commit -m "chore: remove __pycache__ from git tracking"
```

### Step 5: Update Requirements
Already done! ✅
- Removed "Future:" comments
- Organized by category
- All deps verified as used

---

## ✅ Checklist

- [ ] Delete `backend/` folder
- [ ] Delete `frontend/` folder
- [ ] Verify `supplier_pi/` usage
- [ ] Delete `supplier_pi/` (if not used)
- [ ] Delete `MILESTONE_1_COMPLETE.md`
- [ ] Delete `REFACTOR_SUMMARY.md`
- [ ] Delete `ENCODING_FIX.md`
- [ ] Update `.gitignore`
- [ ] Clean git cache (`__pycache__`)
- [ ] Replace `TASKS.md` with `TASKS_NEW.md`
- [ ] Commit all changes
- [ ] Test pipeline still works

---

## 🎯 Expected Result

### Before Cleanup
```
produktoprettelse-v2/
├─ backend/           ❌ Empty
├─ frontend/          ❌ Old React
├─ supplier_pi/       ❓ Verify
├─ app/               ✅ Keep
├─ scripts/           ✅ Keep
├─ data/              ✅ Keep
├─ logs/              ✅ Keep
├─ cache/             ✅ Keep
├─ MILESTONE_1_COMPLETE.md  ❌ Outdated
├─ REFACTOR_SUMMARY.md      ❌ Outdated
├─ ENCODING_FIX.md          ❌ Outdated
├─ requirements.txt         ✅ Updated
└─ ... (other files)
```

### After Cleanup
```
produktoprettelse-v2/
├─ app/               ✅ Streamlit UI
├─ scripts/           ✅ Pipeline steps
├─ data/              ✅ Data folders
├─ logs/              ✅ Log files
├─ cache/             ✅ API cache
├─ AI_MANAGEMENT_*.md ✅ Current docs
├─ CATEGORIZATION_GUIDE.md ✅ Current docs
├─ TASKS.md           ✅ Updated roadmap
├─ README.md          ✅ Main docs
├─ requirements.txt   ✅ Clean deps
├─ config.yaml        ✅ Config
├─ api_manager.py     ✅ API client
└─ ... (essential files only)
```

---

## 📊 Size Reduction Estimate

- `frontend/node_modules/` - **~200-500 MB** (largest)
- `backend/` + `frontend/` - **~500 MB total**
- `supplier_pi/` - **~5-10 MB** (if deleted)
- Old docs - **~100 KB**

**Total savings:** ~500+ MB

---

## ⚡ Quick Cleanup Command

```powershell
# Run this after verification
cd "c:\Users\anton\OneDrive - Bunzl Continental Europe\Konsulent Daniel\Produktoprettelse-v2"

# Safe deletions
Remove-Item -Recurse -Force backend, frontend
Remove-Item MILESTONE_1_COMPLETE.md, REFACTOR_SUMMARY.md, ENCODING_FIX.md

# Verify supplier_pi first!
# grep -r "supplier_pi" scripts/*.py app/*.py
# If safe: Remove-Item -Recurse -Force supplier_pi

# Update tasks
Move-Item TASKS_NEW.md TASKS.md -Force

# Commit
git add -A
git commit -m "chore: cleanup obsolete files and update documentation"
```
