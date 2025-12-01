#!/usr/bin/env python3
"""
Step 3: Image Processing

Processes and organizes product images, downloads PDFs.
Reads from: data/output/supplier_info.json
Writes to: data/output/enriched_products.json, data/output/images/

This is a wrapper that calls the original script during migration.
Full refactoring to use core utilities will be done incrementally.

Usage:
  python -m ai_produktoprettelse.steps.step_3_images
"""

import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ORIGINAL_SCRIPT = PROJECT_ROOT / "scripts" / "3_process_images.py"


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
