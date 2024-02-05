from datetime import date
import uuid
from typing import Any

from sqlalchemy import (
    Column,
    Date,
    Enum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
)
from sqlalchemy.orm import declarative_base, relationship

from price_scraper.enums import Retailer

# Define a Base
Base: Any = declarative_base()


class ProductMetadata(Base):
    """This class contains metadata associated with the product.

    Args:
        product_id: The product id given by the retailer, prepended with retailer enum name for
            uniqueness.
        retailer: The enum of a supported retailer website.
        brand: The brand of product.
        category: The category tree of the product. Provided as a string separated by slash.
            Example: "Electronics/Computers&Accessories/Computers&Tablets/Laptops"
        title: The title of product. Can be used to cross reference products from
            different Retailer.
        additional_attributes: other metadata related to the product, e.g. SKU.
            this is free form field and may differ from retailer to another one.
    """

    __tablename__ = "product_metadata"

    product_id = Column(String, primary_key=True)
    retailer = Column(Enum(Retailer), nullable=False)
    brand = Column(String, nullable=False)
    category = Column(String, nullable=False)
    title = Column(String, nullable=True)
    additional_attributes = Column(JSON, nullable=True)


class ProductPrice(Base):
    """An actual time slice of product data scraped at a give date.

    Args:
        id: table row identifier.
        product_id: The unique identifier of product.
        date: Actual date of product data being scraped.
        buy_price: Actual price to pay at a given date for the product.
        original_price: Original price marked by retailer at a given date.
        coupon_value: If a retailer offering a dollar value coupon for the product at a given date.
        rating: The rating of product on retailer website at a given date.
        review_count: The number of reviews a certain product has at a given date.
    """

    __tablename__ = "product_price"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id = Column(
        String, ForeignKey("product_metadata.product_id"), nullable=False
    )
    date = Column(Date, nullable=False, default=lambda: date.today())
    buy_price = Column(Float, nullable=True)
    original_price = Column(Float, nullable=True)
    coupon_value = Column(Float, nullable=True)
    rating = Column(Float, nullable=True)
    review_count = Column(Integer, nullable=True)

    product_metadata = relationship("ProductMetadata")
