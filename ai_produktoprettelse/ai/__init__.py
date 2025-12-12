"""
AI Module Package

Contains AI-related functionality:
- agents: Writer/Reviewer agent classes
- config: Model configuration, pricing, prompts (from scripts/ai_config.py)
- categorize_helpers: Category prompt building utilities

NOTE: AI config is centralized in scripts/ai_config.py (single source of truth)
"""

import sys
from pathlib import Path

# Add scripts to path to import ai_config
_scripts_dir = Path(__file__).resolve().parent.parent.parent / "scripts"
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

# Import from canonical config location (scripts/ai_config.py)
from ai_config import (
    ENRICHMENT_PRIMARY_MODEL,
    ENRICHMENT_FALLBACK_MODEL,
    EMBEDDING_MODEL,
    CATEGORIZATION_FALLBACK_MODEL,
    REVIEWER_MODEL,
    PRICING,
    calculate_cost,
    get_model_config,
    get_system_prompt,
    get_user_prompt,
    ProductDescriptionAgent,
)

from .agents import (
    BaseAgent,
    WriterAgent,
    ReviewerAgent,
)

from .categorize_helpers import (
    get_category_system_prompt,
    get_category_user_prompt,
    build_category_tree,
)

__all__ = [
    # config
    "ENRICHMENT_PRIMARY_MODEL",
    "ENRICHMENT_FALLBACK_MODEL",
    "EMBEDDING_MODEL",
    "CATEGORIZATION_FALLBACK_MODEL",
    "REVIEWER_MODEL",
    "PRICING",
    "calculate_cost",
    "get_model_config",
    "get_system_prompt",
    "get_user_prompt",
    "ProductDescriptionAgent",
    # agents
    "BaseAgent",
    "WriterAgent",
    "ReviewerAgent",
    # categorize_helpers
    "get_category_system_prompt",
    "get_category_user_prompt",
    "build_category_tree",
]
