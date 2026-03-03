# schema.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.db import TransactionType

class AssetBase(BaseModel):
    """Base schema with common asset fields"""
    symbol: str = Field(..., min_length=1, max_length=10, description="Asset ticker symbol (e.g., AAPL)")
    name: str = Field(..., min_length=1, max_length=100, description="Asset name")
    sector: str = Field(..., min_length=1, max_length=50, description="Market sector")
    average_buy_price: float = Field(..., gt=0, description="Average purchase price")
    quantity: int = Field(..., gt=0, description="Number of shares/units owned")
    profit_pct: Optional[float] = Field(None, description="Profit percentage")


class AssetCreate(AssetBase):
    """Schema for creating a new asset"""
    user_id: UUID = Field(..., description="ID of the user who owns this asset")
    current_price: Optional[float] = Field(None, gt=0, description="Current market price")


class AssetUpdate(BaseModel):
    """Schema for updating an asset"""
    symbol: Optional[str] = Field(None, min_length=1, max_length=10)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    sector: Optional[str] = Field(None, min_length=1, max_length=50)
    average_buy_price: Optional[float] = Field(None, gt=0)
    current_price: Optional[float] = Field(None, gt=0)
    quantity: Optional[int] = Field(None, gt=0)
    wallet_percentage: Optional[float] = Field(None, ge=0, le=100)


class AssetResponse(AssetBase):
    """Schema for asset responses from the API"""
    id: UUID
    current_price: Optional[float] = None
    wallet_percentage: Optional[float] = None
    user_id: UUID
    
    model_config = ConfigDict(from_attributes=True)


class PortfolioResponse(BaseModel):
    """Schema for portfolio response"""
    total_assets: int
    total_value: Optional[float] = None
    assets: list[AssetResponse]

# ========================================================================================
# User Schemas
# ========================================================================================

class UserBase(BaseModel):
    """Base schema for user"""
    email: str = Field(..., min_length=3, max_length=100, description="User email")
    notion_database_id: Optional[str] = Field(None, min_length=1, max_length=50, description="Notion database ID")
    notion_api_key: Optional[str] = Field(None, min_length=1, max_length=100, description="Notion API key")


class UserCreate(UserBase):
    """Schema for creating a user"""
    pass


class UserResponse(UserBase):
    """Schema for user responses"""
    id: UUID
    
    model_config = ConfigDict(from_attributes=True)

# ========================================================================================
# Transaction Schemas
# ========================================================================================

class TransactionBase(BaseModel):
    """Base schema for transaction"""
    transaction_type: TransactionType = Field(..., description="Type of transaction: 'buy' or 'sell'")
    quantity: int = Field(..., gt=0, description="Number of shares/units transacted")
    price_per_unit: float = Field(..., gt=0, description="Price per unit at the time of transaction")
    transaction_date: Optional[datetime] = Field(None, description="Date and time of the transaction")

class TransactionCreate(TransactionBase):
    """Schema for creating a transaction"""
    asset_id: UUID = Field(..., description="ID of the asset associated with this transaction")
    
class TransactionResponse(TransactionBase):
    """Schema for transaction responses"""
    id: UUID
    asset_id: UUID
    
    model_config = ConfigDict(from_attributes=True)

class TransactionUpdate(BaseModel):
    """Schema for updating a transaction"""
    transaction_type: Optional[TransactionType] = None
    quantity: Optional[int] = Field(None, gt=0)
    price_per_unit: Optional[float] = Field(None, gt=0)
    transaction_date: Optional[datetime] = None

# ========================================================================================