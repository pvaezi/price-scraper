from datetime import date
import logging
from typing import List

import boto3
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from price_scraper.enums import Retailer
from price_scraper.storage.base import BaseStorage
from price_scraper.models import Base, ProductPrice, ProductMetadata


logger = logging.getLogger()


class S3Storage(BaseStorage):
    """This is a low cost analytical query based storage option to store product information
    on S3 bucket for future analysis and modeling.
    In this storage, product data is stored as a nested category format and as parquet file.

    Args:
        bucket_and_prefix: The bucket and prefix to use for storing scraped data.
        region: S3 client region.
    """

    num_updated_product_metadata = 0

    def __init__(self, bucket_and_prefix: str, region: str):
        self.bucket_and_prefix = bucket_and_prefix
        # Creating in memory duck db database session
        # TODO persist better with .db file.
        engine = create_engine("duckdb:///:memory:")
        Session = sessionmaker(bind=engine)
        self.session = Session()
        # Register table models to the engine
        Base.metadata.create_all(engine)
        # Set S3 auth and region
        credentials = boto3.Session().get_credentials()
        self.session.execute(text("LOAD httpfs;"))
        self.session.execute(text(f"SET s3_region = '{region}';"))
        self.session.execute(
            text(f"SET s3_access_key_id = '{credentials.access_key}';")
        )
        self.session.execute(
            text(f"SET s3_secret_access_key = '{credentials.secret_key}';")
        )

    def save(
        self,
        product_prices: List[ProductPrice],
        product_metadata: List[ProductMetadata],
    ):
        if len(product_metadata) == 0:
            logger.warning("Nothing to store. Skipping save..")
            return

        category: str = product_metadata[0].category
        brand: str = product_metadata[0].brand
        retailer: Retailer = product_metadata[0].retailer
        dt: date = product_prices[0].date

        self._save_metadata(
            product_metadata=product_metadata,
            category=category,
            brand=brand,
        )
        self._save_prices(
            product_prices=product_prices,
            category=category,
            brand=brand,
            retailer=retailer,
            dt=dt,
        )

    def _save_metadata(
        self,
        category: str,
        brand: str,
        product_metadata: List[ProductMetadata],
    ):
        """This method stores or updates product metadata based on category and brand.

        Args:
            category: The list of category drill down for the product data that is scraped.
            brand: The name of product brand.
            product_metadata: The list of product metadata.
        """
        # Store product metadata scraped from the page
        logger.info("Fetching existing product metadata for category and brand..")
        meta_parquet_s3_path = (
            f"{self.bucket_and_prefix}/{category}/{brand}/metadata.parquet"
        )
        try:
            self.session.execute(
                text(
                    "INSERT INTO product_metadata "
                    f"SELECT * FROM read_parquet('{meta_parquet_s3_path}');"
                )
            )
            # Commit if successful
            self.session.commit()
            logger.info("Existing metadata loaded.")
        except SQLAlchemyError:
            self.session.rollback()
            logger.info(
                "No existing metadata for brand and category found, starting from scratch.."
            )
        try:
            # # Iterate through the list and use merge for each object
            for obj in product_metadata:
                self._update_or_insert_meta(obj)
            if self.num_updated_product_metadata == 0:
                logger.info(
                    "No product metadata is found to be different from before, "
                    "skipping storage write."
                )
                return
            self.session.commit()
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.exception("Cannot commit product metadata to the db, error: %s", e)

        try:
            self.session.execute(
                text(
                    f"COPY product_metadata TO '{meta_parquet_s3_path}' (FORMAT PARQUET);"
                )
            )
            logger.info("Product metadata is stored to %s.", meta_parquet_s3_path)
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.exception("Failed to store product_metadata table to S3: %s", e)
        logger.info(
            "Stored product metadata, %d new product metadata updated.",
            self.num_updated_product_metadata,
        )

    def _save_prices(
        self,
        product_prices: List[ProductPrice],
        category: str,
        brand: str,
        retailer: Retailer,
        dt: date,
    ):
        logger.info("Storing product data..")
        data_parquet_s3_path = (
            f"{self.bucket_and_prefix}/{category}/{brand}/ts/"
            f"{dt.strftime('%Y/%m/%d')}/{retailer.name}.parquet"
        )
        try:
            self.session.add_all(product_prices)
            self.session.commit()
        except Exception as e:
            self.session.rollback()
            logger.exception("Failed to add new scraped data: %s", e)
        try:
            self.session.execute(
                text(
                    f"COPY product_price TO '{data_parquet_s3_path}' (FORMAT PARQUET);"
                )
            )
            self.session.commit()
            logger.info("Product data is stored to %s.", data_parquet_s3_path)
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.exception("Failed to store product data table to S3: %s", e)

    def _update_or_insert_meta(self, obj: ProductMetadata):
        """Updates or insert product metadata into db.

        Args:
            obj: New product metadata instance.
        """
        is_diff = False
        # get existing row
        existing_row = (
            self.session.query(ProductMetadata)
            .filter(ProductMetadata.product_id == obj.product_id)
            .first()
        )
        # update existing row if any changes from before, or insert new product metadata
        if existing_row:
            # If exists and different, update the existing row with object attributes
            for key, value in vars(obj).items():
                if (
                    # NOTE we don't care sqlalchemy attributes nor id which can change
                    # by uuid generation
                    key not in ["_sa_instance_state", "id"]
                    and value != getattr(existing_row, key)
                ):
                    setattr(existing_row, key, value)
                    is_diff = True
        else:
            # If doesn't exist, add object as a new row
            self.session.add(obj)
            is_diff = True
        # increase counter if a newly updated/found product
        if is_diff:
            self.num_updated_product_metadata += 1
