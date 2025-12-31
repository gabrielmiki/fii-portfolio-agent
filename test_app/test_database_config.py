# test_database_config.py
import pytest
from sqlalchemy import text, inspect
from app.db import engine, Base, User

# test_database_config.py
def test_engine_configuration(test_engine_fixture):
    """Test that the engine is configured correctly."""
    # Check database dialect
    assert test_engine_fixture.url.drivername == "postgresql"
    
    # Check that engine is working
    from sqlalchemy import text
    with test_engine_fixture.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        assert result.scalar() == 1
    
    # Pool might not exist if using NullPool, so check safely
    if hasattr(test_engine_fixture.pool, '_pre_ping'):
        assert test_engine_fixture.pool._pre_ping is True

def test_database_connection(test_engine_fixture):
    """
    Test that we can successfully connect to the database.
    This verifies the connection string and credentials are correct.
    """
    # Try to execute a simple query
    with test_engine_fixture.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        assert result.scalar() == 1


def test_database_url_format():
    """
    Test that the database URL is properly formatted.
    """
    from test_app.conftest import TEST_DATABASE_URL

    assert TEST_DATABASE_URL.startswith("postgresql://")
    assert "test_mydatabase" in TEST_DATABASE_URL


def test_engine_configuration():
    """
    Test that the engine is configured correctly.
    """
    assert engine.pool._pre_ping is True
    assert engine.url.drivername == "postgresql"


def test_tables_creation(test_db):
    """
    Test that all tables defined in models are created correctly.
    This verifies Base.metadata.create_all() works.
    """
    # Get inspector to check database schema
    inspector = inspect(test_db.bind)

    # Get list of table names in the database
    table_names = inspector.get_table_names()

    # Verify expected tables exist
    assert "assets" in table_names
    assert "transactions" in table_names
    assert "users" in table_names


def test_assets_columns(test_db):
    """
    Test that tables have the correct columns.
    This verifies your model definitions match the database schema.
    """
    inspector = inspect(test_db.bind)

    # Get columns for the assets table
    columns = inspector.get_columns("assets")
    column_names = [col["name"] for col in columns]

    # Verify expected columns exist
    assert "id" in column_names
    assert "name" in column_names
    assert "symbol" in column_names
    assert "sector" in column_names
    assert "average_buy_price" in column_names
    assert "quantity" in column_names
    assert "wallet_percentage" in column_names
    assert "user_id" in column_names

    # Verify column types if needed
    id_column = next(col for col in columns if col["name"] == "id")
    name_column = next(col for col in columns if col["name"] == "name")
    symbol_column = next(col for col in columns if col["name"] == "symbol")
    sector_column = next(col for col in columns if col["name"] == "sector")
    average_price_column = next(col for col in columns if col["name"] == "average_buy_price")
    quantity_column = next(col for col in columns if col["name"] == "quantity")
    wallet_percentage_column = next(col for col in columns if col["name"] == "wallet_percentage")
    user_id_column = next(col for col in columns if col["name"] == "user_id")
    assert str(id_column["type"]) == "UUID"
    assert str(name_column["type"]) == "VARCHAR(100)"
    assert str(symbol_column["type"]) == "VARCHAR(10)"
    assert str(sector_column["type"]) == "VARCHAR(50)"
    assert str(average_price_column["type"]) == "NUMERIC(10, 2)"
    assert str(quantity_column["type"]) == "INTEGER"
    assert str(wallet_percentage_column["type"]) == "NUMERIC(5, 2)"
    assert str(user_id_column["type"]) == "UUID"


# def test_foreign_keys(test_db):
#     """
#     Test that foreign key relationships are created correctly.
#     """
#     inspector = inspect(test_db.bind)

#     # Example: if Post has a foreign key to User
#     foreign_keys = inspector.get_foreign_keys("posts")

#     assert len(foreign_keys) > 0
#     # Verify the foreign key points to the right table
#     assert foreign_keys[0]["referred_table"] == "users"