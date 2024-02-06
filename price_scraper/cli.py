import argparse
import json
import logging
import os
from typing import Any, Dict, List, TYPE_CHECKING

from pydantic import BaseModel, Field
from pydantic_core import PydanticUndefined

from price_scraper.enums import Retailer, StorageType
from price_scraper.retailer.base import BaseRetailer


logging_level = getattr(logging, os.environ.get("LOG_LEVEL", "INFO"))

# lambda runtime logging level set
if len(logging.getLogger().handlers) > 0:
    logging.getLogger().setLevel(logging_level)
# local interpreter logging config
else:
    logging.basicConfig(
        level=logging_level, format="%(asctime)s - %(levelname)s - %(message)s"
    )
logger = logging.getLogger()


class StorageOptions(BaseModel):
    """Storage schema provided by the user."""

    storage_type: StorageType = Field(
        ...,
        description=(
            "The type of storage to use, must be a valid "
            "StorageType enum supported by the library."
        ),
    )
    storage_options: Dict[str, Any] = Field(
        {}, description="The keyword argument of specific StorageType class."
    )


class PriceScraperSchema(BaseModel):
    """Schema for PriceScraper CLI."""

    retailer: Retailer = Field(
        ...,
        description="The retailer enum. Must be valid Retailer enum supported by the library.",
    )
    url: str = Field(
        ...,
        description=(
            "URL of page to scrape. URL must contain all elements "
            "dedicated to a certain brand and category."
        ),
    )
    category: str = Field(
        ...,
        description=(
            "The name of category the page is for. "
            "Currently assumes the list of products all belong "
            "to a specific category. Category string can be nested separated by '/'."
        ),
    )
    brand: str = Field(
        ...,
        description=(
            "The name of brand the page is for. "
            "Currently assumes the list of products all belong "
            "to a specific brand."
        ),
    )
    storage_config: List[StorageOptions] = Field(
        ...,
        description=(
            "The storage class and config to use, "
            "must have storage_class key with StorageType enum value, "
            "and optionally can have storage_kwargs for storage_cls configuration. "
            "User can configure multiple storage as part of writing scarped data."
        ),
    )
    proxy_config: dict = Field(
        {},
        description="Selenium Firefox proxy configuration given as key value pair.",
    )
    timeout: int = Field(
        30, description="Web loading timeout in seconds.", required=False
    )

    @classmethod
    def create_arg_parser(cls) -> argparse.Namespace:
        parser = argparse.ArgumentParser(
            description="Scrape a given retail website page for its product prices and reviews."
        )
        for field_name, field in cls.model_fields.items():
            kwargs = {}
            # import pdb; pdb.set_trace()
            type_ = field.annotation
            default = field.default
            # if a List type hint make necessary adjustments
            if (
                hasattr(field.annotation, "__origin__")
                and field.annotation.__origin__ == list
            ):
                kwargs.update({"nargs": "+"})
                type_ = field.annotation.__args__[0]
            if default != PydanticUndefined:
                kwargs.update({"default": default})
            # NOTE anything non int, bool, float would be treated as string input in the CLI
            if type_ not in (int, float, bool):
                type_ = str
                if kwargs.get("default") is not None:
                    default = str(default)
                    kwargs.update({"default": default})
            parser.add_argument(
                f"--{field_name.replace('_', '-')}",
                type=type_,
                required=field.is_required(),
                help=field.description,
                **kwargs,
            )
        return parser.parse_args()


def scrape(event: PriceScraperSchema, **kwargs) -> BaseRetailer:
    """The handler processing scraping event.

    Args:
        event: input scraping schema provided by the user.
    """
    scraper: BaseRetailer = Retailer(event.retailer).load()(
        category=event.category.strip("/"),
        brand=event.brand.lower(),
        timeout=event.timeout,
        proxy_kwargs=event.proxy_config,
        **kwargs,
    )
    # scrape product data
    try:
        scraper.paginate_and_scrape(event.url)
        logger.info("Scraped %d products.", len(scraper.product_prices))
    finally:
        scraper.close()
    return scraper


def store(scraper: BaseRetailer, event: PriceScraperSchema, **kwargs):
    """The handler processing storing scraped data.

    Args:
        scraper: The scraper class for the retailer that contains scraped products.
        event: input scraping schema provided by the user.
    """
    # store product data
    for storage_config in event.storage_config:
        try:
            storage = StorageType(storage_config.storage_type).load()(
                **storage_config.storage_options
            )
            storage.save(
                product_prices=scraper.product_prices,
                product_metadata=scraper.product_metadata,
            )
            logger.info("Finished storing data into %s.", storage.__class__.__name__)
            storage.session.close()
        except Exception as err:
            logger.error(
                "Error on storing data to %s: %s", storage.__class__.__name__, err, exc_info=True
            )


def main():
    """The entry function to the CLI."""
    args = PriceScraperSchema.create_arg_parser()
    event = PriceScraperSchema(
        retailer=args.retailer,
        url=args.url,
        category=args.category,
        brand=args.brand,
        storage_config=[json.loads(conf) for conf in args.storage_config],
        proxy_config=json.loads(args.proxy_config),
        timeout=args.timeout,
    )
    scraper = scrape(event=event)
    store(scraper=scraper, event=event)


if __name__ == "__main__":
    main()
