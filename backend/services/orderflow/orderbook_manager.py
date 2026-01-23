"""
Orderbook Manager - Maintains Live Order Book State

Responsibilities:
- Apply delta updates to orderbook snapshots
- Track bid/ask walls and significant levels
- Emit events on significant orderbook changes
- Detect potential spoofing patterns
"""

import logging
from typing import Optional, Dict, List, Callable, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio

from .l2_models import (
    OrderBookSnapshot, OrderBookLevel, OrderBookDelta,
    Side, CircuitBreakerStatus
)

logger = logging.getLogger(__name__)


class OrderBookManager:
    """
    Manages live orderbook state for multiple symbols.
    Tracks significant price levels and detects anomalies.
    """
    
    def __init__(self):
        # Current orderbook state per symbol
        self._orderbooks: Dict[str, OrderBookSnapshot] = {}
        
        # Historical snapshots for comparison (last N snapshots)
        self._history: Dict[str, List[OrderBookSnapshot]] = defaultdict(list)
        self._history_limit = 100
        
        # Significant level tracking
        self._bid_walls: Dict[str, List[OrderBookLevel]] = {}
        self._ask_walls: Dict[str, List[OrderBookLevel]] = {}
        
        # Spoofing detection
        self._level_changes: Dict[str, Dict[float, List[Tuple[datetime, float]]]] = defaultdict(
            lambda: defaultdict(list)
        )
        
        # Event callbacks
        self._callbacks: Dict[str, List[Callable]] = {
            "update": [],
            "wall_detected": [],
            "wall_removed": [],
            "spoof_suspected": [],
            "liquidity_change": []
        }
        
        # Configuration
        self.wall_threshold_multiplier = 3.0  # Size > avg * multiplier = wall
        self.spoof_detection_window = timedelta(seconds=5)
        self.spoof_change_threshold = 3  # N changes in window = suspicious
    
    def on(self, event: str, callback: Callable):
        """Register callback for events"""
        if event in self._callbacks:
            self._callbacks[event].append(callback)
    
    async def _emit(self, event: str, data):
        """Emit event to callbacks"""
        for cb in self._callbacks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(data)
                else:
                    cb(data)
            except Exception as e:
                logger.error(f"Callback error for {event}: {e}")
    
    async def update_snapshot(self, snapshot: OrderBookSnapshot):
        """
        Update orderbook with a new snapshot.
        Detects walls and emits relevant events.
        """
        symbol = snapshot.symbol
        old_snapshot = self._orderbooks.get(symbol)
        
        # Store new snapshot
        self._orderbooks[symbol] = snapshot
        
        # Add to history
        self._history[symbol].append(snapshot)
        if len(self._history[symbol]) > self._history_limit:
            self._history[symbol].pop(0)
        
        # Detect walls
        await self._detect_walls(symbol, snapshot)
        
        # Check for significant liquidity changes
        if old_snapshot:
            await self._check_liquidity_change(symbol, old_snapshot, snapshot)
        
        # Emit update event
        await self._emit("update", snapshot)
    
    async def apply_delta(self, delta: OrderBookDelta):
        """
        Apply incremental update to orderbook.
        Track changes for spoofing detection.
        """
        symbol = delta.symbol
        
        if symbol not in self._orderbooks:
            logger.warning(f"No orderbook for {symbol}, ignoring delta")
            return
        
        snapshot = self._orderbooks[symbol]
        
        # Get the appropriate side
        levels = snapshot.bids if delta.side == Side.BUY else snapshot.asks
        
        # Track this change for spoofing detection
        self._track_level_change(symbol, delta.price, delta.size)
        
        # Find and update the level
        level_found = False
        for i, level in enumerate(levels):
            if abs(level.price - delta.price) < 0.0001:  # Float comparison
                if delta.size == 0:
                    # Remove level
                    levels.pop(i)
                else:
                    # Update level
                    levels[i] = OrderBookLevel(
                        price=delta.price,
                        size=delta.size,
                        order_count=level.order_count
                    )
                level_found = True
                break
        
        if not level_found and delta.size > 0:
            # Add new level
            new_level = OrderBookLevel(price=delta.price, size=delta.size)
            levels.append(new_level)
            
            # Re-sort levels
            if delta.side == Side.BUY:
                snapshot.bids = sorted(levels, key=lambda x: -x.price)
            else:
                snapshot.asks = sorted(levels, key=lambda x: x.price)
        
        # Update timestamp
        snapshot.timestamp = delta.timestamp
        
        # Check for spoofing
        await self._check_spoofing(symbol, delta.price)
    
    def _track_level_change(self, symbol: str, price: float, size: float):
        """Track changes at a price level for spoofing detection"""
        changes = self._level_changes[symbol][price]
        changes.append((datetime.now(), size))
        
        # Cleanup old changes
        cutoff = datetime.now() - self.spoof_detection_window
        self._level_changes[symbol][price] = [
            (t, s) for t, s in changes if t > cutoff
        ]
    
    async def _check_spoofing(self, symbol: str, price: float):
        """Check if price level shows spoofing behavior"""
        changes = self._level_changes[symbol].get(price, [])
        
        if len(changes) >= self.spoof_change_threshold:
            # Check if orders are being placed/cancelled rapidly
            sizes = [s for _, s in changes]
            if 0 in sizes and max(sizes) > 0:
                # Orders appearing and disappearing = potential spoof
                await self._emit("spoof_suspected", {
                    "symbol": symbol,
                    "price": price,
                    "changes": len(changes),
                    "window_seconds": self.spoof_detection_window.seconds
                })
                logger.warning(f"Potential spoofing at {symbol} ${price}")
    
    async def _detect_walls(self, symbol: str, snapshot: OrderBookSnapshot):
        """Detect significant bid/ask walls"""
        # Calculate average sizes
        avg_bid_size = sum(l.size for l in snapshot.bids[:10]) / max(len(snapshot.bids[:10]), 1)
        avg_ask_size = sum(l.size for l in snapshot.asks[:10]) / max(len(snapshot.asks[:10]), 1)
        
        # Find walls (levels significantly larger than average)
        new_bid_walls = [
            l for l in snapshot.bids
            if l.size > avg_bid_size * self.wall_threshold_multiplier
        ]
        new_ask_walls = [
            l for l in snapshot.asks
            if l.size > avg_ask_size * self.wall_threshold_multiplier
        ]
        
        old_bid_walls = self._bid_walls.get(symbol, [])
        old_ask_walls = self._ask_walls.get(symbol, [])
        
        # Detect new walls
        for wall in new_bid_walls:
            if wall not in old_bid_walls:
                await self._emit("wall_detected", {
                    "symbol": symbol,
                    "side": "bid",
                    "price": wall.price,
                    "size": wall.size
                })
        
        for wall in new_ask_walls:
            if wall not in old_ask_walls:
                await self._emit("wall_detected", {
                    "symbol": symbol,
                    "side": "ask",
                    "price": wall.price,
                    "size": wall.size
                })
        
        # Detect removed walls
        old_bid_prices = {w.price for w in old_bid_walls}
        new_bid_prices = {w.price for w in new_bid_walls}
        for price in old_bid_prices - new_bid_prices:
            await self._emit("wall_removed", {
                "symbol": symbol,
                "side": "bid",
                "price": price
            })
        
        # Update wall tracking
        self._bid_walls[symbol] = new_bid_walls
        self._ask_walls[symbol] = new_ask_walls
    
    async def _check_liquidity_change(
        self, 
        symbol: str, 
        old: OrderBookSnapshot, 
        new: OrderBookSnapshot
    ):
        """Detect significant liquidity changes"""
        old_bid_liquidity = old.total_bid_size(5)
        new_bid_liquidity = new.total_bid_size(5)
        old_ask_liquidity = old.total_ask_size(5)
        new_ask_liquidity = new.total_ask_size(5)
        
        # Check for >20% change
        if old_bid_liquidity > 0:
            bid_change = (new_bid_liquidity - old_bid_liquidity) / old_bid_liquidity
            if abs(bid_change) > 0.2:
                await self._emit("liquidity_change", {
                    "symbol": symbol,
                    "side": "bid",
                    "change_pct": bid_change * 100,
                    "old_size": old_bid_liquidity,
                    "new_size": new_bid_liquidity
                })
        
        if old_ask_liquidity > 0:
            ask_change = (new_ask_liquidity - old_ask_liquidity) / old_ask_liquidity
            if abs(ask_change) > 0.2:
                await self._emit("liquidity_change", {
                    "symbol": symbol,
                    "side": "ask",
                    "change_pct": ask_change * 100,
                    "old_size": old_ask_liquidity,
                    "new_size": new_ask_liquidity
                })
    
    def get_orderbook(self, symbol: str) -> Optional[OrderBookSnapshot]:
        """Get current orderbook for symbol"""
        return self._orderbooks.get(symbol)
    
    def get_walls(self, symbol: str) -> Dict[str, List[OrderBookLevel]]:
        """Get current walls for symbol"""
        return {
            "bid_walls": self._bid_walls.get(symbol, []),
            "ask_walls": self._ask_walls.get(symbol, [])
        }
    
    def get_liquidity_at_price(self, symbol: str, price: float, side: Side) -> float:
        """Get total liquidity at or better than price"""
        book = self._orderbooks.get(symbol)
        if not book:
            return 0.0
        
        total = 0.0
        levels = book.bids if side == Side.BUY else book.asks
        
        for level in levels:
            if side == Side.BUY and level.price >= price:
                total += level.size
            elif side == Side.SELL and level.price <= price:
                total += level.size
        
        return total
    
    def estimate_slippage(
        self, 
        symbol: str, 
        side: Side, 
        quantity: float
    ) -> Optional[Tuple[float, float]]:
        """
        Estimate execution price and slippage for a given order size.
        Returns (avg_price, slippage_pct) or None if insufficient liquidity.
        """
        book = self._orderbooks.get(symbol)
        if not book:
            return None
        
        levels = book.asks if side == Side.BUY else book.bids
        if not levels:
            return None
        
        remaining = quantity
        total_cost = 0.0
        reference_price = levels[0].price
        
        for level in levels:
            fill_size = min(remaining, level.size)
            total_cost += fill_size * level.price
            remaining -= fill_size
            
            if remaining <= 0:
                break
        
        if remaining > 0:
            # Insufficient liquidity
            return None
        
        avg_price = total_cost / quantity
        slippage_pct = abs(avg_price - reference_price) / reference_price * 100
        
        return (avg_price, slippage_pct)


# Global instance
orderbook_manager = OrderBookManager()
