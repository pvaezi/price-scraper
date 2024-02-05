# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2024-02-04

### Added

- Ability to scrape retailer websites using Selenium provided as extendable repository pattern. Currently Amazon and BestBuy grid product page layouts are supported.
- Ability to store scrape product price data and metadata into transactional or analytical storages. Storage can be extended via repository pattern.
- `price_scraper` CLI with pydantic schema validation to enable configurable scraping.
