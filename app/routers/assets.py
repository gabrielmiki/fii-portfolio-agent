# app.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Annotated
from uuid import uuid4, UUID

from app.db import get_db, Base, engine, Asset
from app.schema import (
    AssetCreate, 
    AssetResponse, 
    PortfolioResponse,
    AssetUpdate
)

# Create all tables
Base.metadata.create_all(bind=engine)

router = APIRouter()

# Define a dependency type alias
DatabaseSession = Annotated[Session, Depends(get_db)]


@router.get(
    "/portfolio/",
    response_model=PortfolioResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Portfolio",
    description="Retrieve all assets in the portfolio with their current values"
)
async def get_portfolio(session: DatabaseSession):
    """
    Retrieve the complete portfolio.
    
    Returns:
    - List of all assets
    - Total number of assets
    - Total portfolio value (if current prices are available)
    """
    # Query all assets from the database
    assets = session.query(Asset).all()
    
    # Calculate total portfolio value
    total_value = 0.0
    has_prices = True
    
    for asset in assets:
        if asset.current_price is not None:
            total_value += float(asset.current_price) * asset.quantity
        else:
            has_prices = False
    
    return {
        "total_assets": len(assets),
        "total_value": total_value if has_prices else None,
        "assets": assets
    }


@router.post(
    "/assets/",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Asset",
    description="Add a new asset to the portfolio"
)
async def create_asset(
    asset: AssetCreate,
    session: DatabaseSession
):
    """
    Create a new asset in the portfolio.
    
    Parameters:
    - **symbol**: Ticker symbol (must be unique)
    - **name**: Asset name
    - **sector**: Market sector
    - **average_buy_price**: Average purchase price
    - **quantity**: Number of shares/units
    - **user_id**: Owner's user ID
    - **current_price**: Optional current market price
    
    Returns the created asset with its generated ID.
    """
    # Check if asset with this symbol already exists
    existing_asset = session.query(Asset).filter(Asset.symbol == asset.symbol).first()
    if existing_asset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Asset with symbol '{asset.symbol}' already exists"
        )
    
    # Create new asset instance
    db_asset = Asset(
        id=uuid4(),  # Generate UUID
        symbol=asset.symbol,
        name=asset.name,
        sector=asset.sector,
        average_buy_price=asset.average_buy_price,
        current_price=asset.current_price,
        quantity=asset.quantity,
        user_id=asset.user_id,
        wallet_percentage=None  # Can be calculated later
    )
    
    try:
        # Add to database
        session.add(db_asset)
        session.commit()
        session.refresh(db_asset)  # Refresh to get any database-generated values
        
        return db_asset
        
    except IntegrityError as e:
        session.rollback()
        # Check if it's a foreign key violation (user doesn't exist)
        if "foreign key" in str(e.orig).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID '{asset.user_id}' not found"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database error: {str(e.orig)}"
        )


@router.delete(
    "/assets/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Asset",
    description="Remove an asset from the portfolio"
)
async def delete_asset(
    asset_id: UUID,
    session: DatabaseSession
):
    """
    Delete an asset from the portfolio.
    
    Parameters:
    - **asset_id**: UUID of the asset to delete
    
    Returns:
    - 204 No Content on success
    - 404 Not Found if asset doesn't exist
    
    Note: This will also delete all associated transactions due to cascade.
    """
    # Query the asset
    asset = session.query(Asset).filter(Asset.id == asset_id).first()
    
    # If asset doesn't exist, return 404
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID '{asset_id}' not found"
        )
    
    try:
        # Delete the asset
        session.delete(asset)
        session.commit()
        
        # Return 204 No Content (FastAPI handles this with None return)
        return None
        
    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting asset: {str(e)}"
        )


# Bonus: GET single asset endpoint
@router.get(
    "/assets/{asset_id}",
    response_model=AssetResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Asset",
    description="Retrieve a specific asset by ID"
)
async def get_asset(
    asset_id: UUID,
    session: DatabaseSession
):
    """
    Retrieve a single asset by its ID.
    
    Parameters:
    - **asset_id**: UUID of the asset
    
    Returns the asset details or 404 if not found.
    """
    asset = session.query(Asset).filter(Asset.id == asset_id).first()
    
    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID '{asset_id}' not found"
        )
    
    return asset


# Bonus: UPDATE asset endpoint
@router.put(
    "/assets/{asset_id}",
    response_model=AssetResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Asset",
    description="Update an existing asset's information"
)
async def update_asset(
    asset_id: UUID,
    asset_update: AssetUpdate,
    session: DatabaseSession
):
    """
    Update an asset's information.
    
    Parameters:
    - **asset_id**: UUID of the asset to update
    - Only include fields you want to update
    
    Returns the updated asset.
    """
    # Find the asset
    db_asset = session.query(Asset).filter(Asset.id == asset_id).first()
    
    if not db_asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset with ID '{asset_id}' not found"
        )
    
    # Update only provided fields
    update_data = asset_update.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(db_asset, field, value)
    
    try:
        session.commit()
        session.refresh(db_asset)
        return db_asset
        
    except IntegrityError as e:
        session.rollback()
        if "unique" in str(e.orig).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Asset with this symbol already exists"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Database error: {str(e.orig)}"
        )