"""
L2 Market Depth & Orderflow Data Models

Pydantic models for:
- OrderBook snapshots and deltas
- Trade execution events  
- Footprint clusters for volume analysis
- Detection signals for institutional patterns
"""

from typing import Optional, List, Dict, Literal
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


# =============================================================================
# Enums
# =============================================================================

class Side(str, Enum):
    """Trade/order side"""
    BUY = "buy"
    SELL = "sell"


class SignalType(str, Enum):
    """Footprint detection signal types"""
    ABSORPTION = "absorption"
    EXHAUSTION = "exhaustion"
    IMBALANCE = "imbalance"
    SWEEP = "sweep"


class SignalConfidence(str, Enum):
    """Signal confidence levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MarketRegime(str, Enum):
    """Market regime classification"""
    BULLISH = "bullish"
    BEARISH = "bearish"
    SIDEWAYS = "sideways"
    VOLATILE = "volatile"


# =============================================================================
# OrderBook Models
# =============================================================================

class OrderBookLevel(BaseModel):
    """Single price level in the orderbook"""
    price: float = Field(..., description="Price at this level")
    size: float = Field(..., description="Total size at this level")
    order_count: Optional[int] = Field(None, description="Number of orders at level")
    
    class Config:
        json_schema_extra = {
            "example": {"price": 150.25, "size": 1000, "order_count": 15}
        }


class OrderBookSnapshot(BaseModel):
    """Full orderbook snapshot (L2 depth)"""
    symbol: str = Field(..., description="Trading symbol")
    timestamp: datetime = Field(default_factory=datetime.now)
    bids: List[OrderBookLevel] = Field(default_factory=list, description="Bid levels (best first)")
    asks: List[OrderBookLevel] = Field(default_factory=list, description="Ask levels (best first)")
    
    @property
    def best_bid(self) -> Optional[float]:
        return self.bids[0].price if self.bids else None
    
    @property
    def best_ask(self) -> Optional[float]:
        return self.asks[0].price if self.asks else None
    
    @property
    def spread(self) -> Optional[float]:
        if self.best_bid and self.best_ask:
            return self.best_ask - self.best_bid
        return None
    
    @property
    def mid_price(self) -> Optional[float]:
        if self.best_bid and self.best_ask:
            return (self.best_bid + self.best_ask) / 2
        return None
    
    def total_bid_size(self, levels: int = 5) -> float:
        """Sum of bid sizes for top N levels"""
        return sum(level.size for level in self.bids[:levels])
    
    def total_ask_size(self, levels: int = 5) -> float:
        """Sum of ask sizes for top N levels"""
        return sum(level.size for level in self.asks[:levels])
    
    def imbalance_ratio(self, levels: int = 5) -> float:
        """Bid/Ask imbalance ratio (>1 = more bids, <1 = more asks)"""
        bid_size = self.total_bid_size(levels)
        ask_size = self.total_ask_size(levels)
        if ask_size == 0:
            return float('inf') if bid_size > 0 else 1.0
        return bid_size / ask_size


class OrderBookDelta(BaseModel):
    """Incremental orderbook update"""
    symbol: str
    timestamp: datetime = Field(default_factory=datetime.now)
    side: Side
    price: float
    size: float = Field(..., description="New size at level (0 = remove)")
    action: Literal["add", "update", "remove"] = "update"


# =============================================================================
# Trade Execution Models
# =============================================================================

class TradeExecution(BaseModel):
    """Individual trade execution (Time & Sales)"""
    symbol: str
    timestamp: datetime
    price: float
    size: float
    side: Side = Field(..., description="Aggressor side (who crossed the spread)")
    trade_id: Optional[str] = None
    
    @property
    def notional_value(self) -> float:
        return self.price * self.size


class TradeCluster(BaseModel):
    """Cluster of trades at a price level within a time window"""
    price_level: float
    timestamp_start: datetime
    timestamp_end: datetime
    buy_volume: float = 0.0
    sell_volume: float = 0.0
    trade_count: int = 0
    
    @property
    def delta(self) -> float:
        """Net volume (buy - sell)"""
        return self.buy_volume - self.sell_volume
    
    @property
    def total_volume(self) -> float:
        return self.buy_volume + self.sell_volume
    
    @property
    def imbalance_ratio(self) -> float:
        """Buy/Sell ratio (>1 = buyer dominant, <1 = seller dominant)"""
        if self.sell_volume == 0:
            return float('inf') if self.buy_volume > 0 else 1.0
        return self.buy_volume / self.sell_volume


# =============================================================================
# Footprint Analysis Models
# =============================================================================

class FootprintCell(BaseModel):
    """Single cell in footprint chart (price level x time bucket)"""
    price_level: float
    time_bucket: datetime
    bid_volume: float = 0.0  # Volume at bid
    ask_volume: float = 0.0  # Volume at ask
    
    @property
    def delta(self) -> float:
        return self.ask_volume - self.bid_volume  # Positive = buying pressure
    
    @property
    def imbalance_ratio(self) -> float:
        """Ask/Bid imbalance ratio (>1 = buyer dominant)"""
        if self.bid_volume == 0:
            return float('inf') if self.ask_volume > 0 else 1.0
        return self.ask_volume / self.bid_volume


class FootprintCluster(BaseModel):
    """Aggregated footprint data for a candle/time period"""
    symbol: str
    period_start: datetime
    period_end: datetime
    cells: List[FootprintCell] = Field(default_factory=list)
    
    # Summary stats
    high_price: float = 0.0
    low_price: float = 0.0
    total_buy_volume: float = 0.0
    total_sell_volume: float = 0.0
    
    @property
    def total_delta(self) -> float:
        return self.total_buy_volume - self.total_sell_volume
    
    @property
    def poc(self) -> Optional[float]:
        """Point of Control - price level with highest volume"""
        if not self.cells:
            return None
        max_cell = max(self.cells, key=lambda c: c.bid_volume + c.ask_volume)
        return max_cell.price_level
    
    def imbalances(self, threshold: float = 3.0) -> List[FootprintCell]:
        """Find cells with significant buy/sell imbalance (>threshold ratio)"""
        imbalanced = []
        for cell in self.cells:
            if cell.bid_volume > 0 and cell.ask_volume / cell.bid_volume > threshold:
                imbalanced.append(cell)
            elif cell.ask_volume > 0 and cell.bid_volume / cell.ask_volume > threshold:
                imbalanced.append(cell)
        return imbalanced


# =============================================================================
# Detection Signal Models
# =============================================================================

class FootprintSignal(BaseModel):
    """Detection signal from footprint analysis"""
    symbol: str
    timestamp: datetime = Field(default_factory=datetime.now)
    signal_type: SignalType
    direction: Side  # Suggested trade direction
    confidence: SignalConfidence
    price_level: float
    
    # Evidence
    delta: float = Field(..., description="Net volume that triggered signal")
    price_movement: float = Field(..., description="Price movement during signal")
    volume_ratio: float = Field(default=1.0, description="Buy/Sell ratio")
    
    # Context
    description: str = ""
    supporting_data: Dict = Field(default_factory=dict)
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "AAPL",
                "signal_type": "absorption",
                "direction": "buy",
                "confidence": "high",
                "price_level": 150.50,
                "delta": -50000,
                "price_movement": 0.05,
                "description": "Large sell volume absorbed with minimal price drop"
            }
        }


# =============================================================================
# Confirmation & Execution Models
# =============================================================================

class ConfirmationRequest(BaseModel):
    """Request for execution confirmation from the mesh"""
    signal: FootprintSignal
    symbol: str
    side: Side
    quantity: float
    order_type: Literal["market", "limit", "stop"] = "market"
    limit_price: Optional[float] = None
    
    # Risk parameters
    max_slippage_pct: float = Field(default=0.5, description="Max acceptable slippage %")
    require_liquidity: bool = Field(default=True, description="Check L2 liquidity before execution")


class ConfirmationResult(BaseModel):
    """Result from confirmation mesh validation"""
    approved: bool
    signal: FootprintSignal
    
    # Validation results
    liquidity_check: bool = True
    footprint_confirmed: bool = True
    risk_check: bool = True
    
    # Rejection reason (if not approved)
    rejection_reason: Optional[str] = None
    
    # Execution parameters (if approved)
    recommended_quantity: Optional[float] = None
    recommended_price: Optional[float] = None
    available_liquidity: Optional[float] = None
    
    # Timestamps
    requested_at: datetime = Field(default_factory=datetime.now)
    processed_at: datetime = Field(default_factory=datetime.now)


class CircuitBreakerStatus(BaseModel):
    """Circuit breaker state for risk management"""
    symbol: str
    is_tripped: bool = False
    trip_reason: Optional[str] = None
    tripped_at: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None
    
    # Metrics that can trip the breaker
    consecutive_losses: int = 0
    volatility_spike: bool = False
    liquidity_dried_up: bool = False
    spoofing_detected: bool = False
