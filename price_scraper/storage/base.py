from abc import ABC, abstractmethod
import logging
from typing import List

from price_scraper.models import ProductPrice, ProductMetadata


logger = logging.getLogger()


class BaseStorage(ABC):
    """This is a base repository to save a new entry of product to the
    storage class of choice, or retrieve the data from storage.

    This repository pattern is built to support various storage options and changes
    to storage option down the road, if needed.
    """

    @abstractmethod
    def save(
        self,
        product_prices: List[ProductPrice],
        product_metadata: List[ProductMetadata],
    ):
        """This method stores product information to the storage.

        Args:
            product_prices: The list of product prices.
            product_metadata: The list of product metadata.
        """
        raise NotImplementedError
