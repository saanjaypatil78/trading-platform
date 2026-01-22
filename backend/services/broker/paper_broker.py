"""
Paper Broker Implementation
Simulates broker functionality for testing without real money.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
import random

from .adapter import (
    BrokerAdapter, Order, Position, Holding,
    OrderType, OrderSide, ProductType, OrderStatus
)

class PaperBroker(BrokerAdapter):
    """
    Paper trading broker implementation.
    Simulates order execution with realistic fills, slippage, and commissions.
    """
    
    def __init__(self, initial_capital: float = 1000000):
        self.is_connected = False
        self.capital = initial_capital
        self.available_cash = initial_capital
        
        self.orders: Dict[str, Order] = {}
        self.positions: Dict[str, Position] = {}
        self.holdings: Dict[str, Holding] = {}
        
        # Simulation parameters
        self.slippage_percent = 0.05  # 0.05%
        self.commission_per_order = 20  # Rs 20 per order
    
    def connect(self, credentials: Dict[str, str]) -> bool:
        """Simulated connection - always succeeds."""
        self.is_connected = True
        return True
    
    def disconnect(self) -> bool:
        self.is_connected = False
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
        """Place and simulate order execution."""
        order_id = str(uuid.uuid4())[:8].upper()
        now = datetime.now()
        
        # Get simulated market price
        market_price = self._get_simulated_price(symbol)
        
        # Calculate fill price with slippage
        slippage = market_price * (self.slippage_percent / 100)
        if side == OrderSide.BUY:
            fill_price = market_price + slippage
        else:
            fill_price = market_price - slippage
        
        # For limit orders, check if executable
        if order_type == OrderType.LIMIT and price:
            if side == OrderSide.BUY and price < market_price:
                # Limit buy below market - pending
                order = Order(
                    order_id=order_id,
                    symbol=symbol,
                    exchange=exchange,
                    side=side,
                    order_type=order_type,
                    product=product,
                    quantity=quantity,
                    price=price,
                    trigger_price=trigger_price,
                    status=OrderStatus.OPEN,
                    placed_at=now,
                    updated_at=now,
                    message="Limit order placed, waiting for execution"
                )
                self.orders[order_id] = order
                return order
            elif side == OrderSide.SELL and price > market_price:
                # Limit sell above market - pending
                order = Order(
                    order_id=order_id,
                    symbol=symbol,
                    exchange=exchange,
                    side=side,
                    order_type=order_type,
                    product=product,
                    quantity=quantity,
                    price=price,
                    trigger_price=trigger_price,
                    status=OrderStatus.OPEN,
                    placed_at=now,
                    updated_at=now,
                    message="Limit order placed, waiting for execution"
                )
                self.orders[order_id] = order
                return order
            else:
                fill_price = price
        
        # Check funds for buy orders
        order_value = fill_price * quantity
        if side == OrderSide.BUY:
            total_cost = order_value + self.commission_per_order
            if total_cost > self.available_cash:
                order = Order(
                    order_id=order_id,
                    symbol=symbol,
                    exchange=exchange,
                    side=side,
                    order_type=order_type,
                    product=product,
                    quantity=quantity,
                    price=price,
                    status=OrderStatus.REJECTED,
                    placed_at=now,
                    updated_at=now,
                    message=f"Insufficient funds. Required: {total_cost:.2f}, Available: {self.available_cash:.2f}"
                )
                self.orders[order_id] = order
                return order
            
            self.available_cash -= total_cost
        
        # Execute the order
        order = Order(
            order_id=order_id,
            symbol=symbol,
            exchange=exchange,
            side=side,
            order_type=order_type,
            product=product,
            quantity=quantity,
            price=price,
            trigger_price=trigger_price,
            status=OrderStatus.COMPLETE,
            filled_quantity=quantity,
            average_price=fill_price,
            placed_at=now,
            updated_at=now,
            message="Order executed successfully"
        )
        
        self.orders[order_id] = order
        
        # Update positions
        self._update_position(symbol, exchange, product, side, quantity, fill_price)
        
        return order
    
    def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        order_type: Optional[OrderType] = None
    ) -> Order:
        """Modify an existing open order."""
        if order_id not in self.orders:
            raise ValueError(f"Order {order_id} not found")
        
        order = self.orders[order_id]
        
        if order.status != OrderStatus.OPEN:
            raise ValueError(f"Cannot modify order in {order.status} status")
        
        if quantity:
            order.quantity = quantity
        if price:
            order.price = price
        if trigger_price:
            order.trigger_price = trigger_price
        if order_type:
            order.order_type = order_type
        
        order.updated_at = datetime.now()
        order.message = "Order modified"
        
        return order
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an open order."""
        if order_id not in self.orders:
            return False
        
        order = self.orders[order_id]
        
        if order.status != OrderStatus.OPEN:
            return False
        
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.now()
        order.message = "Order cancelled by user"
        
        return True
    
    def get_order(self, order_id: str) -> Optional[Order]:
        return self.orders.get(order_id)
    
    def get_orders(self) -> List[Order]:
        return list(self.orders.values())
    
    def get_positions(self) -> List[Position]:
        return list(self.positions.values())
    
    def get_holdings(self) -> List[Holding]:
        return list(self.holdings.values())
    
    def get_funds(self) -> Dict[str, float]:
        return {
            "total_capital": self.capital,
            "available_cash": self.available_cash,
            "used_margin": self.capital - self.available_cash,
            "collateral": 0
        }
    
    def get_quote(self, symbol: str, exchange: str = "NSE") -> Dict[str, Any]:
        price = self._get_simulated_price(symbol)
        return {
            "symbol": symbol,
            "exchange": exchange,
            "last_price": price,
            "bid": price * 0.9999,
            "ask": price * 1.0001,
            "volume": random.randint(100000, 5000000),
            "open": price * random.uniform(0.98, 1.02),
            "high": price * random.uniform(1.0, 1.03),
            "low": price * random.uniform(0.97, 1.0),
            "close": price
        }
    
    def _get_simulated_price(self, symbol: str) -> float:
        """Generate a simulated price for a symbol."""
        # Use hash of symbol for consistent pricing
        base_hash = hash(symbol) % 10000
        return 500 + (base_hash / 10)  # Price between 500-1500
    
    def _update_position(
        self,
        symbol: str,
        exchange: str,
        product: ProductType,
        side: OrderSide,
        quantity: int,
        price: float
    ):
        """Update position after order execution."""
        key = f"{symbol}_{exchange}_{product}"
        
        if key in self.positions:
            pos = self.positions[key]
            if side == OrderSide.BUY:
                # Add to position
                total_qty = pos.quantity + quantity
                total_value = (pos.quantity * pos.average_price) + (quantity * price)
                pos.quantity = total_qty
                pos.average_price = total_value / total_qty if total_qty else 0
            else:
                # Reduce position
                pos.quantity -= quantity
                if pos.quantity <= 0:
                    # Close position, credit funds
                    pnl = (price - pos.average_price) * quantity
                    self.available_cash += (quantity * price) + pnl
                    del self.positions[key]
                    return
            
            # Update P&L
            pos.last_price = price
            pos.pnl = (price - pos.average_price) * pos.quantity
            pos.pnl_percent = ((price - pos.average_price) / pos.average_price) * 100
        else:
            # New position
            self.positions[key] = Position(
                symbol=symbol,
                exchange=exchange,
                product=product,
                quantity=quantity if side == OrderSide.BUY else -quantity,
                average_price=price,
                last_price=price,
                pnl=0,
                pnl_percent=0
            )
