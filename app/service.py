from fastapi import HTTPException, status, Depends
from typing import Annotated
from sqlalchemy.orm import Session
from app.db import Asset, Transaction, User
from app.db import (
    get_db,
    Base,
    engine
)
from uuid import uuid4
import yfinance as yf
from notion_client import Client

class PortfolioService:
    def __init__(self, session: Session):
        self.session = session

    def record_transaction(self, transaction_data: Transaction, user_id: int):
        """
        Records a transaction and automatically updates the Asset portfolio state.
        This entire function runs within the passed SQLModel session.
        """
        
        # 1. Fetch the existing Asset (if any)
        asset = self.session.query(Asset).filter(
            Asset.user_id == user_id,
            Asset.id == transaction_data.asset_id
        ).first()

        # 2. Logic Split: BUY vs SELL
        if transaction_data.transaction_type == "buy":
            self._handle_buy(asset, transaction_data, user_id)
        elif transaction_data.transaction_type == "sell":
            self._handle_sell(asset, transaction_data)
        else:
            raise HTTPException(status_code=400, detail="Invalid transaction type")

        # 3. Save the Transaction Record itself
        # We associate it with the asset *after* we ensure the asset exists
        # (Note: In your logic, you might link transaction to asset_id, so we need to flush asset first)
        
        # If asset was just created, we need to add it to session to get an ID
        # if asset not in self.session: 
        #      self.session.add(asset)
        
        self.session.flush() # Generates asset.id without committing yet

        transaction_data.asset_id = asset.id
        transaction_data.user_id = user_id
        self.session.add(transaction_data)
        
        # 4. Commit happens at the controller level (or here, depending on preference)
        self.session.commit()
        self.session.refresh(transaction_data)
        return transaction_data

    # TODO: Add a get method for fetching the additional data needed for creating an asset
    def _handle_buy(self, asset: Asset | None, transaction_data: Transaction, user_id: int):
        """Calculates Weighted Average Price"""
        if not asset:
            # Case: First time buying this ticker
            new_asset = Asset(
                id=uuid4(),
                symbol="",
                name="", # TODO: GET NAME FROM ANOTHER SERVICE
                sector="Unknown",      # TODO: GET SECTOR FROM ANOTHER SERVICE
                current_price=transaction_data.price_per_unit, # TODO: GET CURRENT PRICE FROM ANOTHER SERVICE
                quantity=transaction_data.quantity,
                average_buy_price=transaction_data.price_per_unit,
                user_id=user_id
            )
            self.session.add(new_asset)
            return

        # Case: Adding to existing position (Standard Weighted Avg Formula)
        current_total_value = float(asset.quantity * asset.average_buy_price)
        new_purchase_value = transaction_data.quantity * transaction_data.price_per_unit
        
        total_quantity = asset.quantity + transaction_data.quantity
        
        # Avoid division by zero (unlikely in buy, but good practice)
        if total_quantity > 0:
            new_average_price = (current_total_value + new_purchase_value) / total_quantity
        else:
            new_average_price = 0.0

        # Update the Asset object (SQLModel tracks these changes)
        asset.quantity = total_quantity
        asset.average_buy_price = round(new_average_price, 2)
        self.session.add(asset)

    def _handle_sell(self, asset: Asset | None, transaction_data: Transaction):
        """Decreases quantity, validates balance. Does NOT change Average Price."""
        if not asset:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot sell {transaction_data.symbol}. You do not own this asset."
            )

        if asset.quantity < transaction_data.quantity:
            raise HTTPException(
                status_code=400, 
                detail=f"Insufficient balance. You have {asset.quantity}, trying to sell {transaction_data.quantity}."
            )

        # Logic: Only quantity changes. Average Price (Cost Basis) remains historic.
        asset.quantity -= transaction_data.quantity
        
        # Cleanup: If quantity reaches 0, you might want to keep the asset record 
        # but show 0 balance, or delete it. Keeping it is usually better for history.
        self.session.add(asset)

    def update_portfolio_percentages(self, user_id: int):
        """
        Updates the wallet_percentage for all assets in the user's portfolio.
        """
        assets = self.session.query(Asset).filter(Asset.user_id == user_id).all()
        
        total_value = sum(float(asset.current_price or 0) * asset.quantity for asset in assets)
        
        if total_value == 0:
            for asset in assets:
                asset.wallet_percentage = 0.0
                self.session.add(asset)
            self.session.commit()
            return

        for asset in assets:
            asset_value = float(asset.current_price or 0) * asset.quantity
            asset.wallet_percentage = round((asset_value / total_value) * 100, 2)
            self.session.add(asset)
        
        self.session.commit()


