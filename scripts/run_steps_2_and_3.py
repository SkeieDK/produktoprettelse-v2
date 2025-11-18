#!/usr/bin/env python3
"""
Run Step 2 (Scrape) and Step 3 (Process Images) sequentially.
Used by the Streamlit app for the "Step 2+3" button.
"""

import sys
import subprocess
from pathlib import Path

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

def run_script(script_name):
    """Run a script and return its exit code."""
    script_path = SCRIPTS_DIR / script_name
    print(f"Running {script_name}...")
    
    try:
        # Pass through stdout/stderr to be captured by the caller (app.py)
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(PROJECT_ROOT),
            check=True
        )
        return result.returncode
    except subprocess.CalledProcessError as e:
        print(f"Error running {script_name}: {e}")
        return e.returncode
    except Exception as e:
        print(f"Unexpected error running {script_name}: {e}")
        return 1

def main():
    # Step 2: Scrape
    exit_code = run_script("2_scrape.py")
    if exit_code != 0:
        print("Step 2 failed. Stopping.")
        return exit_code
    
    print("-" * 40)
    
    # Step 3: Process Images
    exit_code = run_script("3_process_images.py")
    if exit_code != 0:
        print("Step 3 failed.")
        return exit_code
    
    print("Step 2 and 3 completed successfully.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
