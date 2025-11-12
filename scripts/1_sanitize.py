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
import os
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd
import json
import numpy as np
import yaml

# Add project root to path so we can import csv_data_transformation
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from csv_data_transformation.sanitering import CSVSanitering

# Safe stream for console output (handles encoding errors)
class SafeStream:
    def __init__(self):
        self.encoding = 'utf-8'
    
    def write(self, msg):
        if not msg:
            return
        try:
            sys.__stdout__.write(msg)
        except UnicodeEncodeError:
            try:
                safe_msg = msg.encode('utf-8', errors='replace').decode(sys.__stdout__.encoding or 'utf-8', errors='replace')
                sys.__stdout__.write(safe_msg)
            except Exception:
                try:
                    safe_msg = msg.encode('ascii', errors='replace').decode('ascii')
                    sys.__stdout__.write(safe_msg)
                except Exception:
                    pass
    
    def flush(self):
        try:
            sys.__stdout__.flush()
        except Exception:
            pass
    
    def isatty(self):
        return sys.__stdout__.isatty() if hasattr(sys.__stdout__, 'isatty') else False

class SafeStreamHandler(logging.StreamHandler):
    """Custom logging handler that prevents encoding errors"""
    def emit(self, record):
        try:
            msg = self.format(record)
            self.stream.write(msg)
            self.stream.write('\n')
            self.stream.flush()
        except Exception:
            self.handleError(record)

def setup_logging(log_dir: Path):
    """Configure logging to file and console"""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "1_sanitize.log"
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler (UTF-8, no rotation for now)
    file_handler = logging.FileHandler(log_file, encoding='utf-8', mode='a')
    file_handler.setFormatter(formatter)
    
    # Console handler with SafeStream
    console_handler = SafeStreamHandler(SafeStream())
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def load_config(config_path: Path) -> dict:
    """Load config.yaml"""
    if not config_path.exists():
        logging.warning(f"Config file not found: {config_path}, using defaults")
        return {}
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def find_latest_csv(input_dir: Path) -> Path:
    """Find the most recent CSV file in input directory"""
    csv_files = list(input_dir.glob("*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {input_dir}")
    
    # Sort by modification time, newest first
    csv_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return csv_files[0]

def main():
    # Load config
    config_path = PROJECT_ROOT / "config.yaml"
    config = load_config(config_path)
    paths = config.get('paths', {})
    
    # Set up directories
    input_dir = PROJECT_ROOT / paths.get('input_dir', 'data/input')
    output_dir = PROJECT_ROOT / paths.get('output_dir', 'data/output')
    cache_dir = PROJECT_ROOT / paths.get('cache_dir', 'data/cache')
    logs_dir = PROJECT_ROOT / paths.get('logs_dir', 'logs')
    
    # Create directories
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Set up logging
    logger = setup_logging(logs_dir)
    
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
        products_cache_path = PROJECT_ROOT / paths.get('products_cache', 'cache/products_cache.json')
        
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
        sanitizer.to_json(str(json_output))
        logger.info(f"✓ JSON output: {json_output}")
        
        # 3. Also copy to cache for backward compatibility with Step 2 & 3
        cache_json = cache_dir / "processed_products.json"
        sanitizer.to_json(str(cache_json))
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
