#!/usr/bin/env python3
"""
Run Steps 2 and 3 only (Scraping and Image Processing)

Assumes Step 1 (sanitize) has already been run.
"""

import subprocess
import sys
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

# Use the venv Python explicitly
PYTHON_EXE = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
if not PYTHON_EXE.exists():
    PYTHON_EXE = sys.executable  # Fallback

def main():
    print("="*60)
    print("Running Step 2: Supplier Scraping")
    print("="*60)
    
    # Run step 2
    result = subprocess.run(
        [str(PYTHON_EXE), str(SCRIPTS_DIR / "2_scrape.py")],
        cwd=PROJECT_ROOT
    )
    
    if result.returncode != 0:
        print("ERROR: Step 2 failed")
        return result.returncode
    
    print("\n" + "="*60)
    print("Running Step 3: Image Processing")
    print("="*60)
    
    # Run step 3
    result = subprocess.run(
        [str(PYTHON_EXE), str(SCRIPTS_DIR / "3_process_images.py")],
        cwd=PROJECT_ROOT
    )
    
    if result.returncode != 0:
        print("ERROR: Step 3 failed")
        return result.returncode
    
    print("\nSteps 2 and 3 completed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
