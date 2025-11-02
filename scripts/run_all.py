#!/usr/bin/env python3
"""
Produktoprettelse-v2: Complete Pipeline Orchestrator

Runs all 4 steps of the product enrichment pipeline:
  1. Sanitize CSV input
  2. Scrape supplier information
  3. Process and organize images
  4. Generate AI descriptions

Features:
  - Run all steps or stop after any step (--stop-after flag)
  - Pretty progress output with rich
  - Verbose logging option
  - Summary of all outputs
  - Exit codes for automation/scripting

Usage:
  python scripts/run_all.py                    # Run all 4 steps
  python scripts/run_all.py --stop-after 2    # Run steps 1-2
  python scripts/run_all.py --verbose          # Show detailed logs
  python scripts/run_all.py --help             # Show options
"""

import subprocess
import sys
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import Tuple, Optional

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Warning: 'rich' not installed. Using basic output.")
    print("Install with: pip install rich")


# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
LOGS_DIR = PROJECT_ROOT / "logs"
DATA_OUTPUT = PROJECT_ROOT / "data" / "output"

# Rich console (or fallback)
console = Console() if RICH_AVAILABLE else None


def print_header():
    """Print pipeline header."""
    if RICH_AVAILABLE:
        console.print("\n")
        console.print(Panel(
            "[bold cyan]Produktoprettelse-v2 Pipeline[/bold cyan]\n"
            "[dim]Complete product enrichment workflow[/dim]",
            expand=False,
            border_style="cyan"
        ))
    else:
        print("\n" + "=" * 60)
        print("Produktoprettelse-v2 Pipeline")
        print("Complete product enrichment workflow")
        print("=" * 60 + "\n")


def print_step(step_num: int, title: str, description: str):
    """Print step header."""
    if RICH_AVAILABLE:
        console.print(f"\n[bold yellow]Step {step_num}: {title}[/bold yellow]")
        console.print(f"[dim]{description}[/dim]")
    else:
        print(f"\n--- Step {step_num}: {title} ---")
        print(f"{description}\n")


def run_script(step_num: int, script_name: str, title: str, verbose: bool = False) -> Tuple[bool, str]:
    """
    Run a step script and return (success, output_summary).
    
    Args:
        step_num: Step number (1-4)
        script_name: Script filename (e.g., "1_sanitize.py")
        title: Display title
        verbose: Show all output to console
    
    Returns:
        (success: bool, summary: str)
    """
    script_path = SCRIPTS_DIR / script_name
    
    if not script_path.exists():
        error_msg = f"Script not found: {script_path}"
        if RICH_AVAILABLE:
            console.print(f"[red]✗ {error_msg}[/red]")
        else:
            print(f"ERROR: {error_msg}")
        return False, error_msg
    
    print_step(step_num, title, f"Running {script_name}...")
    
    try:
        if RICH_AVAILABLE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True
            ) as progress:
                task = progress.add_task(f"Processing...", total=None)
                
                if verbose:
                    result = subprocess.run(
                        [sys.executable, str(script_path)],
                        cwd=PROJECT_ROOT,
                        check=True
                    )
                else:
                    result = subprocess.run(
                        [sys.executable, str(script_path)],
                        cwd=PROJECT_ROOT,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    # Print last few lines of output
                    if result.stdout:
                        lines = result.stdout.strip().split('\n')
                        for line in lines[-5:]:
                            console.print(f"  [dim]{line}[/dim]")
        else:
            result = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=PROJECT_ROOT,
                check=True
            )
        
        if RICH_AVAILABLE:
            console.print(f"[green]✓ Step {step_num} complete[/green]")
        else:
            print(f"✓ Step {step_num} complete")
        
        return True, f"Step {step_num} succeeded"
        
    except subprocess.CalledProcessError as e:
        error_msg = f"Step {step_num} failed with exit code {e.returncode}"
        if RICH_AVAILABLE:
            console.print(f"[red]✗ {error_msg}[/red]")
            if e.stderr:
                console.print(f"[red]{e.stderr}[/red]")
        else:
            print(f"ERROR: {error_msg}")
            if e.stderr:
                print(e.stderr)
        return False, error_msg
    
    except Exception as e:
        error_msg = f"Step {step_num} error: {e}"
        if RICH_AVAILABLE:
            console.print(f"[red]✗ {error_msg}[/red]")
        else:
            print(f"ERROR: {error_msg}")
        return False, error_msg


