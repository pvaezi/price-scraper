from enum import Enum
from pydoc import locate


class BaseEnum(Enum):
    """The base enum for shared functionality."""

    @classmethod
    def __getitem__(cls, name):
        if name not in cls.__members__:
            acceptable_values = ", ".join(cls.__members__.keys())
            raise ValueError(
                f"No such enum: {name}. Supported enum are: {acceptable_values}"
            )
        return super().__getitem__(name)

    @classmethod
    def __get_validators__(cls):
        cls.lookup = {v: k.value for v, k in cls.__members__.items()}
        yield cls.validate

    def load(self):
        """Loads the class associated with module path in the enum value."""
        return locate(self.value)

    @classmethod
    def validate(cls, v, *args):
        try:
            return cls.lookup[v]
        except KeyError:
            raise ValueError("invalid value")


class Retailer(BaseEnum):
    """The enumerated values of retailers supported at the moment."""

    BASE = "price_scraper.retailer.BaseRetailer"
    AMZ = "price_scraper.retailer.Amazon"
    BBY = "price_scraper.retailer.BestBuy"


class StorageType(BaseEnum):
    """The enumerated values of supported storage type at the moment."""

    S3 = "price_scraper.storage.s3.S3Storage"
    POSTGRES = "price_scraper.storage.postgres.PostgresStorage"
