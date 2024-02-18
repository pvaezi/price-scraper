from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
import logging
import os
from typing import List, TYPE_CHECKING

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.firefox.options import Options

from price_scraper.enums import Retailer
from price_scraper.models import ProductPrice, ProductMetadata

if TYPE_CHECKING:
    from selenium.webdriver.remote.webelement import WebElement

logger = logging.getLogger()


class BaseRetailer(ABC):
    """This is base repository class to accommodate business logic for scraping different
    retailer websites.

    Args:
        brand: The brand of products being scraped.
        category: The drill down category of products being scraped as a list of string.
        timeout: Web page scraping timeout in seconds.

    Attributes:
        products: The list of product prices scraped from the retailer.
        product_metadata: The list of product metadata scraped from the retailer.
    """

    retailer: Retailer = Retailer.BASE

    def __init__(
        self,
        brand: str,
        category: str,
        timeout: int = 10,
        max_pagination: int = 20,
        proxy_kwargs: dict | None = None,
    ):
        self.timeout = timeout
        self.brand = brand
        self.category = category
        self.max_pagination = max_pagination
        self.product_prices: List[ProductPrice] = []
        self.product_metadata: List[ProductMetadata] = []

        logger.critical("Creating web browser driver..")
        if proxy_kwargs:
            webdriver.DesiredCapabilities.FIREFOX["proxy"] = proxy_kwargs
            logger.info("Configured proxy with following setting: %s", proxy_kwargs)
        firefox_options = Options()
        firefox_options.add_argument("--headless")
        firefox_options.set_preference("browser.cache.disk.enable", False)
        firefox_options.set_preference("browser.cache.memory.enable", False)
        firefox_options.set_preference("browser.cache.offline.enable", False)
        firefox_options.set_preference("network.http.use-cache", False)
        self.driver = webdriver.Firefox(
            service_log_path=os.devnull, options=firefox_options
        )
        self.driver.set_page_load_timeout(timeout)
        logger.info(
            "Web browser driver created with timeout set to %d seconds.", timeout
        )

    def close(self):
        """Closes scrapping session."""
        self.driver.quit()

    @staticmethod
    def get_product_additional_attributes(element: WebElement) -> dict | None:
        """Gets product additional attributes that may exist in the retailer page.

        Args:
            element: Product web element.
        """
        return None

    @staticmethod
    def get_product_buy_price(element: WebElement) -> float | None:
        """Gets product buying price.

        Args:
            element: Product web element.
        """
        return None

    @staticmethod
    def get_product_coupon_value(element: WebElement) -> float | None:
        """Gets product coupon value if any.

        Args:
            element: Product web element.
        """
        return None

    @abstractmethod
    def get_product_elements(self) -> List[WebElement]:
        """Parses the list of products of retailer web page.

        Returns:
            elements: List of products as web elements.
        """
        raise NotImplementedError

    @staticmethod
    @abstractmethod
    def get_product_id(element: WebElement) -> str | None:
        """Gets product unique identifier.

        Args:
            element: Product web element.
        """
        raise NotImplementedError

    @staticmethod
    def get_product_original_price(element: WebElement) -> float | None:
        """Gets product buying price.

        Args:
            element: Product web element.
        """
        return None

    @staticmethod
    def get_product_rating(element: WebElement) -> float | None:
        """Gets product rating.

        Args:
            element: Product web element.
        """
        return None

    @staticmethod
    def get_product_review_count(element: WebElement) -> int | None:
        """Gets number of reviews for the product.

        Args:
            element: Product web element.
        """
        return None

    @staticmethod
    def get_product_title(element: WebElement) -> str | None:
        """Gets product title name as written by retailer.

        Args:
            element: Product web element.
        """
        return None

    def paginate_and_scrape(self, url: str):
        """This method paginates the product pages and scrapes each page for product information.
        If subclass does not provide pagination logic, the base class assumes only a single page.

        NOTE pagination logic per retailer may differ, some would provide lazy loading buttons,
        some require hyperlinks and hard page reload for next page.

        Args:
            url: The input https URL in string format.
        """
        self.scrape_page(url)
        elements = self.get_product_elements()
        self.parse_products_information(elements)

    def parse_products_information(self, elements: List[WebElement]):
        """Goes through each product element and parse product element information using
        aux methods, and stores it product_prices and product_metadata attributes.

        Args:
            elements: The list of web element scraped from the page.
        """
        for element in elements:
            try:
                product_id = self.get_product_id(element)
                if not product_id:
                    logger.error("Cannot fetch product_id, skipping product..")
                    continue
                # prepend retailer enum to enforce cross retailer uniqueness
                product_id = f"{self.retailer.name}{product_id}"
                meta = ProductMetadata(
                    product_id=product_id,
                    retailer=self.retailer,
                    brand=self.brand,
                    category=self.category,
                    title=self.get_product_title(element),
                    additional_attributes=self.get_product_additional_attributes(
                        element
                    ),
                )
                price = ProductPrice(
                    product_id=product_id,
                    date=date.today(),
                    buy_price=self.get_product_buy_price(element),
                    original_price=self.get_product_original_price(element),
                    coupon_value=self.get_product_coupon_value(element),
                    rating=self.get_product_rating(element),
                    review_count=self.get_product_review_count(element),
                )
                logger.debug(
                    "Meta: %s -- Price: %s",
                    {k: v for k, v in vars(meta).items() if not k.startswith("_")},
                    {k: v for k, v in vars(price).items() if not k.startswith("_")},
                )
                self.product_metadata.append(meta)
                self.product_prices.append(price)
                logger.info("Scraped product id '%s'.", product_id)
            except Exception as e:
                logger.error(
                    "Something failed to create row entries from the product information, "
                    "error: %s",
                    e,
                    exc_info=True,
                )

    def scrape_page(self, url: str):
        """Scrape given page URL via Selenium.

        Args:
            url: The input https URL in string format.
        """
        logger.critical("Parsing '%s'..", url)
        try:
            self.driver.get(url)
        except TimeoutException:
            self.driver.execute_script("window.stop();")
