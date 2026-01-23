"""
Unit Tests for Footprint Detection Engine

Tests the core detection algorithms:
- Absorption (high volume, low price movement)
- Exhaustion (declining volume at S/R)
- Imbalance (3:1+ ratio)
- Sweep (multiple levels cleared)
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.orderflow.l2_models import (
    TradeExecution, Side, FootprintCluster, FootprintCell,
    SignalType, SignalConfidence
)
from services.orderflow.footprint_engine import FootprintEngine, DetectionConfig


class TestAbsorptionDetection:
    """Test absorption pattern detection"""
    
    def setup_method(self):
        self.engine = FootprintEngine(DetectionConfig(
            absorption_volume_threshold=1000,
            absorption_price_move_max=0.1,
            absorption_delta_threshold=0.7
        ))
    
    def test_detect_absorption_bullish(self):
        """
        Bullish absorption: Heavy sell volume absorbed with minimal price drop.
        Indicates hidden buyer (iceberg order).
        """
        # Create cluster with negative delta but small price range
        cluster = FootprintCluster(
            symbol="AAPL",
            period_start=datetime.now(),
            period_end=datetime.now(),
            cells=[],
            high_price=150.05,
            low_price=150.00,  # Only 0.033% range
            total_buy_volume=1000,
            total_sell_volume=8000  # Heavy selling
        )
        
        signal = self.engine._detect_absorption("AAPL", cluster)
        
        assert signal is not None
        assert signal.signal_type == SignalType.ABSORPTION
        assert signal.direction == Side.BUY  # Bullish absorption
        assert signal.delta < 0  # Negative delta (selling)
        assert "absorbed" in signal.description.lower()
    
    def test_detect_absorption_bearish(self):
        """
        Bearish absorption: Heavy buy volume absorbed with minimal price rise.
        Indicates hidden seller.
        """
        cluster = FootprintCluster(
            symbol="AAPL",
            period_start=datetime.now(),
            period_end=datetime.now(),
            cells=[],
            high_price=150.05,
            low_price=150.00,
            total_buy_volume=8000,  # Heavy buying
            total_sell_volume=1000
        )
        
        signal = self.engine._detect_absorption("AAPL", cluster)
        
        assert signal is not None
        assert signal.signal_type == SignalType.ABSORPTION
        assert signal.direction == Side.SELL  # Bearish absorption
        assert signal.delta > 0  # Positive delta (buying)
    
    def test_no_absorption_with_large_price_move(self):
        """No absorption if price moved significantly"""
        cluster = FootprintCluster(
            symbol="AAPL",
            period_start=datetime.now(),
            period_end=datetime.now(),
            cells=[],
            high_price=152.00,  # 1.3% range - too large
            low_price=150.00,
            total_buy_volume=1000,
            total_sell_volume=8000
        )
        
        signal = self.engine._detect_absorption("AAPL", cluster)
        assert signal is None
    
    def test_no_absorption_with_balanced_volume(self):
        """No absorption if volume is balanced"""
        cluster = FootprintCluster(
            symbol="AAPL",
            period_start=datetime.now(),
            period_end=datetime.now(),
            cells=[],
            high_price=150.05,
            low_price=150.00,
            total_buy_volume=5000,
            total_sell_volume=5000  # Balanced
        )
        
        signal = self.engine._detect_absorption("AAPL", cluster)
        assert signal is None


class TestExhaustionDetection:
    """Test exhaustion pattern detection"""
    
    def setup_method(self):
        self.engine = FootprintEngine(DetectionConfig(
            exhaustion_volume_decline_pct=0.5,
            exhaustion_lookback_periods=3
        ))
    
    def test_detect_exhaustion_at_resistance(self):
        """Detect bearish exhaustion at resistance level"""
        # Build up history with higher volumes
        base_time = datetime.now()
        
        for i in range(3):
            cluster = FootprintCluster(
                symbol="AAPL",
                period_start=base_time + timedelta(seconds=i*60),
                period_end=base_time + timedelta(seconds=(i+1)*60),
                cells=[],
                high_price=150.00 + i,
                low_price=149.00 + i,
                total_buy_volume=5000,
                total_sell_volume=3000
            )
            self.engine._cluster_history["AAPL"].append(cluster)
        
        # Current cluster has much lower volume at highs
        current = FootprintCluster(
            symbol="AAPL",
            period_start=base_time + timedelta(seconds=180),
            period_end=base_time + timedelta(seconds=240),
            cells=[],
            high_price=153.00,  # At recent highs
            low_price=152.00,
            total_buy_volume=1000,  # Much lower volume
            total_sell_volume=500
        )
        
        signal = self.engine._detect_exhaustion("AAPL", current)
        
        assert signal is not None
        assert signal.signal_type == SignalType.EXHAUSTION
        assert signal.direction == Side.SELL  # Bearish exhaustion at highs


class TestImbalanceDetection:
    """Test imbalance pattern detection"""
    
    def setup_method(self):
        self.engine = FootprintEngine(DetectionConfig(
            imbalance_ratio_threshold=3.0,
            imbalance_min_volume=1000
        ))
    
    def test_detect_buy_imbalance(self):
        """Detect significant buying imbalance"""
        cluster = FootprintCluster(
            symbol="AAPL",
            period_start=datetime.now(),
            period_end=datetime.now(),
            cells=[
                FootprintCell(
                    price_level=150.00,
                    time_bucket=datetime.now(),
                    bid_volume=500,
                    ask_volume=2000  # 4:1 ratio
                )
            ],
            high_price=150.00,
            low_price=150.00,
            total_buy_volume=2000,
            total_sell_volume=500
        )
        
        signals = self.engine._detect_imbalances("AAPL", cluster)
        
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.IMBALANCE
        assert signals[0].direction == Side.BUY
        assert signals[0].volume_ratio >= 3.0
    
    def test_detect_sell_imbalance(self):
        """Detect significant selling imbalance"""
        cluster = FootprintCluster(
            symbol="AAPL",
            period_start=datetime.now(),
            period_end=datetime.now(),
            cells=[
                FootprintCell(
                    price_level=150.00,
                    time_bucket=datetime.now(),
                    bid_volume=2500,  # Heavy selling (hitting bids)
                    ask_volume=500
                )
            ],
            high_price=150.00,
            low_price=150.00,
            total_buy_volume=500,
            total_sell_volume=2500
        )
        
        signals = self.engine._detect_imbalances("AAPL", cluster)
        
        assert len(signals) == 1
        assert signals[0].signal_type == SignalType.IMBALANCE
        assert signals[0].direction == Side.SELL


class TestConfirmationMesh:
    """Test confirmation mesh validation"""
    
    @pytest.fixture
    def mesh(self):
        from services.orderflow.confirmation_mesh import ConfirmationMesh
        return ConfirmationMesh()
    
    @pytest.fixture
    def valid_signal(self):
        from services.orderflow.l2_models import FootprintSignal
        return FootprintSignal(
            symbol="AAPL",
            signal_type=SignalType.ABSORPTION,
            direction=Side.BUY,
            confidence=SignalConfidence.HIGH,
            price_level=150.00,
            delta=-5000,
            price_movement=0.05
        )
    
    @pytest.mark.asyncio
    async def test_reject_low_confidence(self, mesh, valid_signal):
        """Reject low confidence signals when configured"""
        from services.orderflow.l2_models import ConfirmationRequest
        
        mesh.config.require_high_confidence = True
        valid_signal.confidence = SignalConfidence.LOW
        
        request = ConfirmationRequest(
            signal=valid_signal,
            symbol="AAPL",
            side=Side.BUY,
            quantity=100,
            require_liquidity=False
        )
        
        result = await mesh.validate(request)
        
        assert not result.approved
        assert "footprint" in result.rejection_reason.lower()
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_blocks(self, mesh, valid_signal):
        """Circuit breaker should block all executions"""
        from services.orderflow.l2_models import ConfirmationRequest
        
        mesh.trip_circuit_breaker("AAPL", "Test trip")
        
        request = ConfirmationRequest(
            signal=valid_signal,
            symbol="AAPL",
            side=Side.BUY,
            quantity=100
        )
        
        result = await mesh.validate(request)
        
        assert not result.approved
        assert "circuit" in result.rejection_reason.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
