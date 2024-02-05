import logging
import os
from typing import List

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import Index

from price_scraper.storage.base import BaseStorage
from price_scraper.models import Base, ProductPrice, ProductMetadata


logger = logging.getLogger()


class PostgresStorage(BaseStorage):
    """This is postgres database storage to store scraped data into structured table.
    We use this storage class to store scraped data into transactional store for any real time
    needs, e.g. web serving.

    Args:
        postgres_url: The url of postgres host.
        postgres_port: The port for connecting to postgres.
        database_name: name of database.
    """

    def __init__(
        self,
        postgres_url: str = "postgres-postgresql",
        postgres_port: int = 5432,
        database_name: str = "postgres",
    ):
        # define postgres table indecies for efficient queries at read
        Index(
            "idx_product_price_date_product_id",
            ProductPrice.date,
            ProductPrice.product_id,
        )
        Index("idx_product_price_product_id", ProductPrice.product_id)
        Index("idx_product_metadata_category", ProductMetadata.category)
        Index("idx_product_metadata_brand", ProductMetadata.brand)
        # Connect to the database
        engine = create_engine(
            "postgresql+psycopg2://"
            # NOTE postgres username and password are passed via env vars for security
            f"{os.environ['POSTGRES_USER']}:{os.environ['POSTGRES_PASSWORD']}"
            f"@{postgres_url}:{postgres_port}/{database_name}"
        )
        Session = sessionmaker(bind=engine)
        self.session = Session()
        # Register table models to the engine
        Base.metadata.create_all(engine)

    def save(
        self,
        product_prices: List[ProductPrice],
        product_metadata: List[ProductMetadata],
    ):
        """This method stores or updates product metadata based on category and brand.

        Args:
            product_metadata: The list of product metadata.
        """
        try:
            # Iterate through the list and use merge for each object
            for obj in product_metadata:
                self.session.merge(obj)
            self.session.add_all(product_prices)
            self.session.commit()
            logger.info(
                "Success: %d product are added to the database.",
                len(product_metadata),
            )
        except SQLAlchemyError as e:
            self.session.rollback()
            logger.exception("Cannot commit product to the db, error: %s", e)
