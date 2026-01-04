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

# conftest.py
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (slow)"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests (fast)"
    )
    config.addinivalue_line(
        "markers", "database: marks tests that require database"
    )
    config.addinivalue_line(
        "markers", "services: marks tests that require authentication"
    )
    config.addinivalue_line(
        "markers", "endpoints: marks tests for API endpoints"
    )

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Create test database once before all tests."""
    try:
        if not database_exists(TEST_DATABASE_URL):
            print(f"\n📦 Creating test database: {TEST_DATABASE_URL}")
            create_database(TEST_DATABASE_URL)
        else:
            print(f"\n✓ Test database already exists: {TEST_DATABASE_URL}")
    except Exception as e:
        pytest.fail(f"Failed to create test database: {e}\nURL: {TEST_DATABASE_URL}")
    
    try:
        engine = create_engine(TEST_DATABASE_URL)
        print(f"🔧 Creating tables...")
        Base.metadata.create_all(bind=engine)
        print(f"✓ Created {len(Base.metadata.tables)} tables")
    except Exception as e:
        pytest.fail(f"Failed to create tables: {e}")
    
    yield
    
    try:
        print(f"\n🧹 Dropping tables...")
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        print(f"✓ Cleanup complete")
    except Exception as e:
        # Log but don't fail - cleanup errors shouldn't break the test run
        print(f"Warning: Cleanup failed: {e}")

## TODO: Add safety checks in all other fixtures to ensure they use TEST_DATABASE_URL
@pytest.fixture(scope="session")
def db_engine():
    """Database engine shared across all tests."""
    try:
        engine = create_engine(
            TEST_DATABASE_URL,
            pool_pre_ping=True,
            echo=False  # Set to True to see SQL queries
        )
        print(f"✓ Database engine created for tests")
    except Exception as e:
        pytest.fail(f"Failed to create database engine: {e}")

    yield engine

    try:
        print(f"🧹 Disposing database engine...")
        engine.dispose()
        print(f"✓ Database engine disposed")
    except Exception as e:
        print(f"Warning: Failed to dispose engine: {e}")

@pytest.fixture(scope="function")
def test_db(db_engine):
    """
    Provides a database session that automatically rolls back after each test.
    This is much faster than creating/dropping tables for each test.
    """
    try:
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
    except Exception as e:
        pytest.fail(
            f"Failed to create database engine.\n"
            f"Error: {e}\n"
            f"Database URL: {TEST_DATABASE_URL}\n\n"
            f"Common causes:\n"
            f"  • PostgreSQL is not running (try: pg_ctl status)\n"
            f"  • Wrong credentials in TEST_DATABASE_URL\n"
            f"  • Database server not accepting connections\n"
            f"  • Firewall blocking port 5432"
        )
    
    yield session
    
    try:
        # Cleanup: explicitly expunge all objects to avoid session leaks
        session.expunge_all()
        # Rollback the overall transaction, restoring database to clean state
        session.close()
        transaction.rollback()
        connection.close()
    except Exception as e:
        print(
            f"\n⚠️  Warning: Test database cleanup failed: {e}\n"
            f"This may indicate a connection leak or improper session usage.\n"
            f"Test: {pytest.current_test_name if hasattr(pytest, 'current_test_name') else 'unknown'}"
        )


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

# ========================================================================================
# Factories for creating test data
# ========================================================================================

# TODO: Add factories for other models as needed
@pytest.fixture
def user_factory(test_db):
    """
    Factory for creating test users with custom attributes.
    Returns a function that creates and persists users.
    """
    from app.db import User
    from uuid import uuid4
    
    def create_user(**kwargs):
        # Provide defaults but allow overrides
        user_data = {
            'id': uuid4(),
            'email': f'test-{uuid4().hex[:8]}@example.com',  # Unique email
            'notion_database_id': 'test-notion-db',
            'notion_api_key': 'test-api-key'
        }
        # Override defaults with any provided kwargs
        user_data.update(kwargs)

        try:
            user = User(**user_data)
            test_db.add(user)
            test_db.commit()
            test_db.refresh(user) # Ensure user is attached to session
            return user
        except Exception as e:
            # Provide helpful error message for common issues
            test_db.rollback()  # Clean up failed transaction
            raise ValueError(
                f"Failed to create test user: {e}\n"
                f"Data attempted: {user_data}\n"
                f"Common causes:\n"
                f"  • Invalid user_id (user doesn't exist)\n"
                f"  • Invalid field values (check your kwargs)"
            ) from e
    
    return create_user

@pytest.fixture
def asset_factory(test_db, user_factory):
    """
    Factory for creating test assets with custom attributes.
    Returns a function that creates and persists assets.
    """
    from app.db import Asset
    from uuid import uuid4
    
    def create_asset(user_id=None, **kwargs):
        """
        Create a test asset.
        
        Args:
            user_id: Owner of the asset (defaults to test_user)
            **kwargs: Override any asset fields
            
        Returns:
            Asset: Created and persisted asset
            
        Example:
            asset = asset_factory()  # Uses test_user
            asset = asset_factory(user_id=other_user.id, symbol='BTC')
        """
        # Use test_user by default for convenience
        if user_id is None:
            user_id = user_factory().id

        # Generate unique symbol to avoid conflicts
        unique_suffix = uuid4().hex[:6].upper()

        # Provide defaults but allow overrides
        asset_data = {
            'id': uuid4(),
            'name': f'Test Asset {unique_suffix}',
            'symbol': f'TST-{unique_suffix}',
            'sector': 'Testing',
            'average_buy_price': 100.00,
            'quantity': 10,
            'wallet_percentage': 5.00,
            'user_id': user_id  # Must be provided
        }
        # Override defaults with any provided kwargs
        asset_data.update(kwargs)
        
        try:
            asset = Asset(**asset_data)
            test_db.add(asset)
            test_db.commit()
            test_db.refresh(asset)
            return asset
        except Exception as e:
            # Provide helpful error message for common issues
            test_db.rollback()  # Clean up failed transaction
            raise ValueError(
                f"Failed to create test asset: {e}\n"
                f"Data attempted: {asset_data}\n"
                f"Common causes:\n"
                f"  • Invalid user_id (user doesn't exist)\n"
                f"  • Duplicate symbol (if you overrode the symbol)\n"
                f"  • Invalid field values (check your kwargs)"
            ) from e
    
    return create_asset

@pytest.fixture
def transaction_factory(test_db, asset_factory):
    """
    Factory for creating test transactions with custom attributes.
    Returns a function that creates and persists transactions.
    """
    from app.db import Transaction
    from uuid import uuid4
    from app.db import TransactionType
    from datetime import datetime, timezone
    
    def create_transaction(asset_id=None, **kwargs):
        """
        Create a test transaction.
        
        Args:
            asset_id: Asset associated with the transaction (defaults to test_asset)
            **kwargs: Override any transaction fields
            
        Returns:
            Transaction: Created and persisted transaction
            
        Example:
            transaction = transaction_factory()  # Uses test_asset
            transaction = transaction_factory(asset_id=other_asset.id, transaction_type=TransactionType.BUY)
        """
        # Use test_asset by default for convenience
        if asset_id is None:
            asset_id = asset_factory().id

        # Provide defaults but allow overrides
        transaction_data = {
            'id': uuid4(),
            'transaction_type': TransactionType.BUY,
            'quantity': 5,
            'price_per_unit': 100.00,
            'transaction_date': datetime.now(timezone.utc),
            'asset_id': asset_id  # Must be provided
        }
        # Override defaults with any provided kwargs
        transaction_data.update(kwargs)
        
        try:
            transaction = Transaction(**transaction_data)
            test_db.add(transaction)
            test_db.commit()
            test_db.refresh(transaction)
            return transaction
        except Exception as e:
            # Provide helpful error message for common issues
            test_db.rollback()  # Clean up failed transaction
            raise ValueError(
                f"Failed to create test transaction: {e}\n"
                f"Data attempted: {transaction_data}\n"
                f"Common causes:\n"
                f"  • Invalid asset_id (asset doesn't exist)\n"
                f"  • Invalid field values (check your kwargs)"
            ) from e
    
    return create_transaction