def check_output_files() -> dict:
    """Check which output files exist."""
    return {
        "sanitized_csv": bool(list(DATA_OUTPUT.glob("*_sanitized.csv"))),
        "processed_json": bool((DATA_OUTPUT / "processed_products.json").exists()),
        "supplier_info": (DATA_OUTPUT / "supplier_info.json").exists(),
        "enriched_products": (DATA_OUTPUT / "enriched_products.json").exists(),
        "images_dir": (DATA_OUTPUT / "images").exists(),
        "final_products": (DATA_OUTPUT / "final_products.json").exists(),
    }


def print_summary(stop_after: int, results: list, outputs: dict):
    """Print final summary."""
    if RICH_AVAILABLE:
        console.print("\n")
        
        # Results table
        table = Table(title="Pipeline Results", expand=False)
        table.add_column("Step", style="cyan")
        table.add_column("Status", style="green")
        
        for i, (success, msg) in enumerate(results, 1):
            if success:
                table.add_row(f"Step {i}", "[green]✓ Success[/green]")
            else:
                table.add_row(f"Step {i}", "[red]✗ Failed[/red]")
        
        console.print(table)
        
        # Output files table
        output_table = Table(title="Output Files", expand=False)
        output_table.add_column("File", style="cyan")
        output_table.add_column("Status", style="green")
        
        for name, exists in outputs.items():
            status = "[green]✓[/green]" if exists else "[dim]—[/dim]"
            output_table.add_row(name, status)
        
        console.print(output_table)
        
        # Summary panel
        successful = sum(1 for success, _ in results if success)
        console.print(Panel(
            f"[bold]{successful}/{len(results)} steps completed successfully[/bold]\n"
            f"Output directory: [cyan]{DATA_OUTPUT}[/cyan]",
            expand=False,
            border_style="green" if successful == len(results) else "yellow"
        ))
    else:
        print("\n" + "=" * 60)
        print("PIPELINE SUMMARY")
        print("=" * 60)
        for i, (success, msg) in enumerate(results, 1):
            status = "✓ Success" if success else "✗ Failed"
            print(f"Step {i}: {status}")
        print("\nOutput files:")
        for name, exists in outputs.items():
            status = "✓" if exists else "—"
            print(f"  {status} {name}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run the Produktoprettelse-v2 pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                        Run all 4 steps
  %(prog)s --stop-after 2         Run steps 1-2 only
  %(prog)s --verbose              Show detailed output
  %(prog)s --stop-after 1 --verbose  Step 1 with details
        """
    )
    
    parser.add_argument(
        "--stop-after",
        type=int,
        default=4,
        choices=[1, 2, 3, 4],
        help="Stop after this step (default: 4 = all steps)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output from each step"
    )
    
    parser.add_argument(
        "--no-rich",
        action="store_true",
        help="Disable rich formatting (use plain text)"
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
        if console:
            console.print("[red]✗ No CSV files found in data/input/[/red]")
        else:
            print("ERROR: No CSV files found in data/input/")
        return 1
    
    # Run steps
    results = []
    steps = [
        (1, "1_sanitize.py", "CSV Sanitization"),
        (2, "2_scrape.py", "Supplier Scraping"),
        (3, "3_process_images.py", "Image Processing"),
        (4, "4_generate_ai.py", "AI Enrichment"),
    ]
    
    for step_num, script, title in steps:
        if step_num > args.stop_after:
            break
        
        success, msg = run_script(step_num, script, title, args.verbose)
        results.append((success, msg))
        
        if not success:
            if console:
                console.print(f"\n[red]Stopping pipeline due to step {step_num} failure[/red]")
            else:
                print(f"\nStopping pipeline due to step {step_num} failure")
            break
    
    # Print summary
    outputs = check_output_files()
    print_summary(args.stop_after, results, outputs)
    
    # Exit code: 0 if all ran steps succeeded
    all_succeeded = all(success for success, _ in results)
    return 0 if all_succeeded else 1


if __name__ == "__main__":
    sys.exit(main())
