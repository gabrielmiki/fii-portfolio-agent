from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from typing import Annotated
from uuid import uuid4

from app.db import get_db, Base, engine, Asset, User
from app.schema import (
    AssetCreate, 
    AssetResponse, 
    PortfolioResponse,
    AssetUpdate,
    UserCreate,
    UserResponse
)
from app.routers import assets, auth

# Create all tables (in production, you'd use Alembic migrations instead)
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Define a dependency type alias for cleaner code
DatabaseSession = Annotated[Session, Depends(get_db)]

app.include_router(assets.router, prefix="/assets", tags=["Assets"])
app.include_router(auth.router, prefix="/users", tags=["Users"])