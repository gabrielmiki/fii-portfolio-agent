from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Numeric, Integer, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import enum
from uuid import uuid4

DATABASE_URL = "postgresql://myuser:mypassword@localhost:5432/mydatabase"

class TransactionType(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(100), unique=True, nullable=False)
    notion_database_id = Column(String(50), unique=True, nullable=True)
    notion_api_key = Column(String(100), nullable=True)

    assets = relationship("Asset", back_populates="user", cascade="all, delete-orphan")

class Asset(Base):
    __tablename__ = "assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    symbol = Column(String(10), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    sector = Column(String(50), nullable=False)
    average_buy_price = Column(Numeric(10, 2), nullable=False)
    current_price = Column(Numeric(10, 2), nullable=True)
    quantity = Column(Integer, nullable=False)
    wallet_percentage = Column(Numeric(5, 2), nullable=True)
    profit_pct = Column(Numeric(5, 2), nullable=True)
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="assets")

    transactions = relationship("Transaction", back_populates="asset", cascade="all, delete-orphan")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    transaction_type = Column(Enum(TransactionType), nullable=False)  # e.g., 'buy' or 'sell'
    quantity = Column(Integer, nullable=False)
    price_per_unit = Column(Numeric(10, 2), nullable=False)
    transaction_date = Column(DateTime, default=datetime.utcnow)

    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id"), nullable=False)
    asset = relationship("Asset", back_populates="transactions")

engine = create_engine(
    DATABASE_URL,
    # These settings control connection pooling behavior
    pool_pre_ping=True,  # Verifies connections are alive before using them
    echo=True  # Logs all SQL queries (useful for development, turn off in production)
)

SessionLocal = sessionmaker(
    autocommit=False,  # We control when to commit changes
    autoflush=False,   # We control when to flush changes to the database
    bind=engine        # Bind this session factory to our engine
)


# This goes in your database.py file as well
def get_db():
    """
    Dependency that provides a database session to endpoints.
    The session is automatically closed after the request completes,
    even if an exception occurred.
    """
    db = SessionLocal()  # Create a new session
    try:
        yield db  # Provide the session to the endpoint
    finally:
        db.close()  # Ensure the session is closed when done