class MarketDataService:
    def __init__(self, session: Session):
        self.session = session

    def update_all_prices(self, session: Session):
        """
        Iterates through all assets, fetches real-time price, 
        and updates the 'current_price' field.
        """
        assets = self.session.query(Asset).all()
        
        for asset in assets:
            try:
                # yfinance needs '.SA' for Brazilian stocks
                ticker_symbol = f"{asset.symbol}.SA" if not asset.symbol.endswith(".SA") else asset.symbol
                
                # Fetch data
                stock = yf.Ticker(ticker_symbol)
                current_price = stock.fast_info['last_price']
                
                # Update Asset Logic
                asset.current_price = round(current_price, 2)
                
                # Recalculate Profit % based on Average Price
                if asset.average_buy_price > 0:
                    profit = ((current_price - asset.average_buy_price) / asset.average_buy_price) * 100
                    asset.profit_pct = round(profit, 2)

                self.session.add(asset)
            except Exception as e:
                print(f"Error updating {asset.symbol}: {e}")
        
        self.session.commit()
        return {"message": "Prices updated successfully"}

# ===================================================================
# Notion Client Service
# ===================================================================

class NotionSyncService:
    def __init__(self, session: Session, user: User):
        # Inicializa o cliente com o token seguro
        self.client = Client(auth=user.notion_api_key)
        self.database_id = user.notion_database_id
        self.session = session

    def sync_portfolio(self):
        """
        Lê todos os ativos do Banco SQL e espelha no Notion.
        """
        assets = self.session.query(Asset).all()
        results = []

        for asset in assets:
            try:
                # 1. Verifica se o ativo já existe no Notion
                page_id = self._get_page_id_by_symbol(asset.symbol)

                # 2. Monta o payload (os dados formatados para o Notion)
                properties = self._build_properties(asset)

                if page_id:
                    # UPDATE: Se já existe, atualiza
                    self.client.update_page(page_id=page_id, properties=properties)
                    action = "Updated"
                else:
                    # CREATE: Se não existe, cria
                    self.client.create_page(
                        parent={"database_id": self.database_id},
                        properties=properties
                    )
                    action = "Created"
                
                results.append(f"{asset.symbol}: {action}")
            
            except Exception as e:
                print(f"Erro ao sincronizar {asset.symbol}: {e}")
                results.append(f"{asset.symbol}: Failed")

        return results

    def _get_page_id_by_symbol(self, symbol: str) -> str | None:
        """
        Busca no Notion se existe uma linha com esse Symbol.
        Retorna o ID da página ou None.
        """
        response = self.client.databases.query(
            database_id=self.database_id,
            filter={
                "property": "Symbol",
                "title": {
                    "equals": symbol
                }
            }
        )
        results = response.get("results")
        if results:
            return results[0]["id"]
        return None

    def _build_properties(self, asset: Asset) -> dict:
        """
        Transforma o objeto Asset do Python no JSON que o Notion exige.
        """
        return {
            "Symbol": {
                "title": [{"text": {"content": asset.symbol}}]
            },
            "Quantity": {
                "number": asset.quantity
            },
            "Current Price": {
                "number": asset.current_price if asset.current_price else 0.0
            },
            "Profit %": {
                # O Notion espera frações para porcentagem (10% = 0.1)
                "number": (asset.profit_pct / 100) if asset.profit_pct else 0.0
            }
        }