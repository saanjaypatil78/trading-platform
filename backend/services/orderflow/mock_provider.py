"""
Mock L2 Data Provider

Generates realistic mock L2 orderbook and trade data for development/testing
without requiring actual API keys. Simulates market microstructure.
"""

import asyncio
import random
import logging
from typing import List, Callable, Optional
from datetime import datetime, timedelta
import math

from .l2_models import (
    OrderBookSnapshot, OrderBookLevel, OrderBookDelta,
    TradeExecution, Side
)

logger = logging.getLogger(__name__)


class MockL2Provider:
    """
    Mock L2 data provider that generates realistic market data.
    
    Features:
    - Simulated orderbook with bid/ask spread
    - Random walk price movement
    - Realistic trade execution simulation
    - Occasional wall insertions and sweeps
    """
    
    def __init__(
        self,
        base_price: float = 150.0,
        tick_size: float = 0.01,
        levels: int = 10,
        volatility: float = 0.001
    ):
        self.base_price = base_price
        self.tick_size = tick_size
        self.levels = levels
        self.volatility = volatility
        
        # Current state
        self._current_mid = base_price
        self._spread = tick_size * 2
        self._subscriptions: List[str] = []
        
        # Callbacks
        self._orderbook_callbacks: List[Callable] = []
        self._trade_callbacks: List[Callable] = []
        
        # Control
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    @property
    def is_connected(self) -> bool:
        return self._running
    
    def on_orderbook(self, callback: Callable):
        """Register orderbook update callback"""
        self._orderbook_callbacks.append(callback)
    
    def on_trade(self, callback: Callable):
        """Register trade execution callback"""
        self._trade_callbacks.append(callback)
    
    async def connect(self) -> bool:
        """Start mock data generation"""
        if self._running:
            return True
        
        self._running = True
        self._task = asyncio.create_task(self._generate_data())
        logger.info("Mock L2 provider connected")
        return True
    
    async def disconnect(self):
        """Stop mock data generation"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Mock L2 provider disconnected")
    
    async def subscribe(self, symbol: str) -> bool:
        """Subscribe to a symbol"""
        if symbol not in self._subscriptions:
            self._subscriptions.append(symbol)
            logger.info(f"Mock subscribed to {symbol}")
        return True
    
    async def unsubscribe(self, symbol: str):
        """Unsubscribe from a symbol"""
        if symbol in self._subscriptions:
            self._subscriptions.remove(symbol)
    
    async def _generate_data(self):
        """Main data generation loop"""
        while self._running:
            for symbol in self._subscriptions:
                # Update price with random walk
                self._update_price()
                
                # Generate orderbook
                snapshot = self._generate_orderbook(symbol)
                await self._emit_orderbook(snapshot)
                
                # Occasionally generate trades
                if random.random() < 0.7:  # 70% chance of trade
                    trades = self._generate_trades(symbol)
                    for trade in trades:
                        await self._emit_trade(trade)
            
            # Sleep between updates (100-300ms for realism)
            await asyncio.sleep(random.uniform(0.1, 0.3))
    
    def _update_price(self):
        """Random walk price update"""
        # Brownian motion with mean reversion
        change = random.gauss(0, self._current_mid * self.volatility)
        mean_rev = (self.base_price - self._current_mid) * 0.01
        self._current_mid += change + mean_rev
        
        # Ensure positive price
        self._current_mid = max(self._current_mid, self.base_price * 0.5)
    
    def _generate_orderbook(self, symbol: str) -> OrderBookSnapshot:
        """Generate realistic orderbook snapshot"""
        bids = []
        asks = []
        
        best_bid = self._current_mid - self._spread / 2
        best_ask = self._current_mid + self._spread / 2
        
        for i in range(self.levels):
            # Size follows power law distribution (more at best levels)
            bid_size = random.paretovariate(2) * 100
            ask_size = random.paretovariate(2) * 100
            
            # Occasionally insert walls
            if random.random() < 0.05:
                bid_size *= 5  # Wall at this level
            if random.random() < 0.05:
                ask_size *= 5
            
            bids.append(OrderBookLevel(
                price=round(best_bid - i * self.tick_size, 2),
                size=round(bid_size, 0),
                order_count=random.randint(1, 20)
            ))
            
            asks.append(OrderBookLevel(
                price=round(best_ask + i * self.tick_size, 2),
                size=round(ask_size, 0),
                order_count=random.randint(1, 20)
            ))
        
        return OrderBookSnapshot(
            symbol=symbol,
            timestamp=datetime.now(),
            bids=bids,
            asks=asks
        )
    
    def _generate_trades(self, symbol: str) -> List[TradeExecution]:
        """Generate realistic trade executions"""
        trades = []
        num_trades = random.randint(1, 5)
        
        for _ in range(num_trades):
            # Side weighted by recent price movement
            side = Side.BUY if random.random() < 0.5 else Side.SELL
            
            # Price near current mid
            if side == Side.BUY:
                price = self._current_mid + self._spread / 2  # Lifts ask
            else:
                price = self._current_mid - self._spread / 2  # Hits bid
            
            # Size follows log-normal distribution (occasional large trades)
            size = math.exp(random.gauss(3, 1.5))  # ~20 to several hundred
            
            trades.append(TradeExecution(
                symbol=symbol,
                timestamp=datetime.now(),
                price=round(price, 2),
                size=round(size, 0),
                side=side,
                trade_id=f"mock_{int(datetime.now().timestamp() * 1000)}_{random.randint(1000, 9999)}"
            ))
        
        return trades
    
    async def _emit_orderbook(self, snapshot: OrderBookSnapshot):
        """Emit orderbook to callbacks"""
        for cb in self._orderbook_callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(snapshot)
                else:
                    cb(snapshot)
            except Exception as e:
                logger.error(f"Orderbook callback error: {e}")
    
    async def _emit_trade(self, trade: TradeExecution):
        """Emit trade to callbacks"""
        for cb in self._trade_callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(trade)
                else:
                    cb(trade)
            except Exception as e:
                logger.error(f"Trade callback error: {e}")


class MockScenarioProvider(MockL2Provider):
    """
    Extended mock provider that can simulate specific market scenarios.
    Useful for testing detection algorithms.
    """
    
    async def simulate_absorption(self, symbol: str, direction: Side):
        """
        Simulate absorption pattern.
        Heavy volume on one side but price doesn't move.
        """
        logger.info(f"Simulating {direction.value} absorption on {symbol}")
        
        for _ in range(10):
            # Generate many trades on one side
            trade = TradeExecution(
                symbol=symbol,
                timestamp=datetime.now(),
                price=round(self._current_mid, 2),  # Price stays flat
                size=random.uniform(500, 2000),  # Large size
                side=direction,
                trade_id=f"absorption_{int(datetime.now().timestamp() * 1000)}"
            )
            await self._emit_trade(trade)
            await asyncio.sleep(0.05)
    
    async def simulate_sweep(self, symbol: str, direction: Side):
        """
        Simulate sweep pattern.
        Aggressive orders clearing multiple price levels.
        """
        logger.info(f"Simulating {direction.value} sweep on {symbol}")
        
        price = self._current_mid
        for i in range(5):
            # Price moves aggressively
            if direction == Side.BUY:
                price += self.tick_size * 2
            else:
                price -= self.tick_size * 2
            
            trade = TradeExecution(
                symbol=symbol,
                timestamp=datetime.now(),
                price=round(price, 2),
                size=random.uniform(300, 800),
                side=direction,
                trade_id=f"sweep_{int(datetime.now().timestamp() * 1000)}_{i}"
            )
            await self._emit_trade(trade)
            await asyncio.sleep(0.05)  # Fast sequence
        
        self._current_mid = price  # Update mid after sweep
    
    async def simulate_wall(self, symbol: str, side: Side, size: float = 10000):
        """
        Simulate a bid/ask wall appearing.
        """
        logger.info(f"Simulating {side.value} wall on {symbol}, size {size}")
        
        snapshot = self._generate_orderbook(symbol)
        
        # Insert wall at best price
        if side == Side.BUY:
            snapshot.bids[0].size = size
        else:
            snapshot.asks[0].size = size
        
        await self._emit_orderbook(snapshot)


# Global mock instance for development
mock_provider = MockL2Provider()
mock_scenario_provider = MockScenarioProvider()
