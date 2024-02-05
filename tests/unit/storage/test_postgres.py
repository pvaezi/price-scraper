import os
from unittest.mock import MagicMock, patch

from sqlalchemy.exc import SQLAlchemyError

from price_scraper.storage import postgres


@patch.dict(
    os.environ, {"POSTGRES_USER": "user", "POSTGRES_PASSWORD": "pass"}, clear=True
)
@patch(postgres.__name__ + ".Base")
@patch(postgres.__name__ + ".sessionmaker")
@patch(postgres.__name__ + ".create_engine")
@patch(postgres.__name__ + ".Index")
def test_postgres(mock_index, mock_create_engine, mock_session_maker, mock_model_base):
    # test __init__
    storage = postgres.PostgresStorage()

    assert mock_index.call_count == 4
    mock_create_engine.assert_called_once()
    mock_session_maker.assert_called_once()
    mock_model_base.metadata.create_all.assert_called_once()

    # test save success
    mock_product_meta = [MagicMock()]
    mock_product_data = MagicMock()
    mock_session = mock_session_maker.return_value.return_value
    storage.save(product_prices=mock_product_data, product_metadata=mock_product_meta)

    mock_session.merge.assert_called_once_with(mock_product_meta[0])
    mock_session.add_all.assert_called_once_with(mock_product_data)
    mock_session.commit.assert_called_once()
    mock_session.rollback.assert_not_called()

    # test save rollback exception
    mock_session.commit.side_effect = SQLAlchemyError
    storage.save(product_prices=mock_product_data, product_metadata=mock_product_meta)
    mock_session.rollback.assert_called_once()
