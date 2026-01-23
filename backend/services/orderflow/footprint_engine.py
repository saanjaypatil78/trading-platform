"""
Footprint Detection Engine

Detects institutional order flow patterns:
- Absorption: High volume with minimal price movement (hidden liquidity)
- Exhaustion: Declining volume at support/resistance (reversal signal)
- Imbalance: Disproportionate buying/selling (trend continuation)
- Sweep: Aggressive orders clearing thin liquidity
"""

import logging
from typing import Optional, List, Dict, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from dataclasses import dataclass

from .l2_models import (
    TradeExecution, TradeCluster, FootprintCluster, FootprintCell,
    FootprintSignal, SignalType, SignalConfidence, Side,
    OrderBookSnapshot
)

logger = logging.getLogger(__name__)


@dataclass
class DetectionConfig:
    """Configuration for detection algorithms"""
    # Absorption detection
    absorption_volume_threshold: float = 10000  # Minimum volume to consider
    absorption_price_move_max: float = 0.1  # Max price % change
    absorption_delta_threshold: float = 0.7  # Delta must be >70% one-sided
    
    # Exhaustion detection
    exhaustion_volume_decline_pct: float = 0.5  # Volume must drop by 50%
    exhaustion_lookback_periods: int = 5  # Compare against N previous periods
    
    # Imbalance detection  
    imbalance_ratio_threshold: float = 3.0  # 3:1 buy/sell ratio
    imbalance_min_volume: float = 5000  # Minimum volume for imbalance
    
    # Sweep detection
    sweep_levels_cleared: int = 3  # Min price levels cleared
    sweep_time_window_ms: int = 500  # Must happen within N ms
    sweep_min_volume: float = 10000  # Min volume for sweep


