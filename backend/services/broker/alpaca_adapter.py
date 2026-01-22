
import logging
from typing import Dict, Any, List, Optional
from backend.services.broker.adapter import BrokerAdapter, OrderRequest, OrderResponse, Position, Holding, OrderStatus, OrderSide, OrderType, ProductType

logger = logging.getLogger(__name__)

class AlpacaAdapter(BrokerAdapter):
    """
    Adapter for Alpaca Trading API.
    """
    
    def __init__(self, api_key: str, api_secret: str, base_url: str = "https://paper-api.alpaca.markets"):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.connected = False
        self.trading_client = None

    async def connect(self, credentials: Dict[str, str] = None) -> bool:
        try:
            from alpaca.trading.client import TradingClient
            self.trading_client = TradingClient(self.api_key, self.api_secret, paper=True) # Default to paper
            account = self.trading_client.get_account()
            if account.status == 'ACTIVE':
                self.connected = True
                logger.info("Connected to Alpaca Trading API")
                return True
            return False
        except Exception as e:
            logger.error(f"Alpaca connection failed: {e}")
            return False

    async def disconnect(self) -> bool:
        self.connected = False
        return True

    async def place_order(self, request: OrderRequest) -> OrderResponse:
        if not self.connected:
            await self.connect()
            
        try:
            from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
            from alpaca.trading.enums import OrderSide as AlpacaSide, TimeInForce
            
            side = AlpacaSide.BUY if request.side == OrderSide.BUY else AlpacaSide.SELL
            
            if request.order_type == OrderType.MARKET:
                order_data = MarketOrderRequest(
                    symbol=request.symbol,
                    qty=request.quantity,
                    side=side,
                    time_in_force=TimeInForce.DAY
                )
            else:
                # Limit order logic
                order_data = LimitOrderRequest(
                    symbol=request.symbol,
                    qty=request.quantity,
                    side=side,
                    time_in_force=TimeInForce.DAY,
                    limit_price=request.price
                )
                
            order = self.trading_client.submit_order(order_data)
            
            return OrderResponse(
                order_id=str(order.id),
                status=order.status,
                symbol=order.symbol,
                side=request.side,
                quantity=float(order.qty) if order.qty else 0,
                message="Order submitted to Alpaca"
            )
        except Exception as e:
            logger.error(f"Alpaca place_order failed: {e}")
            return OrderResponse(
                order_id="FAILED",
                status="REJECTED",
                symbol=request.symbol,
                side=request.side,
                quantity=request.quantity,
                message=str(e)
            )

    # Implement other abstract methods as placeholders to satisfy interface
    async def get_order(self, order_id: str): return None
    async def get_orders(self): return []
    async def get_positions(self): return []
    async def get_holdings(self): return []
    async def get_funds(self): return {"available_cash": 0.0}
    async def modify_order(self, *args, **kwargs): return None
    async def cancel_order(self, order_id: str) -> bool: return False
    async def get_quote(self, symbol: str, exchange: str = "NASDAQ"): return {}
