from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Annotated
from app.db import get_db, Base, engine, Transaction, Asset
from uuid import uuid4
from app.schema import (
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate
)
from app.service import PortfolioService
import traceback

# Create all tables
Base.metadata.create_all(bind=engine)

router = APIRouter()

# Define a dependency type alias
DatabaseSession = Annotated[Session, Depends(get_db)]

@router.post(
    "/transactions/",
    summary="Create Transaction",
    description="Create a new transaction for an asset",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_transaction(session: DatabaseSession, transaction: TransactionCreate):
    """
    Create a new transaction for an asset.
    
    Parameters:
    - **transaction_type**: Type of transaction ('buy' or 'sell')
    - **quantity**: Number of shares/units transacted
    - **price_per_unit**: Price per unit at the time of transaction
    - **transaction_date**: Date and time of the transaction
    - **asset_id**: ID of the asset associated with this transaction
    """
    # look up the asset first to get its owner
    asset = session.query(Asset).filter(Asset.id == transaction.asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail=f"Asset '{transaction.asset_id}' not found")

    db_transaction = Transaction(
        id=uuid4(),
        transaction_type=transaction.transaction_type,
        quantity=transaction.quantity,
        price_per_unit=transaction.price_per_unit,
        transaction_date=transaction.transaction_date,
        asset_id=transaction.asset_id
    )

    try:
        portfolio_service = PortfolioService(session=session)
        portfolio_service.record_transaction(db_transaction, user_id=asset.user_id)
        portfolio_service.update_portfolio_percentages(user_id=asset.user_id)
    except Exception as e:
            print(f"Error Type: {type(e).__name__}")
            print(f"Error Message: {str(e)}")
            print(f"\nFull Traceback:")
            traceback.print_exc()
            raise HTTPException(status_code=500, detail="Failed to update asset related to this transaction") from e       

    try:
        session.add(db_transaction)
        session.commit()
        session.refresh(db_transaction)
        return db_transaction
    except Exception as e:
        session.rollback()
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        print(f"\nFull Traceback:")
        traceback.print_exc()
        error_msg = str(e).lower()
        if 'foreign key' in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Asset with id '{transaction.asset_id}' does not exist"
            )
        elif 'not null' in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing required transaction fields"
            )
        elif 'invalid asset' in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid asset id '{transaction.asset_id}'"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to create transaction") from e

@router.get(
    "/transactions/{transaction_id}",
    summary="Get Transaction",
    description="Retrieve a transaction by its ID",
    response_model=TransactionResponse,
)
def get_transaction(transaction_id: str, session: DatabaseSession):
    """
    Retrieve a transaction by its ID.
    
    Parameters:
    - **transaction_id**: UUID of the transaction to retrieve
    """
    transaction = session.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail=f"Transaction with ID '{transaction_id}' not found")
    return transaction

@router.get(
    "/transactions/",
    summary="Get All Transactions",
    description="Retrieve all transactions",
    response_model=list[TransactionResponse],
)
def get_all_transactions(session: DatabaseSession):
    """
    Retrieve all transactions.
    """
    transactions = session.query(Transaction).all()
    if not transactions:
        print("No transactions found in the database.")
        raise HTTPException(status_code=404, detail="No transactions found")

    return transactions

@router.delete(
    "/transactions/{transaction_id}",
    summary="Delete Transaction",
    description="Delete a transaction by its ID",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_transaction(transaction_id: str, session: DatabaseSession):
    """
    Delete a transaction by its ID.
    
    Parameters:
    - **transaction_id**: UUID of the transaction to delete
    """
    transaction = session.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail=f"Transaction with ID '{transaction_id}' not found")

    try:
        session.delete(transaction)
        session.commit()
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete transaction") from e

@router.put(
    "/transactions/{transaction_id}",
    summary="Update Transaction",
    description="Update an existing transaction by its ID",
    response_model=TransactionResponse,
)
def update_transaction(transaction_id: str, transaction_update: TransactionUpdate, session: DatabaseSession):
    """
    Update an existing transaction by its ID.
    
    Parameters:
    - **transaction_id**: UUID of the transaction to update
    - **transaction_update**: Fields to update in the transaction
    """
    transaction = session.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not transaction:
        raise HTTPException(status_code=404, detail=f"Transaction with ID '{transaction_id}' not found")

    # Update fields if provided
    if transaction_update.transaction_type is not None:
        transaction.transaction_type = transaction_update.transaction_type
    if transaction_update.quantity is not None:
        transaction.quantity = transaction_update.quantity
    if transaction_update.price_per_unit is not None:
        transaction.price_per_unit = transaction_update.price_per_unit
    if transaction_update.transaction_date is not None:
        transaction.transaction_date = transaction_update.transaction_date

    try:
        session.commit()
        session.refresh(transaction)
        return transaction
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail="Failed to update transaction") from e