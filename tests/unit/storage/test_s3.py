from unittest.mock import MagicMock, patch

from sqlalchemy.exc import SQLAlchemyError
import pytest

from price_scraper.storage import s3


@pytest.fixture
@patch("boto3.Session")
@patch(s3.__name__ + ".text")
@patch(s3.__name__ + ".Base")
@patch(s3.__name__ + ".sessionmaker")
@patch(s3.__name__ + ".create_engine")
def storage(
    mock_create_engine, mock_session_maker, mock_model_base, mock_text, mock_boto3
):
    return s3.S3Storage(bucket_and_prefix="s3://<bucket>/<prefix>", region="<region>")


def test_init(storage):
    assert storage.session.execute.call_count == 4


@patch.object(s3.S3Storage, "_save_metadata")
@patch.object(s3.S3Storage, "_save_prices")
def test_save(mock_save_prices, mock_save_metadata, storage):
    mock_product_meta = [MagicMock()]
    mock_product_data = MagicMock()

    storage.save(product_prices=mock_product_data, product_metadata=mock_product_meta)

    mock_save_prices.assert_called_once()
    mock_save_metadata.assert_called_once()


def test__save_metadata(storage):
    mock_product_meta = [MagicMock()]
    storage.session.execute.reset_mock()

    storage._save_metadata(
        category="category",
        brand="brand",
        product_metadata=mock_product_meta,
    )

    assert storage.session.query.call_count == 1
    assert storage.session.execute.call_count == 2
    assert storage.session.commit.call_count == 2

    # test rollback
    storage.session.commit.side_effect = SQLAlchemyError
    storage._save_metadata(
        category="category",
        brand="brand",
        product_metadata=mock_product_meta,
    )
    assert storage.session.rollback.call_count == 2


def test__save_prices(storage):
    mock_product_prices = MagicMock()
    retailer_enum = MagicMock()
    storage.session.execute.reset_mock()

    storage._save_prices(
        product_prices=mock_product_prices,
        category="category",
        brand="brand",
        retailer=retailer_enum,
        dt=MagicMock(),
    )

    assert storage.session.add_all.call_count == 1
    assert storage.session.execute.call_count == 1
    assert storage.session.commit.call_count == 2

    # test rollback
    storage.session.commit.side_effect = SQLAlchemyError
    storage._save_prices(
        product_prices=mock_product_prices,
        category="category",
        brand="brand",
        retailer=retailer_enum,
        dt=MagicMock(),
    )
    assert storage.session.rollback.call_count == 2
