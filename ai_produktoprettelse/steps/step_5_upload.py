#!/usr/bin/env python3
"""
Step 5: Upload to CMS

Uploads products to Dandomain CMS via API.
Reads from: data/output/final_products.json
Writes to: data/output/upload_results.json

This is a wrapper that calls the original script during migration.
Full refactoring to use core utilities will be done incrementally.

Usage:
  python -m ai_produktoprettelse.steps.step_5_upload
"""

import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ORIGINAL_SCRIPT = PROJECT_ROOT / "scripts" / "5_upload_to_cms.py"


def main():
    """Run the original script during migration period."""
    if not ORIGINAL_SCRIPT.exists():
        print(f"ERROR: Original script not found: {ORIGINAL_SCRIPT}")
        return 1

    result = subprocess.run(
        [sys.executable, str(ORIGINAL_SCRIPT)],
        cwd=PROJECT_ROOT,
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
