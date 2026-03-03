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
from app.routers import assets, auth, transactions, refresh, portfolio

from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# Create all tables (in production, you'd use Alembic migrations instead)
Base.metadata.create_all(bind=engine)

app = FastAPI()

# app.mount("/", StaticFiles(directory="static", html=True), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # tighten this to your domain in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define a dependency type alias for cleaner code
DatabaseSession = Annotated[Session, Depends(get_db)]

app.include_router(assets.router, prefix="/assets", tags=["Assets"])
app.include_router(auth.router, prefix="/users", tags=["Users"])
app.include_router(transactions.router, prefix="/transactions", tags=["Transactions"])
app.include_router(refresh.router, tags=["Market Data"])
app.include_router(portfolio.router, tags=["Notion Sync", "Portfolio"])