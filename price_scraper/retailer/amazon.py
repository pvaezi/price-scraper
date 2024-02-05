from __future__ import annotations

import logging
import re
from typing import List, TYPE_CHECKING

from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from price_scraper.enums import Retailer
from price_scraper.retailer.base import BaseRetailer

if TYPE_CHECKING:
    from selenium.webdriver.remote.webelement import WebElement


logger = logging.getLogger()


class Amazon(BaseRetailer):
    """Scrapping Amazon product grid view pages for product price information.

    Attributes:
        retailer: The enum specified for the retailer
    """

    retailer = Retailer.AMZ

    def paginate_and_scrape(self, url: str):
        """This method clicks on Show more button to load additional pages of data into the same
        page as part of pagination strategy.

        Args:
            url: The input https URL in string format.
        """
        super().scrape_page(url)
        # Press show more button until all items are rendered in the page.
        for page_num in range(self.max_pagination):
            try:
                # Wait for the element to be present
                show_more_button: WebElement = WebDriverWait(
                    self.driver, self.timeout
                ).until(
                    EC.presence_of_element_located(
                        (
                            By.CSS_SELECTOR,
                            '[class*="{}"]'.format("ShowMoreButton__button__"),
                        )
                    )
                )
                show_more_button.click()
                logger.info(
                    "Clicked on show more button to get page %d..", page_num + 1
                )
            except TimeoutException:
                logger.warning(
                    "Did not find the show more element after waiting %d seconds. Moving on..",
                    self.timeout,
                )
                break
            except NoSuchElementException:
                logger.info("Show more element is not present. Moving on..")
                break
        # find all product elements in the page
        elements = self.get_product_elements()
        self.parse_products_information(elements)

    def get_product_elements(self) -> List[WebElement]:
        """Parses the list of products of retailer web page.

        Returns:
            elements: List of products as web elements.
        """
        return self.driver.find_elements(
            by=By.CSS_SELECTOR, value='[class^="{}"]'.format("ProductGridItem__item__")
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
        try:
            title = element.find_element(
                by=By.CSS_SELECTOR, value='[class^="{}"]'.format("Title__title__")
            )
            # extract unique identifier of product page on amazon
            # Regular expression to match the pattern /dp/ followed by the product ID
            match = re.search(r"/dp/([^/?]+)", title.get_attribute("href"))
            if match:
                return match.group(1)
            else:
                return None
        except NoSuchElementException as e:
            logger.error(
                "Something failed to create row entries from the production information, "
                "error: %s",
                e,
                exc_info=True,
            )
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
            class_name = "ProductGridItem__buyPrice__"
            price = element.find_element(
                by=By.CSS_SELECTOR,
                value='[class*="{}"]'.format(class_name),
            ).get_attribute("aria-label")
            try:
                # Remove non-numeric characters and convert to float
                return float(re.sub(r"[^\d.]", "", price))
            except ValueError:
                # Handle the case where the string cannot be converted
                logger.warning(
                    "Cannot convert buy price '%s' to float, assuming null..", price
                )
                return None
        except NoSuchElementException:
            logger.warning(
                "Cannot find the web element for buy price %s, assuming null..",
                class_name,
            )
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
            class_name = "StrikeThroughPrice__strikePrice__"
            price = element.find_element(
                by=By.CSS_SELECTOR,
                value='[class*="{}"]'.format(class_name),
            ).get_attribute("aria-label")
            try:
                # Remove non-numeric characters and convert to float
                return float(re.sub(r"[^\d.]", "", price))
            except ValueError:
                # Handle the case where the string cannot be converted
                logger.warning(
                    "Cannot convert original price '%s' to float, assuming null..",
                    price,
                )
                return None
        except NoSuchElementException:
            logger.warning(
                "Cannot find the web element for original price %s, assuming null..",
                class_name,
            )
            return None

    @staticmethod
    def get_product_coupon_value(element: WebElement) -> float | None:
        """Extract the coupon value website offers for the product.

        Args:
            element: The product web element.

        Returns:
            price: The coupon value.
        """
        try:
            class_name = "Price__base__"
            price = element.find_element(
                by=By.CSS_SELECTOR,
                value='[class*="{}"]'.format(class_name),
            ).get_attribute("aria-label")
            try:
                # Remove non-numeric characters and convert to float
                return float(re.sub(r"[^\d.]", "", price))
            except ValueError:
                # Handle the case where the string cannot be converted
                logger.warning(
                    "Cannot convert coupon value '%s' to float, assuming null..", price
                )
                return None
        except NoSuchElementException:
            logger.warning(
                "Cannot find the web element for coupon value %s, assuming null..",
                class_name,
            )
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
            title = element.find_element(
                by=By.CSS_SELECTOR, value='[class^="{}"]'.format("Title__title__")
            )
            # get image element
            image = element.find_element(
                by=By.CSS_SELECTOR,
                value='[class^="{}"]'.format("ProductGridItem__image__"),
            )
            # get product name
            try:
                # NOTE currently image alt shows more complete name of product
                return image.find_element(by=By.TAG_NAME, value="img").get_attribute(
                    "alt"
                )
            except NoSuchElementException:
                # if element does not exist use title span text as backup option
                return title.text
        except NoSuchElementException as e:
            logger.exception(
                "Something failed to create row entries from the production information, "
                "error: %s",
                e,
            )
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
            rating = element.find_element(
                by=By.CSS_SELECTOR, value='[class^="{}"]'.format("Icon__icon__")
            ).get_attribute("innerHTML")
            try:
                # Extract the numeric part of the rating (handles both integer and decimal)
                match = re.search(r"(\d+(\.\d+)?)", rating)
                if match:
                    return float(match.group(1))
                else:
                    # If the format doesn't match, return None
                    logger.warning(
                        "Cannot match rating from '%s', assuming null..", rating
                    )
                    return None
            except ValueError:
                # Handle any unexpected ValueError
                logger.warning(
                    "Cannot extract rating from '%s', assuming null..", rating
                )
                return None
        except NoSuchElementException:
            logger.warning("Cannot find the web element for rating, assuming null..")
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
            review_count = element.find_element(
                by=By.CSS_SELECTOR,
                value='[class^="{}"]'.format("ProductGridItem__reviewCount"),
            ).text
            try:
                # Extract the numerical part
                match = re.search(r"(\d+(?:\.\d+)?)", review_count)
                if match:
                    # Convert to float and then to int to get the integer part
                    return int(float(match.group(1)))
                else:
                    # If no valid number is found, return None
                    logger.warning(
                        "Cannot match review count from '%s', assuming null..",
                        review_count,
                    )
                    return None
            except ValueError:
                # If conversion fails, return None
                logger.warning(
                    "Cannot extract review count from '%s', assuming null..",
                    review_count,
                )
                return None
        except NoSuchElementException:
            logger.warning("Cannot find the web element for rating, assuming null..")
            return None
