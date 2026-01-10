from app.service import PortfolioService, MarketDataService
from app.db import engine
from sqlalchemy.orm import Session

def refresh_my_portfolio():
    """
    Triggers a real-time update of all asset prices in the portfolio 
    using live market data from B3.

    Returns a confirmation message upon completion.

    inputs: None
    outputs: str - Confirmation message
    """
    with Session(engine) as session:
        service = MarketDataService()
        service.update_all_prices(session)
    return "Portfolio prices have been updated."

def update_portfolio_percentages(user_id: int):
    """
    Updates the wallet_percentage for all assets in the user's portfolio.
    
    inputs:
    - user_id: int - The ID of the user whose portfolio percentages need updating.
    
    outputs:
    - str - Confirmation message
    """
    with Session(engine) as session:
        service = PortfolioService()
        service.update_portfolio_percentages(session, user_id)
    return "Portfolio percentages have been updated."   