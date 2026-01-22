"""
Broker Adapter Interface
Abstract base class for broker integrations (OpenAlgo-style).
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import BaseModel
from datetime import datetime

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"          # Stop Loss
    SL_M = "SL-M"      # Stop Loss Market

class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class ProductType(str, Enum):
    CNC = "CNC"        # Cash and Carry (Delivery)
    MIS = "MIS"        # Intraday
    NRML = "NRML"      # Normal (F&O)

class OrderStatus(str, Enum):
    PENDING = "PENDING"
    OPEN = "OPEN"
    COMPLETE = "COMPLETE"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"

class Order(BaseModel):
    order_id: str
    symbol: str
    exchange: str = "NSE"
    side: OrderSide
    order_type: OrderType
    product: ProductType
    quantity: int
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    average_price: float = 0
    placed_at: datetime = None
    updated_at: datetime = None
    message: str = ""

class OrderRequest(BaseModel):
    symbol: str
    side: OrderSide
    quantity: int
    product: Optional[ProductType] = None  # Optional, adapter can default
    order_type: Optional[OrderType] = OrderType.MARKET
    price: Optional[float] = None
    stop_price: Optional[float] = None
    exchange: str = "NSE"

class OrderResponse(BaseModel):
    order_id: str
    status: str
    symbol: str
    side: str
    quantity: int
    message: Optional[str] = None

class Position(BaseModel):
    symbol: str
    exchange: str = "NSE"
    product: ProductType
    quantity: int
    average_price: float
    last_price: float
    pnl: float
    pnl_percent: float

class Holding(BaseModel):
    symbol: str
    exchange: str = "NSE"
    quantity: int
    average_price: float
    last_price: float
    pnl: float

class BrokerAdapter(ABC):
    """
    Abstract broker adapter interface.
    All broker implementations must inherit from this.
    """
    
    @abstractmethod
    def connect(self, credentials: Dict[str, str]) -> bool:
        """Connect to the broker API."""
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """Disconnect from the broker API."""
        pass
    
    @abstractmethod
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
        """Place a new order."""
        pass
    
    @abstractmethod
    def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        order_type: Optional[OrderType] = None
    ) -> Order:
        """Modify an existing order."""
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        pass
    
    @abstractmethod
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order details."""
        pass
    
    @abstractmethod
    def get_orders(self) -> List[Order]:
        """Get all orders for the day."""
        pass
    
    @abstractmethod
    def get_positions(self) -> List[Position]:
        """Get current positions."""
        pass
    
    @abstractmethod
    def get_holdings(self) -> List[Holding]:
        """Get holdings (long-term)."""
        pass
    
    @abstractmethod
    def get_funds(self) -> Dict[str, float]:
        """Get available funds/margins."""
        pass
    
    @abstractmethod
    def get_quote(self, symbol: str, exchange: str = "NSE") -> Dict[str, Any]:
        """Get real-time quote for a symbol."""
        pass
