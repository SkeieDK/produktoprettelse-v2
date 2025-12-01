"""
Pricing CLI Package

Command-line tools for batch price/offer operations:
- prepare: Build operations JSON without calling API
- apply: Execute operations from JSON file

Usage:
    python -m pricing.cli.prepare --input products.json --output ops.json --action create --price 79.95
    python -m pricing.cli.apply --ops ops.json
    python -m pricing.cli.apply --ops ops.json --dry-run
"""
