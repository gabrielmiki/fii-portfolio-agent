from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Depends
from app.db import get_db
from sqlalchemy.orm import Session
from app.service import MarketDataService

router = APIRouter()

@router.post(
    "/refresh", 
    summary="Refresh Market Data",
    description="Triggers a background task to refresh market data for all assets.",
    status_code=status.HTTP_202_ACCEPTED
)
def refresh_market_data(
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_db)
):
    market_data_service = MarketDataService(session=session)

    try:
        background_tasks.add_task(market_data_service.update_all_prices, session=session)
    except Exception as e:
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        print(f"\nFull Traceback:")
    return {"message": "Market data refresh initiated in the background."}