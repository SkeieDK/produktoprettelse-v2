"""
AI Module Package

Contains AI-related functionality:
- agents: Writer/Reviewer agent classes
- config: Model configuration, pricing, prompts
- categorize_helpers: Category prompt building utilities
"""

from .config import (
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
