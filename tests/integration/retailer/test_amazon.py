import allure
import pytest

from price_scraper.cli import scrape, PriceScraperSchema


@allure.epic("Amazon")
@allure.parent_suite('Brand grid product page')
@pytest.mark.amazon
@pytest.mark.selenium
@pytest.mark.brand_grid
def test_amazon():
    allure.dynamic.suite("Brand Grid")
    scraper = scrape(
        PriceScraperSchema(
            retailer="AMZ",
            url="https://www.amazon.com/stores/page/D209D922-7883-495C-9894-6B13D9BB1A67",
            category="dummy/category",
            brand="dummy",
            storage_config=[],
        ),
        max_pagination=2,
    )

    assert any([0 < (price.buy_price or 0) < 10_000 for price in scraper.product_prices])
    assert any([price.rating is not None for price in scraper.product_prices])
    assert any([price.review_count is not None for price in scraper.product_prices])
    assert any([price.product_id is not None for price in scraper.product_metadata])
