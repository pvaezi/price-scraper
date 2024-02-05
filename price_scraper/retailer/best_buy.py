from __future__ import annotations

import logging
import re
from typing import List, TYPE_CHECKING

from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from price_scraper.enums import Retailer
from price_scraper.retailer.base import BaseRetailer

if TYPE_CHECKING:
    from selenium.webdriver.remote.webelement import WebElement


logger = logging.getLogger()


class BestBuy(BaseRetailer):
    """Scrapping BestBuy product list view pages for product price information.

    Attributes:
        retailer: The enum specified for the retailer
    """

    retailer = Retailer.BBY

    def paginate_and_scrape(self, url: str):
        """This method clicks on Show more button to load additional pages of data into the same
        page as part of pagination strategy.

        Args:
            url: The input https URL in string format.
        """
        super().scrape_page(url)
        WebDriverWait(self.driver, self.timeout).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, '[class^="{}"]'.format("footer"))
            )
        )
        try:
            num_pages = int(
                self.driver.find_element(
                    by=By.CSS_SELECTOR, value='[class^="{}"]'.format("paging-list")
                )
                .find_elements(
                    by=By.CSS_SELECTOR, value='[class^="{}"]'.format("page-item")
                )[-1]
                .text
            )
        except (NoSuchElementException, ValueError):
            logger.warning(
                "Could not extract the pagination section, assuming one page for product.."
            )
            num_pages = 1
        loop_break_counter = min(num_pages, self.max_pagination)
        logger.info(
            "Found %d pages to scrape, scraping up to %d pages..",
            num_pages,
            loop_break_counter,
        )
        page_num = 1
        while True:
            elements = self.get_product_elements()
            self.parse_products_information(elements)
            page_num += 1
            if page_num >= loop_break_counter:
                break
            try:
                WebDriverWait(self.driver, self.timeout).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, '[class^="{}"]'.format("footer"))
                    )
                )
            except (TimeoutException, NoSuchElementException) as e:
                logger.error(
                    "Did not find the footer element %s. Moving on..",
                    e,
                    exc_info=True,
                )
            logger.info("Now scraping page %d out of %d..", page_num, num_pages)
            super().scrape_page(f"{url}?cp={page_num}")

    def get_product_elements(self) -> List[WebElement]:
        """Parses the list of products of retailer web page.

        Returns:
            elements: List of products as web elements.
        """
        return self.driver.find_elements(
            by=By.CSS_SELECTOR, value='[class^="{}"]'.format("list-item")
        )

    @staticmethod
    def get_product_id(element: WebElement) -> str | None:
        """Extract unique identifier of product given by the retailer. Usually part of product
        url.

        Args:
            element: The product web element.

        Returns:
            product_id: The product identifier
        """
        # get model and sku of the product
        try:
            description = element.find_element(
                by=By.CSS_SELECTOR, value='[class^="{}"]'.format("sku-model")
            ).text
            # Regular expression pattern
            pattern = r"SKU:\s*(\S+)(?:\nModel:\s*(\S+))?"
            # Search for matches
            match = re.search(pattern, description)
            if match:
                # Extracting SKU as the product id
                sku = match.group(1)
                return sku
            else:
                logger.exception(
                    "SKU could not be parsed from description %s, skipping item..",
                    description,
                )
                return None
        except (NoSuchElementException, ValueError):
            logger.exception("SKU element not found, skipping item..")
            return None

    @staticmethod
    def get_product_buy_price(element: WebElement) -> float | None:
        """Extract the current buy price of product.

        Args:
            element: The product web element.

        Returns:
            price: The current buy price.
        """
        try:
            class_name = "priceView-hero-price"
            price = element.find_element(
                by=By.CSS_SELECTOR,
                value='[class^="{}"]'.format(class_name),
            ).text
            try:
                # Regular expression to match various price formats
                match = re.search(r"\$\d{1,3}(?:,\d{3})*(?:\.\d{0,2})?", price)
                if match:
                    # Removing commas and dollar sign, and converting to float
                    return float(match.group(0).replace(",", "").replace("$", ""))
                else:
                    # If no price is found, return None
                    logger.exception(
                        "%s information could not be extracted from %s, skipping item..",
                        class_name,
                        price,
                    )
                    return None
            except ValueError:
                # If conversion fails, return None
                logger.exception(
                    "%s information could not be extracted from %s, skipping item..",
                    class_name,
                    price,
                )
                return None
        except NoSuchElementException:
            logger.warning("%s element not found, skipping item..", class_name)
            return None

    @staticmethod
    def get_product_original_price(element: WebElement) -> float | None:
        """Extract the original price of product.

        Args:
            element: The product web element.

        Returns:
            price: The product original price.
        """
        try:
            class_name = "pricing-price__regular-price-content"
            price = element.find_element(
                by=By.CSS_SELECTOR,
                value='[class^="{}"]'.format(class_name),
            ).text
            try:
                # Regular expression to match various price formats
                match = re.search(r"\$\d{1,3}(?:,\d{3})*(?:\.\d{0,2})?", price)
                if match:
                    # Removing commas and dollar sign, and converting to float
                    return float(match.group(0).replace(",", "").replace("$", ""))
                else:
                    # If no price is found, return None
                    logger.exception(
                        "%s information could not be extracted from %s, skipping item..",
                        class_name,
                        price,
                    )
                    return None
            except ValueError:
                # If conversion fails, return None
                logger.exception(
                    "%s information could not be extracted from %s, skipping item..",
                    class_name,
                    price,
                )
                return None
        except NoSuchElementException:
            logger.warning("%s element not found, skipping item..", class_name)
            return None

    @staticmethod
    def get_product_title(element: WebElement) -> str | None:
        """Extract the product title given by the retailer.

        Args:
            element: The product web element.

        Returns:
            title: The title of product.
        """
        try:
            return element.find_element(
                by=By.CSS_SELECTOR, value='[class^="{}"]'.format("sku-title")
            ).text
        except NoSuchElementException:
            logger.warning("Cannot fetch product title, marking as null..")
            return None

    @staticmethod
    def get_product_rating(element: WebElement) -> float | None:
        """Extract the product rating on the retailer website.

        Args:
            element: The product web element.

        Returns:
            rating: The product rating out of scale of 5.
        """
        try:
            reviews = element.find_element(
                by=By.CSS_SELECTOR,
                value='[class^="{}"]'.format("c-ratings-reviews"),
            ).text
            try:
                # Extract the float rating
                rating_match = re.search(r"Rating (\d+(\.\d+)?) out of", reviews)
                rating = float(rating_match.group(1)) if rating_match else None
                return rating
            except ValueError:
                logger.exception(
                    "Review information could not be extracted from %s, skipping item..",
                    reviews,
                )
                # Return None for both if any conversion fails
                return None
        except NoSuchElementException:
            logger.warning("Rating element not found, skipping item..")
            return None

    @staticmethod
    def get_product_review_count(element: WebElement) -> int | None:
        """Extract the number of reviews of the product.

        Args:
            element: The product web element.

        Returns:
            review_count: The number of reviews of the product in the retailer website.
        """
        try:
            reviews = element.find_element(
                by=By.CSS_SELECTOR,
                value='[class^="{}"]'.format("c-ratings-reviews"),
            ).text
            try:
                # Extract the integer (number of reviews) and remove commas
                reviews_match = re.search(r"with ([\d,]+) reviews", reviews)
                reviews = (
                    int(reviews_match.group(1).replace(",", ""))
                    if reviews_match
                    else None
                )

                return reviews
            except ValueError:
                logger.exception(
                    "Review count information could not be extracted from %s, skipping item..",
                    reviews,
                )
                # Return None for both if any conversion fails
                return None
        except NoSuchElementException:
            logger.warning("Review count element not found, skipping item..")
            return None

    @staticmethod
    def get_product_additional_attributes(element: WebElement) -> dict | None:
        """Gets product additional attributes that may exist in the retailer page.

        Args:
            element: Product web element.
        """
        try:
            description = element.find_element(
                by=By.CSS_SELECTOR, value='[class^="{}"]'.format("sku-model")
            ).text
            # Regular expression pattern
            pattern = r"Model: ([^\n]+)"
            # Search for matches
            match = re.search(pattern, description)
            if match:
                # Extracting Model values if exist
                model = match.group(1) if match.group(1) else None
                return {"model": model}
            else:
                logger.exception(
                    "Model could not be parsed from description %s, skipping item..",
                    description,
                )
                return None
        except (NoSuchElementException, ValueError):
            logger.exception("Model element not found, skipping item..")
            return None
