import pytest
from app.db import User, Asset, Transaction
from app.service import PortfolioService

@pytest.mark.services
def test_record_transaction_buy(test_db, user_factory, asset_factory, transaction_factory):
    """Test recording a buy transaction updates asset correctly."""
    test_user = user_factory()
    test_asset = asset_factory(user_id=test_user.id, quantity=100, average_buy_price=100.00)
    
    portfolio_service = PortfolioService(session=test_db)

    buy_transaction = Transaction(
        transaction_type="buy",
        quantity=50,
        price_per_unit=120.00,
        asset_id=test_asset.id
    )

    portfolio_service.record_transaction(buy_transaction, user_id=test_user.id)

    updated_asset = test_db.query(Asset).filter(Asset.id == test_asset.id).first()
    
    assert updated_asset.quantity == 150
    expected_avg_price = ((100 * 100.00) + (50 * 120.00)) / 150
    assert float(updated_asset.average_buy_price) == round(expected_avg_price, 2)

@pytest.mark.services
def test_record_transaction_sell(test_db, user_factory, asset_factory, transaction_factory):
    """Test recording a sell transaction updates asset correctly."""
    test_user = user_factory()
    test_asset = asset_factory(user_id=test_user.id, quantity=100, average_buy_price=100.00)
    
    portfolio_service = PortfolioService(session=test_db)

    sell_transaction = Transaction(
        transaction_type="sell",
        quantity=40,
        price_per_unit=110.00,
        asset_id=test_asset.id
    )

    portfolio_service.record_transaction(sell_transaction, user_id=test_user.id)

    updated_asset = test_db.query(Asset).filter(Asset.id == test_asset.id).first()
    
    assert updated_asset.quantity == 60
    assert float(updated_asset.average_buy_price) == 100.00  # Average buy price should remain unchanged

@pytest.mark.services
def test_update_portfolio_percentages(test_db, user_factory, asset_factory):
    """Test updating portfolio percentages."""
    test_user = user_factory()
    asset1 = asset_factory(user_id=test_user.id, quantity=100, current_price=10.00)  # Total value = 1000
    asset2 = asset_factory(user_id=test_user.id, quantity=50, current_price=20.00)   # Total value = 1000
    asset3 = asset_factory(user_id=test_user.id, quantity=25, current_price=40.00)   # Total value = 1000

    portfolio_service = PortfolioService(session=test_db)
    portfolio_service.update_portfolio_percentages(user_id=test_user.id)

    updated_asset1 = test_db.query(Asset).filter(Asset.id == asset1.id).first()
    updated_asset2 = test_db.query(Asset).filter(Asset.id == asset2.id).first()
    updated_asset3 = test_db.query(Asset).filter(Asset.id == asset3.id).first()

    assert float(updated_asset1.wallet_percentage) == 33.33
    assert float(updated_asset2.wallet_percentage) == 33.33
    assert float(updated_asset3.wallet_percentage) == 33.33


# ==============================================================
# Market Data Service Tests
# ==============================================================

@pytest.mark.services
def test_update_all_prices(test_db, user_factory, asset_factory, monkeypatch):
    """Test updating all asset prices from market data service."""
    test_user = user_factory()
    asset1 = asset_factory(user_id=test_user.id, symbol="TEST1", current_price=10.00)
    asset2 = asset_factory(user_id=test_user.id, symbol="TEST2", current_price=20.00)

    # Mock yfinance Ticker to return controlled price data
    class MockTicker:
        def __init__(self, symbol):
            self.symbol = symbol
            self.fast_info = {'last_price': 99.99 if symbol == "TEST1.SA" else 199.99}

    monkeypatch.setattr("app.service.yf.Ticker", MockTicker)

    from app.service import MarketDataService
    market_data_service = MarketDataService(session=test_db)
    market_data_service.update_all_prices(session=test_db)

    updated_asset1 = test_db.query(Asset).filter(Asset.id == asset1.id).first()
    updated_asset2 = test_db.query(Asset).filter(Asset.id == asset2.id).first()

    assert float(updated_asset1.current_price) == 99.99
    assert float(updated_asset2.current_price) == 199.99