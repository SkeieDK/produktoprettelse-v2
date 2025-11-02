# Produktoprettelse-v2 — Lean Roadmap

This plan cuts the project to a robust local-first pipeline with a minimal app, keeps Selenium (Playwright only as a bonus), and adds Docker for reproducible runs.

## Guiding Principles
- Local-first: reliable on a single PC with a venv; no server required.
- One step = one script; clear inputs/outputs; atomic writes; log to files.
- Keep scraping and image/PDF handling modular per vendor.
- Optional UI: a tiny Streamlit app that orchestrates scripts locally.
- Docker for reproducibility (especially for Chrome/driver).

## Target Structure
```
produktoprettelse-v2/
├─ config.yaml                 # paths, chrome binary, API keys (env overrides)
├─ data/
│  ├─ input/                   # CSVs to process
│  ├─ cache/                   # temp downloads, PDFs, raw images
│  └─ output/                  # sanitized CSV, scraped JSON, enriched JSON, images
├─ logs/                       # one file per script step
├─ scripts/
│  ├─ 1_sanitize.py            # CSV cleaning
│  ├─ 2_scrape.py              # Selenium scraping, vendor modules
│  ├─ 3_process_images.py      # resize/organize images to output/images
│  ├─ 4_generate_ai.py         # AI descriptions + metadata
│  └─ run_all.py               # optional: orchestrate 1→4
├─ supplier_modules/           # vikan.py, pluspack.py, etc.
├─ utils/                      # logging, image, pdf, io helpers
├─ requirements.txt
├─ Dockerfile                  # runtime for CLI + Chrome
└─ TASKS.md                    # this file
```

---

## Milestone 1 — Local Script Pipeline (Core)
Goal: run all steps via Python CLIs, no server.

- [ ] Create `config.yaml` (paths, chrome_binary, timeouts, api placeholders)
  - Accept env overrides for secrets: e.g. `AI_API_KEY`.
  - Acceptance: scripts load config; defaults work on Windows.

- [ ] scripts/1_sanitize.py
  - Input: `data/input/<file>.csv`
  - Output: `data/output/<stem>_sanitized.csv` and `data/cache/processed_products.json`
  - Acceptance: logs to `logs/1_sanitize.log`; handles common CSV quirks.

- [ ] scripts/2_scrape.py (adapt existing scraper)
  - Read: `data/cache/processed_products.json`
  - Write incrementally: `data/output/supplier_info.json`, `data/output/run_summary.json` (atomic tmp→replace)
  - Vendor architecture: keep current per-vendor modules; no emojis in logs.
  - Selenium: detect Chrome binary, pin driver via webdriver-manager; retry non-headless.
  - Acceptance: progress printed to console; files grow as products are processed; exit code 0 on success.

- [ ] scripts/3_process_images.py
  - Read `supplier_info.json`, copy/resize images into `data/output/images/` and `data/output/images/thumbnails/`.
  - Update json `images` entries with relative paths.
  - Acceptance: thumbnails exist; JSON references are valid relative paths.

- [ ] scripts/4_generate_ai.py
  - Read: `supplier_info.json`
  - Call: AI API (OpenAI/Claude) with prompt template; batch + retry; rate-limit aware.
  - Write: `data/output/enriched_products.json` with fields: description, meta title/desc, categories, confidence.
  - Acceptance: dry-run without key; with key, small sample completes under rate limits.

- [ ] scripts/run_all.py
  - Orchestrate 1→4 with flags to stop after any step; pretty progress with `rich`.
  - Acceptance: end-to-end pipeline produces all outputs from a sample CSV.

---

## Milestone 2 — Minimal App (Streamlit)
Goal: a tiny local UI that runs the scripts; no FastAPI/React.

- [ ] `app/app.py` (Streamlit)
  - Upload CSV → save to `data/input/`
  - Buttons: Sanitize, Scrape, Process Images, Generate AI, Run All
  - Tail logs live; show progress bars; preview outputs (first N rows, thumbnails)
  - Acceptance: non-dev users can run the whole pipeline from the app.

- [ ] Packaging / launcher
  - Windows shortcut or `python -m streamlit run app/app.py`
  - Acceptance: documented start command; no extra config required.

---

## Milestone 3 — Docker (Reproducible Runtime)
Goal: provide a container that can run CLI pipeline and Streamlit app.

- [ ] `Dockerfile`
  - Base: Python slim + Chrome (stable, pinned) + webdriver-manager cache dir
  - Install requirements; create non-root user; set working dirs
  - Health: `python -c "import selenium; print('ok')"`
  - Acceptance: `docker run` can execute `scripts/run_all.py` against a mounted `data/` volume.

- [ ] `docker-compose.yml` (optional for app)
  - Service for Streamlit on port 8501; volume mount `./data:/app/data`
  - Acceptance: `docker compose up` brings up the app and pipeline can run.

- [ ] Docs: Windows host notes
  - If Chrome conflicts: advise container-only scraping.

---

## Milestone 4 — Reliability & QA
Goal: reduce surprises; make runs repeatable and observable.

- [ ] Robust logging
  - One log per script; rotate by size; UTF‑8 everywhere; no emojis.

- [ ] Unit tests (pytest)
  - utils/image resize small test; pdf text extraction; path utilities.

- [ ] Sample dataset
  - `data/input/sample.csv` + `docs/sample_run.md` with expected outputs.

- [ ] Error budgets & retries
  - Network timeouts, exponential backoff for scraping and AI calls; partial failure handling per item.

---

## Milestone 5 — Documentation
Goal: easy onboarding for teammates and clients.

- [ ] README overhaul
  - Setup venv, install, config, run scripts, run app, run in Docker.

- [ ] CHANGELOG and versioning
  - Tag milestones; semantic versioning for pipeline outputs.

---

## Bonus (not required)
- [ ] Playwright migration for more stable headless runs.
- [ ] Pre-built Windows executable (PyInstaller) for the Streamlit app.

---

## Decommission (remove complexity)
- [ ] Remove `backend/` and `frontend/` from the repo once Streamlit is in place.
- [ ] Remove job polling and FastAPI code; keep only what scripts need.

---

## Acceptance Matrix (Quick Reference)
- End-to-end run from CLI produces: sanitized CSV, supplier_info.json, run_summary.json, images+thumbs, enriched_products.json.
- Streamlit app can run each step and preview results.
- Docker image can run the pipeline against a mounted data volume on Windows.
- Logs are readable, errors don’t crash the entire run, partial outputs are preserved.
