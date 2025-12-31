# schema.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime

class AssetBase(BaseModel):
    """Base schema with common asset fields"""
    symbol: str = Field(..., min_length=1, max_length=10, description="Asset ticker symbol (e.g., AAPL)")
    name: str = Field(..., min_length=1, max_length=100, description="Asset name")
    sector: str = Field(..., min_length=1, max_length=50, description="Market sector")
    average_buy_price: float = Field(..., gt=0, description="Average purchase price")
    quantity: int = Field(..., gt=0, description="Number of shares/units owned")


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
# Additional schemas for User and Transaction can be defined similarly if needed.
# ========================================================================================

class UserBase(BaseModel):
    """Base schema for user"""
    email: str = Field(..., min_length=3, max_length=100, description="User email")
    notion_database_id: str = Field(..., min_length=1, max_length=50, description="Notion database ID")
    notion_api_key: str = Field(..., min_length=1, max_length=100, description="Notion API key")


class UserCreate(UserBase):
    """Schema for creating a user"""
    pass


class UserResponse(UserBase):
    """Schema for user responses"""
    id: UUID
    
    model_config = ConfigDict(from_attributes=True)