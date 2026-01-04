from app.db import User, Asset, Transaction, TransactionType
import pytest
from uuid import uuid4

# ====================================================================================
# Test User Endpoints
# ====================================================================================

def test_user_fixture_works(test_db, user_factory):
    """Debug test: verify user_factory creates a user"""
    test_user = user_factory()
    print(f"\n🔍 Test user ID: {test_user.id}")
    print(f"🔍 Test user email: {test_user.email}")
    
    # Verify user exists in database
    found_user = test_db.query(User).filter(User.id == test_user.id).first()
    assert found_user is not None
    assert found_user.email == test_user.email
    print("✅ User found in database!")

def test_create_user(client):
	"""Test creating an user with a valid user"""
	user_data = {
		"email": "test@example.com",
		"notion_database_id": "test-create-user",
		"notion_api_key": "test-create-user-key"
	}

	response = client.post("/users/users/", json=user_data)

	assert response.status_code == 201

def test_create_repeated_user(client, user_factory):
    """Test creating a user with an email that already exists"""
    existing_user = user_factory(email="test@example.com")

    user_data = {
        "email": "test@example.com",
        "notion_database_id": "test-create-user",
        "notion_api_key": "test-create-user-key"
    }

    response = client.post("/users/users/", json=user_data)

    assert response.status_code == 409

def test_client_sees_user(client, test_db, user_factory):
    """Debug test: verify client can see the test user"""
    test_user = user_factory()
    print(f"\n🔍 Test user ID: {test_user.id}")
    
    # Check if user is in the session
    from app.db import User
    user_in_db = test_db.query(User).filter(User.id == test_user.id).first()
    print(f"🔍 User in test_db: {user_in_db is not None}")
    
    # Check all users in the database
    all_users = test_db.query(User).all()
    print(f"🔍 Total users in test_db: {len(all_users)}")
    for u in all_users:
        print(f"   - {u.id}: {u.email}")
    
    # Try to get the user via API
    response = client.get(f"/users/users/{test_user.id}")
    print(f"🔍 Response status: {response.status_code}")
    print(f"🔍 Response body: {response.json()}")
    
    assert response.status_code == 200

# ====================================================================================
# Test Transactions Endpoints
# ====================================================================================

def test_transaction_fixture_works(test_db, transaction_factory):
    """Debug test: verify transaction_factory creates a transaction"""
    test_transaction = transaction_factory()
    
    # Verify transaction exists in database
    found_transaction = test_db.query(Transaction).filter(Transaction.id == test_transaction.id).first()
    assert found_transaction is not None
    assert found_transaction.id == test_transaction.id

def test_create_transaction_with_asset(client, asset_factory):
    """Test creating a transaction with a valid asset"""
    test_asset = asset_factory()
    transaction_data = {
        "transaction_type": "buy",
        "quantity": 50,
        "price_per_unit": 150.00,
        "asset_id": str(test_asset.id)
    }
    
    response = client.post("/transactions/transactions/", json=transaction_data)
    
    assert response.status_code == 201

def test_create_repeated_transaction(client, transaction_factory, asset_factory):
    """Test creating a transaction with the same data"""
    test_asset = asset_factory()
    existing_transaction = transaction_factory(
        transaction_type="buy",
        quantity=50,
        price_per_unit=150.00,
        transaction_date="2024-01-01T10:00:00Z",
        asset_id=test_asset.id
    )

    transaction_data = {
        "transaction_type": "buy",
        "quantity": 50,
        "price_per_unit": 150.00,
        "transaction_date": "2024-01-01T10:00:00Z",
        "asset_id": str(test_asset.id)
    }

    response = client.post("/transactions/transactions/", json=transaction_data)

    assert response.status_code == 201  # Assuming duplicates are allowed

def test_create_invalid_transaction(client):
    """Test creating a transaction with an invalid asset"""
    transaction_data = {
        "transaction_type": "buy",
        "quantity": 50,
        "price_per_unit": 150.00,
        "transaction_date": "2024-01-01T10:00:00Z",
        "asset_id": str(uuid4())
    }
    
    response = client.post("/transactions/transactions/", json=transaction_data)

    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    assert response.status_code == 400

def test_delete_transaction(client, transaction_factory):
    """Test deleting a transaction"""
    test_transaction = transaction_factory()
    
    response = client.delete(f"/transactions/transactions/{test_transaction.id}")
    
    assert response.status_code == 204
    
    # Verify transaction is deleted
    get_response = client.get(f"/transactions/transactions/{test_transaction.id}")
    assert get_response.status_code == 404

def test_update_transaction(client, transaction_factory):
    """Test updating a transaction"""
    test_transaction = transaction_factory()
    
    update_data = {
        "quantity": 200,
        "price_per_unit": 145.00
    }
    
    response = client.put(
        f"/transactions/transactions/{test_transaction.id}",
        json=update_data
    )
    
    assert response.status_code == 200
    updated_transaction = response.json()
    assert updated_transaction["quantity"] == 200
    assert updated_transaction["price_per_unit"] == 145.00

# ====================================================================================
# Test Asset Endpoints 
# ====================================================================================

def test_asset_fixture_works(test_db, asset_factory):
    """Debug test: verify asset_factory creates an asset"""
    test_asset = asset_factory()
    
    # Verify asset exists in database
    found_asset = test_db.query(Asset).filter(Asset.id == test_asset.id).first()
    assert found_asset is not None
    assert found_asset.symbol == test_asset.symbol

def test_create_asset_with_user(client, user_factory):
    """Test creating an asset with a valid user"""
    test_user = user_factory()
    asset_data = {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "sector": "Technology",
        "average_buy_price": 150.50,
        "current_price": 155.00,
        "quantity": 100,
        "user_id": str(test_user.id)
    }
    
    response = client.post("/assets/assets/", json=asset_data)
    
    assert response.status_code == 201

def test_create_repeated_asset(client, asset_factory, user_factory):
    """Test creating an asset with a symbol that already exists"""
    test_user = user_factory()
    existing_asset = asset_factory(symbol="AAPL", user_id=test_user.id)

    asset_data = {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "sector": "Technology",
        "average_buy_price": 150.50,
        "current_price": 155.00,
        "quantity": 100,
        "user_id": str(test_user.id)
    }

    response = client.post("/assets/assets/", json=asset_data)

    assert response.status_code == 409

# ====================================================================================
# Test Market Data Refresh Endpoint
# ====================================================================================

@pytest.mark.endpoints
def test_refresh_market_data_endpoint(client):
    """Test the /refresh endpoint to trigger market data refresh"""
    response = client.post("/refresh")
    
    assert response.status_code == 202
    assert response.json() == {"message": "Market data refresh initiated in the background."}