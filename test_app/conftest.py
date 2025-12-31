# conftest.py
import pytest
from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy_utils import database_exists, create_database, drop_database
from fastapi.testclient import TestClient

from app.db import Base, get_db
from app.app import app

# Test database configuration
TEST_DATABASE_URL = "postgresql://myuser:mypassword@localhost:5432/test_mydatabase"


TEST_DATABASE_URL = "postgresql://myuser:mypassword@localhost:5432/test_mydatabase"


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """
    Create test database once before all tests.
    Tables are created once and reused with transaction rollback.
    """
    if not database_exists(TEST_DATABASE_URL):
        print(f"\n📦 Creating test database...")
        create_database(TEST_DATABASE_URL)
    
    engine = create_engine(TEST_DATABASE_URL)
    
    # Create all tables once
    print(f"🔧 Creating tables...")
    Base.metadata.create_all(bind=engine)
    
    yield
    
    # Cleanup after all tests
    print(f"\n🧹 Dropping tables...")
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="session")
def db_engine():
    """Database engine shared across all tests."""
    engine = create_engine(
        TEST_DATABASE_URL,
        pool_pre_ping=True,
        echo=False  # Set to True to see SQL queries
    )
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def test_db(db_engine):
    """
    Provides a database session that automatically rolls back after each test.
    This is much faster than creating/dropping tables for each test.
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    
    session = sessionmaker(bind=connection)()
    
    # Start a SAVEPOINT (nested transaction)
    nested = connection.begin_nested()
    
    # Each time the SAVEPOINT ends, reopen it
    @event.listens_for(session, "after_transaction_end")
    def end_savepoint(session, transaction):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()
    
    yield session
    
    # Rollback the overall transaction, restoring database to clean state
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(test_db):
    """FastAPI test client using test database."""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture(scope="session")
def test_engine_fixture(db_engine):
    """
    Alias for db_engine to maintain compatibility with existing tests.
    """
    return db_engine

@pytest.fixture
def test_user(test_db):
    """Provides a test user for tests"""
    from app.db import User
    from uuid import uuid4
    
    user = User(
        id=uuid4(),
        email="test@example.com",
        notion_database_id="test-notion-db",
        notion_api_key="test-api-key"
    )
    test_db.add(user)
    test_db.commit()  # This commits to the SAVEPOINT
    test_db.expire_all()  # Force reload from transaction
    
    # Re-query to ensure it's attached to session
    user = test_db.query(User).filter(User.email == "test@example.com").first()
    
    return user