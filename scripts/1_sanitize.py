#!/usr/bin/env python3
"""
Step 1: CSV Sanitization
Reads a CSV from data/input/, applies transformations, and writes:
  - data/output/<stem>_sanitized.csv
  - data/cache/processed_products.json

Usage:
  python scripts/1_sanitize.py [input_csv]
  
  If no input_csv provided, processes the latest file in data/input/
"""

import sys
import logging
from pathlib import Path
import pandas as pd

# Add project root to path so we can import csv_data_transformation
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# Use core utilities (consolidated from multiple implementations)
from core.config import load_config
from core.logging import setup_logging
from core.file_utils import save_json

from csv_data_transformation.sanitering import CSVSanitering

def find_latest_csv(input_dir: Path) -> Path:
    """Find the most recent CSV file in input directory"""
    csv_files = list(input_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {input_dir}")
    
    # Sort by modification time, newest first
    csv_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return csv_files[0]

def main():
    # Load config (returns AppConfig dataclass)
    config = load_config()
    
    # Set up directories using typed config
    input_dir = config.paths.input_dir
    output_dir = config.paths.output_dir
    cache_dir = config.paths.cache_dir
    logs_dir = config.paths.logs_dir
    products_cache_path = config.paths.products_cache
    
    # Create directories
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Set up logging
    logger = setup_logging(logs_dir, "1_sanitize")
    
    logger.info("=" * 60)
    logger.info("Step 1: CSV Sanitization")
    logger.info("=" * 60)
    
    # Determine input CSV
    if len(sys.argv) > 1:
        input_csv = Path(sys.argv[1])
        if not input_csv.is_absolute():
            input_csv = PROJECT_ROOT / input_csv
    else:
        logger.info(f"No input file specified, finding latest in {input_dir}")
        input_csv = find_latest_csv(input_dir)
    
    if not input_csv.exists():
        logger.error(f"Input file not found: {input_csv}")
        sys.exit(1)
    
    logger.info(f"Input CSV: {input_csv}")
    
    # Read CSV
    try:
        df = pd.read_csv(input_csv)
        logger.info(f"Loaded {len(df)} rows, {len(df.columns)} columns")
    except Exception as e:
        logger.error(f"Failed to read CSV: {e}")
        sys.exit(1)
    
    # Process with existing sanitization logic
    try:
        sanitizer = CSVSanitering(df)
        
        # Get products cache path from config
        if not products_cache_path.exists():
            logger.warning(f"Products cache not found: {products_cache_path}")
            logger.warning("Will start from E100000 for PROD_NUM")
        
        processed_df = sanitizer.process(cache_path=str(products_cache_path))
        logger.info(f"Processing complete: {len(processed_df)} products")
        
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        sys.exit(1)
    
    # Write outputs
    try:
        # 1. Sanitized CSV
        output_csv = output_dir / f"{input_csv.stem}_sanitized.csv"
        processed_df.to_csv(output_csv, index=False, encoding='utf-8')
        logger.info(f"✓ Sanitized CSV: {output_csv}")
        
        # 2. JSON output (main location: output_dir)
        json_output = output_dir / f"{input_csv.stem}_processed.json"
        records = sanitizer.to_records()
        save_json(json_output, records, atomic=True)
        logger.info(f"✓ JSON output: {json_output}")
        
        # 3. Also copy to cache for backward compatibility with Step 2 & 3
        cache_json = cache_dir / "processed_products.json"
        save_json(cache_json, records, atomic=True)
        logger.info(f"✓ Cache copy: {cache_json}")
        
    except Exception as e:
        logger.error(f"Failed to write outputs: {e}", exc_info=True)
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("✓ Step 1 complete")
    logger.info(f"  Processed: {len(processed_df)} products")
    logger.info(f"  Output CSV: {output_csv}")
    logger.info(f"  JSON: {json_output}")
    logger.info("=" * 60)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