class FootprintEngine:
    """
    Core detection engine for institutional order flow patterns.
    Processes trade executions and L2 data to identify actionable signals.
    """
    
    def __init__(self, config: Optional[DetectionConfig] = None):
        self.config = config or DetectionConfig()
        
        # Trade accumulation buffers per symbol
        self._trade_buffer: Dict[str, List[TradeExecution]] = defaultdict(list)
        self._buffer_window = timedelta(seconds=1)  # 1-second aggregation
        
        # Historical clusters for comparison
        self._cluster_history: Dict[str, List[FootprintCluster]] = defaultdict(list)
        self._history_limit = 100
        
        # Price level tracking for sweeps
        self._price_levels_touched: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        
        # Signal callbacks
        self._signal_callbacks: List = []
    
    def on_signal(self, callback):
        """Register callback for detected signals"""
        self._signal_callbacks.append(callback)
    
    async def _emit_signal(self, signal: FootprintSignal):
        """Emit detected signal"""
        for cb in self._signal_callbacks:
            try:
                if hasattr(cb, '__call__'):
                    import asyncio
                    if asyncio.iscoroutinefunction(cb):
                        await cb(signal)
                    else:
                        cb(signal)
            except Exception as e:
                logger.error(f"Signal callback error: {e}")
    
    async def process_trade(self, trade: TradeExecution):
        """
        Process incoming trade and check for patterns.
        Trades are buffered and aggregated into clusters.
        """
        symbol = trade.symbol
        self._trade_buffer[symbol].append(trade)
        
        # Track price level for sweep detection
        self._price_levels_touched[symbol].append((trade.timestamp, trade.price))
        
        # Check for sweep pattern on each trade
        sweep_signal = await self._detect_sweep(symbol, trade)
        if sweep_signal:
            await self._emit_signal(sweep_signal)
        
        # Cleanup old price level data
        cutoff = datetime.now() - timedelta(seconds=1)
        self._price_levels_touched[symbol] = [
            (t, p) for t, p in self._price_levels_touched[symbol] if t > cutoff
        ]
    
    async def flush_buffer(self, symbol: str) -> Optional[FootprintCluster]:
        """
        Flush trade buffer and create footprint cluster.
        Called periodically or when buffer is full.
        """
        trades = self._trade_buffer.get(symbol, [])
        if not trades:
            return None
        
        # Clear buffer
        self._trade_buffer[symbol] = []
        
        # Build footprint cluster
        cluster = self._build_cluster(symbol, trades)
        
        # Store in history
        self._cluster_history[symbol].append(cluster)
        if len(self._cluster_history[symbol]) > self._history_limit:
            self._cluster_history[symbol].pop(0)
        
        # Run detection algorithms
        signals = await self._analyze_cluster(symbol, cluster)
        
        for signal in signals:
            await self._emit_signal(signal)
        
        return cluster
    
    def _build_cluster(self, symbol: str, trades: List[TradeExecution]) -> FootprintCluster:
        """Build footprint cluster from list of trades"""
        if not trades:
            return FootprintCluster(
                symbol=symbol,
                period_start=datetime.now(),
                period_end=datetime.now()
            )
        
        # Group trades by price level (round to tick size)
        tick_size = 0.01  # Default tick size
        cells_by_price: Dict[float, FootprintCell] = {}
        
        total_buy = 0.0
        total_sell = 0.0
        high_price = trades[0].price
        low_price = trades[0].price
        
        for trade in trades:
            # Round to tick
            price_level = round(trade.price / tick_size) * tick_size
            
            if price_level not in cells_by_price:
                cells_by_price[price_level] = FootprintCell(
                    price_level=price_level,
                    time_bucket=trades[0].timestamp
                )
            
            cell = cells_by_price[price_level]
            
            if trade.side == Side.BUY:
                cell.ask_volume += trade.size  # Buyers lift the ask
                total_buy += trade.size
            else:
                cell.bid_volume += trade.size  # Sellers hit the bid
                total_sell += trade.size
            
            high_price = max(high_price, trade.price)
            low_price = min(low_price, trade.price)
        
        return FootprintCluster(
            symbol=symbol,
            period_start=trades[0].timestamp,
            period_end=trades[-1].timestamp,
            cells=list(cells_by_price.values()),
            high_price=high_price,
            low_price=low_price,
            total_buy_volume=total_buy,
            total_sell_volume=total_sell
        )
    
    async def _analyze_cluster(
        self, 
        symbol: str, 
        cluster: FootprintCluster
    ) -> List[FootprintSignal]:
        """Run all detection algorithms on a cluster"""
        signals = []
        
        # Check absorption
        absorption = self._detect_absorption(symbol, cluster)
        if absorption:
            signals.append(absorption)
        
        # Check exhaustion
        exhaustion = self._detect_exhaustion(symbol, cluster)
        if exhaustion:
            signals.append(exhaustion)
        
        # Check imbalances
        imbalances = self._detect_imbalances(symbol, cluster)
        signals.extend(imbalances)
        
        return signals
    
    def _detect_absorption(
        self, 
        symbol: str, 
        cluster: FootprintCluster
    ) -> Optional[FootprintSignal]:
        """
        Detect absorption pattern.
        
        Absorption = High volume on one side + Minimal price movement
        Indicates hidden liquidity (iceberg orders) absorbing market orders.
        
        Example: Heavy selling (negative delta) but price doesn't drop
        -> Bullish absorption (hidden buyer)
        """
        total_volume = cluster.total_buy_volume + cluster.total_sell_volume
        
        # Skip if insufficient volume
        if total_volume < self.config.absorption_volume_threshold:
            return None
        
        # Calculate price movement
        price_range = cluster.high_price - cluster.low_price
        if cluster.low_price > 0:
            price_move_pct = price_range / cluster.low_price * 100
        else:
            return None
        
        # Check if price movement is minimal
        if price_move_pct > self.config.absorption_price_move_max:
            return None
        
        # Calculate delta ratio
        delta = cluster.total_delta
        if total_volume == 0:
            return None
        
        delta_ratio = abs(delta) / total_volume
        
        # Check if delta is one-sided (absorption indicator)
        if delta_ratio < self.config.absorption_delta_threshold:
            return None
        
        # Determine direction
        # Negative delta (more selling) but no price drop = bullish absorption
        # Positive delta (more buying) but no price rise = bearish absorption
        if delta < 0:
            direction = Side.BUY
            description = f"Bullish absorption: {abs(delta):.0f} sell volume absorbed with only {price_move_pct:.2f}% price drop"
        else:
            direction = Side.SELL
            description = f"Bearish absorption: {delta:.0f} buy volume absorbed with only {price_move_pct:.2f}% price rise"
        
        # Determine confidence
        if delta_ratio > 0.9 and price_move_pct < 0.05:
            confidence = SignalConfidence.HIGH
        elif delta_ratio > 0.8:
            confidence = SignalConfidence.MEDIUM
        else:
            confidence = SignalConfidence.LOW
        
        return FootprintSignal(
            symbol=symbol,
            signal_type=SignalType.ABSORPTION,
            direction=direction,
            confidence=confidence,
            price_level=cluster.poc or cluster.low_price,
            delta=delta,
            price_movement=price_move_pct,
            volume_ratio=delta_ratio,
            description=description,
            supporting_data={
                "total_volume": total_volume,
                "buy_volume": cluster.total_buy_volume,
                "sell_volume": cluster.total_sell_volume,
                "price_range": price_range
            }
        )
    
    def _detect_exhaustion(
        self, 
        symbol: str, 
        cluster: FootprintCluster
    ) -> Optional[FootprintSignal]:
        """
        Detect exhaustion pattern.
        
        Exhaustion = Declining volume + Price at resistance/support
        Indicates loss of momentum, potential reversal.
        """
        history = self._cluster_history.get(symbol, [])
        
        if len(history) < self.config.exhaustion_lookback_periods:
            return None
        
        # Get recent clusters for comparison
        recent = history[-self.config.exhaustion_lookback_periods:]
        
        # Calculate average recent volume
        avg_volume = sum(
            c.total_buy_volume + c.total_sell_volume for c in recent
        ) / len(recent)
        
        current_volume = cluster.total_buy_volume + cluster.total_sell_volume
        
        if avg_volume == 0:
            return None
        
        volume_change = (current_volume - avg_volume) / avg_volume
        
        # Check for significant volume decline
        if volume_change > -self.config.exhaustion_volume_decline_pct:
            return None
        
        # Determine direction based on price position and delta
        # If at highs with declining buy volume = bearish exhaustion
        # If at lows with declining sell volume = bullish exhaustion
        
        recent_highs = max(c.high_price for c in recent)
        recent_lows = min(c.low_price for c in recent)
        
        if cluster.high_price >= recent_highs * 0.99 and cluster.total_delta > 0:
            # At highs but buying exhausted
            direction = Side.SELL
            description = f"Bearish exhaustion: Volume declined {abs(volume_change)*100:.0f}% at resistance"
        elif cluster.low_price <= recent_lows * 1.01 and cluster.total_delta < 0:
            # At lows but selling exhausted
            direction = Side.BUY
            description = f"Bullish exhaustion: Volume declined {abs(volume_change)*100:.0f}% at support"
        else:
            return None
        
        return FootprintSignal(
            symbol=symbol,
            signal_type=SignalType.EXHAUSTION,
            direction=direction,
            confidence=SignalConfidence.MEDIUM,
            price_level=cluster.poc or cluster.high_price,
            delta=cluster.total_delta,
            price_movement=volume_change * 100,
            description=description,
            supporting_data={
                "current_volume": current_volume,
                "avg_volume": avg_volume,
                "volume_decline_pct": volume_change * 100
            }
        )
    
    def _detect_imbalances(
        self, 
        symbol: str, 
        cluster: FootprintCluster
    ) -> List[FootprintSignal]:
        """
        Detect imbalance patterns within footprint cells.
        
        Imbalance = Disproportionate buying vs selling at price level
        Strong imbalances indicate institutional commitment.
        """
        signals = []
        
        for cell in cluster.cells:
            total_vol = cell.bid_volume + cell.ask_volume
            
            if total_vol < self.config.imbalance_min_volume:
                continue
            
            ratio = cell.imbalance_ratio
            
            if ratio >= self.config.imbalance_ratio_threshold:
                # More buying (asks lifted)
                signals.append(FootprintSignal(
                    symbol=symbol,
                    signal_type=SignalType.IMBALANCE,
                    direction=Side.BUY,
                    confidence=SignalConfidence.HIGH if ratio > 5 else SignalConfidence.MEDIUM,
                    price_level=cell.price_level,
                    delta=cell.delta,
                    price_movement=0,
                    volume_ratio=ratio,
                    description=f"Buy imbalance {ratio:.1f}:1 at ${cell.price_level:.2f}",
                    supporting_data={
                        "ask_volume": cell.ask_volume,
                        "bid_volume": cell.bid_volume
                    }
                ))
            elif ratio > 0 and 1/ratio >= self.config.imbalance_ratio_threshold:
                # More selling (bids hit)
                signals.append(FootprintSignal(
                    symbol=symbol,
                    signal_type=SignalType.IMBALANCE,
                    direction=Side.SELL,
                    confidence=SignalConfidence.HIGH if 1/ratio > 5 else SignalConfidence.MEDIUM,
                    price_level=cell.price_level,
                    delta=cell.delta,
                    price_movement=0,
                    volume_ratio=1/ratio,
                    description=f"Sell imbalance {1/ratio:.1f}:1 at ${cell.price_level:.2f}",
                    supporting_data={
                        "ask_volume": cell.ask_volume,
                        "bid_volume": cell.bid_volume
                    }
                ))
        
        return signals
    
    async def _detect_sweep(
        self, 
        symbol: str, 
        trade: TradeExecution
    ) -> Optional[FootprintSignal]:
        """
        Detect sweep pattern in real-time.
        
        Sweep = Aggressive orders clearing multiple price levels rapidly
        Indicates institutional urgency.
        """
        levels = self._price_levels_touched.get(symbol, [])
        
        if len(levels) < self.config.sweep_levels_cleared:
            return None
        
        # Get trades within sweep window
        cutoff = trade.timestamp - timedelta(milliseconds=self.config.sweep_time_window_ms)
        recent = [(t, p) for t, p in levels if t >= cutoff]
        
        if len(recent) < self.config.sweep_levels_cleared:
            return None
        
        # Count unique price levels
        unique_prices = set(p for _, p in recent)
        
        if len(unique_prices) < self.config.sweep_levels_cleared:
            return None
        
        # Calculate total volume in sweep
        trades_in_window = [
            t for t in self._trade_buffer.get(symbol, [])
            if t.timestamp >= cutoff
        ]
        
        total_volume = sum(t.size for t in trades_in_window)
        
        if total_volume < self.config.sweep_min_volume:
            return None
        
        # Determine direction
        prices = sorted(unique_prices)
        if trade.price == max(prices):
            direction = Side.BUY
            description = f"Buy sweep: {len(unique_prices)} levels cleared in {self.config.sweep_time_window_ms}ms"
        else:
            direction = Side.SELL
            description = f"Sell sweep: {len(unique_prices)} levels cleared in {self.config.sweep_time_window_ms}ms"
        
        return FootprintSignal(
            symbol=symbol,
            signal_type=SignalType.SWEEP,
            direction=direction,
            confidence=SignalConfidence.HIGH,
            price_level=trade.price,
            delta=total_volume if direction == Side.BUY else -total_volume,
            price_movement=max(prices) - min(prices),
            volume_ratio=len(unique_prices),
            description=description,
            supporting_data={
                "levels_cleared": len(unique_prices),
                "volume": total_volume,
                "window_ms": self.config.sweep_time_window_ms
            }
        )


# Global instance
footprint_engine = FootprintEngine()
