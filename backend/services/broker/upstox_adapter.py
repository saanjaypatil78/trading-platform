"""
Upstox Broker Adapter
Implementation of BrokerAdapter for Upstox API.
"""
import logging
from typing import Dict, Any, List, Optional
import asyncio
from upstox_client import (
    Configuration, 
    ApiClient, 
    OrderApi, 
    PortfolioApi, 
    UserApi,
    PlaceOrderRequest,
    ModifyOrderRequest
)
from backend.services.broker.adapter import BrokerAdapter, OrderRequest, OrderResponse, Position, Holding

logger = logging.getLogger(__name__)

class UpstoxAdapter(BrokerAdapter):
    """
    Adapter for Upstox API (Indian Markets).
    """
    
    def __init__(self, api_key: str, api_secret: str, redirect_uri: str, access_token: Optional[str] = None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.redirect_uri = redirect_uri
        self.access_token = access_token
        
        self.config = Configuration()
        if self.access_token:
            self.config.access_token = self.access_token
        
        self.api_client = ApiClient(self.config)
        self.order_api = OrderApi(self.api_client)
        self.portfolio_api = PortfolioApi(self.api_client)
        self.user_api = UserApi(self.api_client)
        self.connected = bool(self.access_token)

    async def connect(self) -> bool:
        """Connect to Upstox. Assumes access_token is already set or handled via OAuth."""
        if not self.access_token:
            logger.error("Upstox access token missing. Please authenticate via OAuth.")
            return False
        
        try:
            # Test connection by getting profile
            profile = self.user_api.get_profile("2.0")
            logger.info(f"Connected to Upstox. User: {profile.data.user_name}")
            self.connected = True
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Upstox: {e}")
            return False

    async def disconnect(self) -> bool:
        self.connected = False
        return True

    async def place_order(self, request: OrderRequest) -> OrderResponse:
        if not self.connected:
            raise ConnectionError("Upstox not connected")
        
        try:
            # Map product types
            product_map = {
                "MIS": "I",
                "CNC": "D",
                "INTRADAY": "I",
                "DELIVERY": "D"
            }
            product_code = product_map.get(request.product.upper(), "I") if request.product else "I"

            order_data = PlaceOrderRequest(
                quantity=request.quantity,
                product=product_code,
                validity="DAY",
                price=request.price or 0.0,
                tag="Antigravity",
                instrument_token=request.symbol, # Upstox uses tokens usually, need mapping
                order_type=request.order_type or "MARKET",
                transaction_type=request.side.upper(),
                disclosed_quantity=0,
                trigger_price=request.stop_price or 0.0,
                is_amo=False
            )
            
            response = self.order_api.place_order(order_data, "2.0")
            
            return OrderResponse(
                order_id=response.data.order_id,
                status="SUBMITTED",
                symbol=request.symbol,
                side=request.side,
                quantity=request.quantity,
                message="Order placed successfully via Upstox"
            )
        except Exception as e:
            logger.error(f"Upstox place_order failed: {e}")
            return OrderResponse(
                order_id="FAILED",
                status="REJECTED",
                symbol=request.symbol,
                side=request.side,
                quantity=request.quantity,
                message=str(e)
            )

    async def cancel_order(self, order_id: str) -> bool:
        try:
            self.order_api.cancel_order(order_id, "2.0")
            return True
        except Exception as e:
            logger.error(f"Upstox cancel_order failed: {e}")
            return False

    async def get_positions(self) -> List[Position]:
        try:
            response = self.portfolio_api.get_positions("2.0")
            positions = []
            for p in response.data:
                positions.append(Position(
                    symbol=p.tradingsymbol,
                    quantity=int(p.quantity),
                    entry_price=float(p.average_price),
                    current_price=float(p.last_price),
                    pnl=float(p.pnl)
                ))
            return positions
        except Exception as e:
            logger.error(f"Upstox get_positions failed: {e}")
            return []

    async def get_holdings(self) -> List[Holding]:
        try:
            response = self.portfolio_api.get_holdings("2.0")
            holdings = []
            for h in response.data:
                holdings.append(Holding(
                    symbol=h.tradingsymbol,
                    quantity=int(h.quantity),
                    average_price=float(h.average_price),
                    market_value=float(h.last_price) * int(h.quantity)
                ))
            return holdings
        except Exception as e:
            logger.error(f"Upstox get_holdings failed: {e}")
            return []

    async def get_funds(self) -> Dict[str, float]:
        try:
            response = self.user_api.get_user_fund_margin("2.0")
            equity_funds = response.data.equity
            return {
                "available_cash": float(equity_funds.available_margin),
                "used_margin": float(equity_funds.used_margin),
                "total_collateral": float(equity_funds.collateral) if hasattr(equity_funds, 'collateral') else 0.0
            }
        except Exception as e:
            logger.error(f"Upstox get_funds failed: {e}")
            return {"available_cash": 0.0, "used_margin": 0.0}

    async def get_order(self, order_id: str) -> Optional[Any]:
        # Placeholder for now
        return None

    async def get_orders(self) -> List[Any]:
        try:
            response = self.order_api.get_order_book("2.0")
            # Return raw or mapped orders. For now, return raw list to satisfy interface
            return response.data or []
        except:
            return []

    async def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        order_type: Optional[Any] = None
    ) -> Any:
        # Placeholder
        return None

    async def get_quote(self, symbol: str, exchange: str = "NSE") -> Dict[str, Any]:
        # Implementation via UpstoxProvider is preferred, but here is a stub
        return {}
