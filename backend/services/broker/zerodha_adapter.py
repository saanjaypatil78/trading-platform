"""
Zerodha Kite Connect Broker Adapter
Implementation of BrokerAdapter for Indian Markets.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from kiteconnect import KiteConnect

from .adapter import BrokerAdapter, Order, Position, Holding, OrderStatus, OrderType, OrderSide, ProductType

logger = logging.getLogger(__name__)

class ZerodhaAdapter(BrokerAdapter):
    def __init__(self):
        self.kite: Optional[KiteConnect] = None

    def connect(self, credentials: Dict[str, Any]) -> bool:
        try:
            self.kite = KiteConnect(api_key=credentials["api_key"])
            if "access_token" in credentials:
                self.kite.set_access_token(credentials["access_token"])
            else:
                # Normal flow would require redirect -> request_token -> access_token
                # For this implementation, we assume token is provided or handled via OAuth flow
                logger.warning("[Zerodha] Access token missing. Re-authentication might be required.")
            
            # Simple check
            self.kite.profile()
            return True
        except Exception as e:
            logger.error(f"[Zerodha] Connection failed: {e}")
            return False

    def disconnect(self) -> bool:
        self.kite = None
        return True

    def place_order(
        self,
        symbol: str,
        side: OrderSide,
        quantity: int,
        order_type: OrderType = OrderType.MARKET,
        product: ProductType = ProductType.MIS,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        exchange: str = "NSE"
    ) -> Order:
        if not self.kite:
            raise Exception("Zerodha not connected")

        # Map types
        z_side = self.kite.TRANSACTION_TYPE_BUY if side == OrderSide.BUY else self.kite.TRANSACTION_TYPE_SELL
        z_type = {
            OrderType.MARKET: self.kite.ORDER_TYPE_MARKET,
            OrderType.LIMIT: self.kite.ORDER_TYPE_LIMIT,
            OrderType.SL: self.kite.ORDER_TYPE_SL,
            OrderType.SL_M: self.kite.ORDER_TYPE_SLM
        }.get(order_type, self.kite.ORDER_TYPE_MARKET)
        
        z_product = {
            ProductType.CNC: self.kite.PRODUCT_CNC,
            ProductType.MIS: self.kite.PRODUCT_MIS,
            ProductType.NRML: self.kite.PRODUCT_NRML
        }.get(product, self.kite.PRODUCT_MIS)

        order_id = self.kite.place_order(
            variety=self.kite.VARIETY_REGULAR,
            exchange=exchange,
            tradingsymbol=symbol,
            transaction_type=z_side,
            quantity=quantity,
            product=z_product,
            order_type=z_type,
            price=price,
            trigger_price=trigger_price
        )

        # Fetch the placed order to return full details
        z_orders = self.kite.orders()
        for o in z_orders:
            if o["order_id"] == order_id:
                return self._map_order(o)
        
        # Fallback if not found in recent (unlikely)
        return Order(
            order_id=order_id, symbol=symbol, side=side, 
            order_type=order_type, product=product, quantity=quantity, status=OrderStatus.PENDING
        )

    def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        order_type: Optional[OrderType] = None
    ) -> Order:
        z_type = {
            OrderType.MARKET: self.kite.ORDER_TYPE_MARKET,
            OrderType.LIMIT: self.kite.ORDER_TYPE_LIMIT,
            OrderType.SL: self.kite.ORDER_TYPE_SL,
            OrderType.SL_M: self.kite.ORDER_TYPE_SLM
        }.get(order_type) if order_type else None

        self.kite.modify_order(
            variety=self.kite.VARIETY_REGULAR,
            order_id=order_id,
            quantity=quantity,
            price=price,
            trigger_price=trigger_price,
            order_type=z_type
        )
        return self.get_order(order_id)

    def cancel_order(self, order_id: str) -> bool:
        self.kite.cancel_order(variety=self.kite.VARIETY_REGULAR, order_id=order_id)
        return True

    def get_order(self, order_id: str) -> Optional[Order]:
        orders = self.kite.orders()
        for o in orders:
            if o["order_id"] == order_id:
                return self._map_order(o)
        return None

    def get_orders(self) -> List[Order]:
        z_orders = self.kite.orders()
        return [self._map_order(o) for o in z_orders]

    def get_positions(self) -> List[Position]:
        res = self.kite.positions()
        net_positions = res["net"]
        day_positions = res["day"]
        
        positions = []
        for p in net_positions + day_positions:
            # Simple mapping
            positions.append(Position(
                symbol=p["tradingsymbol"],
                exchange=p["exchange"],
                product=ProductType.CNC if p["product"] == "CNC" else ProductType.MIS,
                quantity=p["quantity"],
                average_price=p["average_price"],
                last_price=p["last_price"],
                pnl=p["pnl"],
                pnl_percent=(p["pnl"] / (p["average_price"] * p["quantity"] + 1e-6)) * 100
            ))
        return positions

    def get_holdings(self) -> List[Holding]:
        z_holdings = self.kite.holdings()
        return [Holding(
            symbol=h["tradingsymbol"],
            exchange=h["exchange"],
            quantity=h["quantity"],
            average_price=h["average_price"],
            last_price=h["last_price"],
            pnl=h["pnl"]
        ) for h in z_holdings]

    def get_funds(self) -> Dict[str, float]:
        margins = self.kite.margins()
        # Simplified for equity
        equity = margins.get("equity", {})
        return {
            "available": float(equity.get("available", {}).get("cash", 0)),
            "used": float(equity.get("used", {}).get("debit", 0)),
            "total": float(equity.get("available", {}).get("cash", 0)) + float(equity.get("used", {}).get("debit", 0))
        }

    def get_quote(self, symbol: str, exchange: str = "NSE") -> Dict[str, Any]:
        key = f"{exchange}:{symbol}"
        q = self.kite.quote(key).get(key, {})
        return {
            "symbol": symbol,
            "lp": q.get("last_price"),
            "ohlc": q.get("ohlc"),
            "volume_traded": q.get("volume"),
            "timestamp": q.get("timestamp")
        }

    def _map_order(self, o: Dict[str, Any]) -> Order:
        status_map = {
            "PUT ORDER REQ RECEIVED": OrderStatus.PENDING,
            "VALIDATION PENDING": OrderStatus.PENDING,
            "OPEN PENDING": OrderStatus.PENDING,
            "OPEN": OrderStatus.OPEN,
            "COMPLETE": OrderStatus.COMPLETE,
            "CANCELLED": OrderStatus.CANCELLED,
            "REJECTED": OrderStatus.REJECTED,
        }
        
        return Order(
            order_id=o["order_id"],
            symbol=o["tradingsymbol"],
            exchange=o["exchange"],
            side=OrderSide.BUY if o["transaction_type"] == "BUY" else OrderSide.SELL,
            order_type=OrderType.LIMIT if "LIMIT" in o["order_type"] else OrderType.MARKET,
            product=ProductType.CNC if o["product"] == "CNC" else ProductType.MIS,
            quantity=o["quantity"],
            price=o["price"],
            status=status_map.get(o["status"], OrderStatus.PENDING),
            filled_quantity=o["filled_quantity"],
            average_price=o["average_price"],
            placed_at=o["order_timestamp"],
            updated_at=o["exchange_timestamp"],
            message=o.get("status_message", "")
        )
