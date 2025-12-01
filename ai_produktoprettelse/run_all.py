#!/usr/bin/env python3
"""
Produktoprettelse-v2: Complete Pipeline Orchestrator

Runs all steps of the product enrichment pipeline:
  1. Sanitize CSV input
  2. Scrape supplier information
  3. Process and organize images
  3.5. AI-powered category assignment
  4. Generate AI descriptions
  5. Upload to CMS

Refactored from: scripts/run_all.py
Now uses new ai_produktoprettelse package structure.

Features:
  - Run all steps or stop after any step (--stop-after flag)
  - Pretty progress output with rich
  - Verbose logging option
  - Summary of all outputs
  - Exit codes for automation/scripting

Usage:
  python -m ai_produktoprettelse.run_all                    # Run all steps
  python -m ai_produktoprettelse.run_all --verbose          # Show detailed logs
  python -m ai_produktoprettelse.run_all --stop-after 3.5   # Stop after categorization
  python -m ai_produktoprettelse.run_all --help             # Show options
"""

import subprocess
import sys
import argparse
from pathlib import Path
from typing import Tuple, List

try:
    from rich.console import Console

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Warning: 'rich' not installed. Using basic output.")
    print("Install with: pip install rich")


# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
STEPS_DIR = PROJECT_ROOT / "ai_produktoprettelse" / "steps"
LOGS_DIR = PROJECT_ROOT / "logs"
DATA_OUTPUT = PROJECT_ROOT / "data" / "output"

# Rich console (or fallback)
console = Console() if RICH_AVAILABLE else None


def print_header():
    """Print pipeline header."""
    print("\n" + "=" * 60)
    print("Produktoprettelse-v2 Pipeline")
    print("Complete product enrichment workflow")
    print("=" * 60 + "\n")


def print_step(step_num: str, title: str, description: str):
    """Print step header."""
    print(f"\n--- Step {step_num}: {title} ---")
    print(f"{description}\n")


def run_script(
    step_num: str, script_name: str, title: str, verbose: bool = False
) -> Tuple[bool, str]:
    """
    Run a step script and return (success, output_summary).

    Args:
        step_num: Step number (1, 2, 3, 3.5, 4, 5)
        script_name: Script filename (e.g., "step_1_sanitize.py")
        title: Display title
        verbose: Show all output to console

    Returns:
        (success: bool, summary: str)
    """
    script_path = STEPS_DIR / script_name

    if not script_path.exists():
        error_msg = f"Script not found: {script_path}"
        print(f"ERROR: {error_msg}")
        return False, error_msg

    print_step(step_num, title, f"Running {script_name}...")

    try:
        # Simple subprocess execution
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=PROJECT_ROOT,
            capture_output=(not verbose),
            text=True,
            check=True,
        )

        # Print last few lines of output if captured
        if not verbose and result.stdout:
            lines = result.stdout.strip().split("\n")
            for line in lines[-5:]:
                print(f"  {line}")

        print(f"[OK] Step {step_num} complete")
        return True, f"Step {step_num} succeeded"

    except subprocess.CalledProcessError as e:
        error_msg = f"Step {step_num} failed with exit code {e.returncode}"
        print(f"ERROR: {error_msg}")
        if e.stderr:
            print(f"STDERR: {e.stderr[:500]}")
        return False, error_msg

    except Exception as e:
        error_msg = f"Step {step_num} error: {str(e)}"
        print(f"ERROR: {error_msg}")
        return False, error_msg


def check_output_files() -> dict:
    """Check which output files exist."""
    return {
        "sanitized_csv": bool(list(DATA_OUTPUT.glob("*_sanitized.csv"))),
        "processed_json": bool(list(DATA_OUTPUT.glob("*_processed.json"))),
        "supplier_info": (DATA_OUTPUT / "supplier_info.json").exists(),
        "enriched_products": (DATA_OUTPUT / "enriched_products.json").exists(),
        "categorized_products": (DATA_OUTPUT / "categorized_products.json").exists(),
        "images_dir": (DATA_OUTPUT / "images").exists(),
        "final_products": (DATA_OUTPUT / "final_products.json").exists(),
        "upload_results": (DATA_OUTPUT / "upload_results.json").exists(),
    }


def print_summary(results: List[Tuple[str, bool, str]], outputs: dict):
    """Print final summary in plain text format."""
    print("\n" + "=" * 60)
    print("PIPELINE SUMMARY")
    print("=" * 60)
    for step_num, success, msg in results:
        status = "[OK] Success" if success else "[FAIL] Failed"
        print(f"Step {step_num}: {status}")
    print("\nOutput files:")
    for name, exists in outputs.items():
        status = "[OK]" if exists else "[--]"
        print(f"  {status} {name}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run the Produktoprettelse-v2 pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                        Run all 5 steps
  %(prog)s --verbose              Show detailed output
  %(prog)s --stop-after 3.5       Stop after categorization
        """,
    )

    parser.add_argument(
        "--stop-after",
        type=str,
        default="5",
        choices=["1", "2", "3", "3.5", "4", "5"],
        help="Stop after this step (default: 5 = all steps)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output from each step",
    )

    parser.add_argument(
        "--no-rich",
        action="store_true",
        help="Disable rich formatting (use plain text)",
    )

    args = parser.parse_args()

    # Disable rich if requested
    if args.no_rich or not RICH_AVAILABLE:
        global console
        console = None

    # Print header
    print_header()

    # Check that input data exists
    input_dir = PROJECT_ROOT / "data" / "input"
    if not list(input_dir.glob("*.csv")):
        print("ERROR: No CSV files found in data/input/")
        return 1

    # Run steps - using new step file names
    results = []
    steps = [
        ("1", "step_1_sanitize.py", "CSV Sanitization"),
        ("2", "step_2_scrape.py", "Supplier Scraping"),
        ("3", "step_3_images.py", "Image Processing"),
        ("3.5", "step_3_5_categorize.py", "AI Categorization"),
        ("4", "step_4_ai.py", "AI Enrichment"),
        ("5", "step_5_upload.py", "Upload to CMS"),
    ]

    # Convert stop_after to comparable value
    stop_after_val = float(args.stop_after)

    for step_num, script, title in steps:
        if float(step_num) > stop_after_val:
            break

        success, msg = run_script(step_num, script, title, args.verbose)
        results.append((step_num, success, msg))

        if not success:
            print(f"\nStopping pipeline due to step {step_num} failure")
            break

    # Print summary
    outputs = check_output_files()
    print_summary(results, outputs)

    # Exit code: 0 if all ran steps succeeded
    all_succeeded = all(success for _, success, _ in results)
    return 0 if all_succeeded else 1


if __name__ == "__main__":
    sys.exit(main())
