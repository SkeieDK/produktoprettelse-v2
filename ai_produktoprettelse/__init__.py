"""
AI Produktoprettelse Pipeline Package

This package contains the 5-step product creation pipeline:
- Step 1: CSV Sanitization
- Step 2: Supplier Scraping
- Step 3: Image Processing
- Step 3.5: AI Categorization
- Step 4: AI Description Generation
- Step 5: CMS Upload

The pipeline can be run entirely via `run_all.py` or steps individually.

Usage:
    # Run entire pipeline
    python -m ai_produktoprettelse.run_all

    # Run individual steps
    python -m ai_produktoprettelse.steps.step_1_sanitize
    python -m ai_produktoprettelse.steps.step_2_scrape
    python -m ai_produktoprettelse.steps.step_3_images
    python -m ai_produktoprettelse.steps.step_3_5_categorize
    python -m ai_produktoprettelse.steps.step_4_ai
    python -m ai_produktoprettelse.steps.step_5_upload
"""

from pathlib import Path

# Package-level constants
PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent

__all__ = [
    "PACKAGE_ROOT",
    "PROJECT_ROOT",
]
