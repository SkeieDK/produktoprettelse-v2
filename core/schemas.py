"""
Pydantic data models for produktoprettelse-v2.

Provides schema validation at pipeline step boundaries with fail-fast behavior.
These models ensure data consistency as products flow through the pipeline:

Step 1 (Sanitize)  -> ProcessedProduct
Step 2 (Scrape)    -> EnrichedProduct
Step 3 (Images)    -> EnrichedProduct (updated)
Step 3.5 (Cat.)    -> CategorizedProduct
Step 4 (AI)        -> FinalProduct
Step 5 (Upload)    -> FinalProduct (consumed)

Usage:
    from core.schemas import ProcessedProduct, validate_products

    # Validate a list of products
    valid_products = validate_products(raw_data, ProcessedProduct)

    # Validate a single product
    product = ProcessedProduct(**raw_dict)
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Type, TypeVar, Union
from pydantic import BaseModel, Field, field_validator, model_validator
import logging

from .errors import ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


# =============================================================================
# Base Models
# =============================================================================


class BaseProduct(BaseModel):
    """Base product model with common fields."""

    PROD_NUM: str = Field(..., description="Product number (primary identifier)")
    PROD_NUM_old: Optional[str] = Field(None, description="Original/old product number")
    ORIGINAL_PROD_NAME: Optional[str] = Field(None, description="Original product name")

    class Config:
        extra = "allow"  # Allow extra fields not in schema
        str_strip_whitespace = True

    @field_validator("PROD_NUM", mode="before")
    @classmethod
    def validate_prod_num(cls, v: Any) -> str:
        if v is None:
            raise ValueError("PROD_NUM cannot be None")
        v = str(v).strip()
        if not v:
            raise ValueError("PROD_NUM cannot be empty")
        # Strip " - DEAKTIVERET" suffix if present
        if " - DEAKTIVERET" in v:
            v = v.replace(" - DEAKTIVERET", "").strip()
        return v


class PriceEntry(BaseModel):
    """Model for a price entry."""

    unitPrice: Optional[float] = None
    specialOfferPrice: Optional[float] = None
    b2bGroupId: Optional[Union[str, int]] = None
    quantity: Optional[int] = 1
    currencyCode: Optional[str] = "DKK"

    class Config:
        extra = "allow"


class CategoryInfo(BaseModel):
    """Model for category information."""

    category_id: Optional[str] = Field(None, alias="PROD_CAT_ID")
    category_number: Optional[str] = None
    category_name: Optional[str] = Field(None, alias="nederste_kategori")
    parent_ids: Optional[List[str]] = None
    confidence: Optional[float] = None

    class Config:
        extra = "allow"
        populate_by_name = True


class AICategorizationResult(BaseModel):
    """Model for AI categorization results."""

    primary_category_id: Optional[str] = None
    primary_category_name: Optional[str] = None
    confidence_score: Optional[float] = None
    fallback_used: bool = False
    embedding_matches: Optional[List[Dict[str, Any]]] = None

    class Config:
        extra = "allow"


# =============================================================================
# Pipeline Step Models
# =============================================================================


class ProcessedProduct(BaseProduct):
    """
    Product after Step 1 (Sanitize).

    Required fields from CSV sanitization.
    """

    PROD_NAME: Optional[str] = None
    PROD_COST_PRICE: Optional[float] = None
    SUPPLIER_ID: Optional[str] = None
    SUPPLIER_NAME: Optional[str] = None
    PROD_UNIT: Optional[str] = None
    PURCHASE_UNIT: Optional[str] = None
    Retail_Price: Optional[float] = None

    @field_validator("PROD_COST_PRICE", mode="before")
    @classmethod
    def validate_cost_price(cls, v: Any) -> Optional[float]:
        if v is None:
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None


class EnrichedProduct(ProcessedProduct):
    """
    Product after Step 2 (Scrape) and Step 3 (Images).

    Adds supplier info and image paths from web scraping.
    """

    supplier_info: Optional[str] = Field(None, description="Scraped product info from supplier website")
    supplier_images: Optional[List[str]] = Field(default_factory=list, description="URLs to supplier images")
    images: Optional[List[str]] = Field(default_factory=list, description="Local image paths")
    pdf_path: Optional[str] = Field(None, description="Path to product PDF")
    scrape_status: Optional[str] = Field(None, description="Status of scraping operation")
    scrape_error: Optional[str] = Field(None, description="Error message if scraping failed")


class CategorizedProduct(EnrichedProduct):
    """
    Product after Step 3.5 (Categorize).

    Adds AI-determined category assignment.
    """

    ai_categorization: Optional[AICategorizationResult] = Field(
        None, description="AI categorization results"
    )
    primaryCategoryId: Optional[str] = Field(None, description="Selected primary category ID")
    PROD_CAT_ID: Optional[str] = Field(None, description="Category ID for upload")
    category_path: Optional[str] = Field(None, description="Full category hierarchy path")


class FinalProduct(CategorizedProduct):
    """
    Product after Step 4 (AI Generate).

    Adds AI-generated descriptions and final content.
    """

    AI_description_short: Optional[str] = Field(None, description="AI-generated short description")
    AI_description_long: Optional[str] = Field(None, description="AI-generated long description")
    AI_bullet_points: Optional[List[str]] = Field(default_factory=list, description="AI-generated bullet points")
    AI_meta_title: Optional[str] = Field(None, description="AI-generated SEO title")
    AI_meta_description: Optional[str] = Field(None, description="AI-generated SEO description")
    AI_generation_cost: Optional[float] = Field(None, description="Cost of AI generation in USD")
    AI_model_used: Optional[str] = Field(None, description="AI model used for generation")
    processing_status: Optional[str] = Field("pending", description="Overall processing status")
    processed_at: Optional[datetime] = Field(None, description="Timestamp of processing")


# =============================================================================
# Validation Functions
# =============================================================================


def validate_product(
    data: Dict[str, Any],
    model: Type[T],
    raise_on_error: bool = True,
) -> Optional[T]:
    """
    Validate a single product dictionary against a Pydantic model.

    Args:
        data: Raw product dictionary
        model: Pydantic model class to validate against
        raise_on_error: If True, raises ValidationError on failure

    Returns:
        Validated model instance, or None if validation fails and raise_on_error=False

    Raises:
        ValidationError: If validation fails and raise_on_error=True

    Example:
        product = validate_product(raw_dict, ProcessedProduct)
    """
    try:
        return model(**data)
    except Exception as e:
        prod_num = data.get("PROD_NUM", "UNKNOWN")
        msg = f"Validation failed for product {prod_num}: {e}"

        if raise_on_error:
            raise ValidationError(
                msg,
                field="product",
                value=prod_num,
                details={"errors": str(e)},
            ) from e

        logger.warning(msg)
        return None


def validate_products(
    data: List[Dict[str, Any]],
    model: Type[T],
    raise_on_error: bool = True,
    skip_invalid: bool = False,
) -> List[T]:
    """
    Validate a list of products against a Pydantic model.

    Args:
        data: List of raw product dictionaries
        model: Pydantic model class to validate against
        raise_on_error: If True, raises ValidationError on first failure
        skip_invalid: If True and raise_on_error=False, skip invalid products

    Returns:
        List of validated model instances

    Raises:
        ValidationError: If validation fails and raise_on_error=True

    Example:
        products = validate_products(raw_list, ProcessedProduct)
        products = validate_products(raw_list, EnrichedProduct, skip_invalid=True)
    """
    validated = []
    errors = []

    for i, item in enumerate(data):
        try:
            validated.append(model(**item))
        except Exception as e:
            prod_num = item.get("PROD_NUM", f"index_{i}")
            error_info = {"index": i, "prod_num": prod_num, "error": str(e)}
            errors.append(error_info)

            if raise_on_error:
                raise ValidationError(
                    f"Validation failed for product {prod_num} at index {i}: {e}",
                    field="products",
                    value=prod_num,
                    details={"errors": errors},
                ) from e

            if not skip_invalid:
                logger.warning(f"Invalid product at index {i} ({prod_num}): {e}")

    if errors and not skip_invalid:
        logger.warning(f"Validation completed with {len(errors)} errors out of {len(data)} products")

    return validated


def products_to_dicts(products: List[BaseModel]) -> List[Dict[str, Any]]:
    """
    Convert a list of Pydantic models back to dictionaries.

    Args:
        products: List of Pydantic model instances

    Returns:
        List of dictionaries

    Example:
        dicts = products_to_dicts(validated_products)
        save_json("output.json", dicts)
    """
    return [p.model_dump(exclude_none=False) for p in products]
