# FII Tracker — Agentic Portfolio Backend

A containerized backend for tracking and managing Brazilian Real Estate Investment Funds (FIIs). Built with **FastAPI** and **SQLAlchemy**, it exposes a RESTful API for full portfolio lifecycle management — from registering assets and logging transactions to refreshing live market prices via **yfinance** and syncing portfolios to **Notion**.

---

## Screenshots

### Login & Sign Up

| Login | Sign Up |
|-------|---------|
| ![Login](docs/login.png) | ![Sign Up](docs/signup.png) |

### Portfolio Dashboard

| Portfolio | Updated Portfolio | Portfolio Updated Refreshed |
|-------|---------|---------|
| ![Portfolio](docs/portfolio.png) | ![Updated Portfolio](docs/updated_portfolio.png) | ![Portfolio Updated Refreshed](docs/portfolio_updated_refreshed.png) |

Live P&L, sector allocation breakdown, and per-asset trend sparklines.

### Transactions

| Transactions | Transactions Updated |
|-------|-------|
| ![Transactions](docs/transactions.png) | ![Transactions Updated](docs/transaction_updated.png) |

Full buy/sell history with timestamped records per asset.

### Modals

| Add FII Asset | New Transaction |
|---------------|-----------------|
| ![Add Asset](docs/add_fii_popup.png) | ![New Transaction](docs/transaction_popup.png) |

---

## Features

- **Portfolio Management** — Add, view, update, and delete FII assets with CRUD endpoints
- **Transaction Tracking** — Record buy/sell operations per asset with quantity, price, and date
- **Live Market Prices** — Background refresh via `yfinance` (`.SA` suffix for Brazilian FIIs)
- **Notion Sync** — One-click background sync of the full portfolio to a linked Notion database
- **Sector Allocation** — Automatic wallet percentage calculation per sector
- **P&L Calculation** — Unrealized profit/loss computed from average buy price vs. current price
- **Single-file Frontend** — Zero-dependency HTML/CSS/JS frontend, open directly in any browser

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API Framework | FastAPI + Uvicorn |
| ORM / Validation | SQLAlchemy + Pydantic |
| Database | PostgreSQL |
| Market Data | yfinance |
| Notion Integration | notion-client |
| Testing | Pytest + transaction rollback fixtures |
| Frontend | Vanilla HTML/CSS/JS (single file) |

---

## Project Structure

```
fii-portfolio-agent/
├── app/
│   ├── app.py          # FastAPI app, middleware, router registration
│   ├── db.py           # SQLAlchemy models (User, Asset, Transaction)
│   ├── schema.py       # Pydantic request/response schemas
│   ├── service.py      # Business logic (PortfolioService, MarketDataService, NotionSyncService)
│   └── routers/
│       ├── assets.py       # /assets endpoints
│       ├── auth.py         # /users endpoints
│       ├── transactions.py # /transactions endpoints
│       ├── refresh.py      # /refresh endpoint
│       └── portfolio.py    # /sync/notion endpoint
├── main.py             # Uvicorn entrypoint
├── fii_tracker.html    # Single-file frontend
└── requirements.txt
```

---

## API Reference

### Assets

| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| `GET` | `/assets/portfolio/` | 200 | Retrieve all assets with totals and current values |
| `POST` | `/assets/assets/` | 201 | Add a new FII asset to the portfolio |
| `PUT` | `/assets/assets/{id}` | 200 | Update an existing asset |
| `DELETE` | `/assets/assets/{id}` | 204 | Remove an asset and all linked transactions |

### Users

| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| `POST` | `/users/users/` | 201 | Create a new user with optional Notion credentials |
| `GET` | `/users/users/` | 200 | Retrieve all users |
| `GET` | `/users/users/{user_id}` | 200 | Retrieve a specific user by UUID |
| `DELETE` | `/users/users/{user_id}` | 204 | Delete a user and all their assets (cascade) |

### Transactions

| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| `POST` | `/transactions/transactions/` | 201 | Record a buy or sell transaction |
| `GET` | `/transactions/transactions/` | 200 | Retrieve all transactions |
| `GET` | `/transactions/transactions/{id}` | 200 | Retrieve a single transaction |
| `PUT` | `/transactions/transactions/{id}` | 200 | Update a transaction |
| `DELETE` | `/transactions/transactions/{id}` | 204 | Delete a transaction |

### Market Data & Notion

| Method | Endpoint | Status | Description |
|--------|----------|--------|-------------|
| `POST` | `/refresh` | 202 | Trigger background price refresh for all assets |
| `POST` | `/sync/notion` | 200 | Trigger background portfolio sync to Notion |

> `/refresh` returns `202 Accepted` immediately. Price fetching runs fully in the background via `FastAPI BackgroundTasks`.

---

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL running locally (or via Docker)

### 1. Clone and install dependencies

```bash
git clone https://github.com/your-username/fii-portfolio-agent.git
cd fii-portfolio-agent
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure the database

Edit the connection string in `app/db.py`:

```python
DATABASE_URL = "postgresql://myuser:mypassword@localhost:5432/mydatabase"
```

Or set it via environment variable and load with `python-dotenv`.

### 3. Run the backend

```bash
python main.py
```

The API will be available at `http://localhost:8000`.  
Interactive docs at `http://localhost:8000/docs`.

### 4. Open the frontend

Open `fii_tracker.html` directly in your browser — no build step or server required.

---

## Database Schema

```
User
├── id (UUID, PK)
├── email (unique)
├── notion_database_id (nullable)
└── notion_api_key (nullable)

Asset
├── id (UUID, PK)
├── symbol (unique)
├── name
├── sector
├── average_buy_price
├── current_price (nullable)
├── quantity
├── wallet_percentage (nullable)
├── profit_pct (nullable)
└── user_id (FK → User, cascade delete)

Transaction
├── id (UUID, PK)
├── transaction_type (buy | sell)
├── quantity
├── price_per_unit
├── transaction_date
└── asset_id (FK → Asset, cascade delete)
```

---

## Testing

The test suite uses a **transaction rollback** strategy: tables are created once per session, and each test runs inside a transaction that is rolled back on completion — giving full isolation without the overhead of recreating the database on every test.

```bash
pytest
```

---

## Notion Integration

To enable portfolio sync:

1. Create a Notion integration at [notion.so/my-integrations](https://www.notion.so/my-integrations) and copy the API key (`secret_...`)
2. Share your Notion database with the integration
3. Copy the database ID from the URL (`notion.so/.../<database_id>?v=...`)
4. Provide both values when creating your account in the frontend

Once configured, click **⬡ Sync Notion** in the dashboard header to push the full portfolio to Notion.

---

## Author

**Gabriel de Almeida Miki**  
Production Engineering (USP São Carlos) · M.Sc. Computer Engineering (Politecnico di Milano)  
[LinkedIn](https://linkedin.com/in/gabriel-miki) · [GitHub](https://github.com/gabriel-miki)
