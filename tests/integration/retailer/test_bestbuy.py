from price_scraper.cli import scrape, PriceScraperSchema


def test_amazon():
    scraper = scrape(
        PriceScraperSchema(
            retailer="BBY",
            url="https://www.bestbuy.com/site/all-laptops/macbooks/pcmcat247400050001.c",
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
