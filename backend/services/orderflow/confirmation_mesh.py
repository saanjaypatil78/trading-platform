"""
Confirmation Mesh - Signal Validation & Execution Orchestration

Validates trade signals through multiple layers:
1. Footprint pattern confirmation
2. L2 liquidity verification
3. Risk management checks
4. Circuit breaker enforcement
"""

import logging
from typing import Optional, List, Dict, Callable
from datetime import datetime, timedelta
from enum import Enum
import asyncio

from .l2_models import (
    FootprintSignal, ConfirmationRequest, ConfirmationResult,
    CircuitBreakerStatus, Side, SignalConfidence
)
from .orderbook_manager import OrderBookManager, orderbook_manager
from .footprint_engine import FootprintEngine, footprint_engine

logger = logging.getLogger(__name__)


class ValidationStage(str, Enum):
    """Stages in the confirmation pipeline"""
    FOOTPRINT_CHECK = "footprint_check"
    LIQUIDITY_CHECK = "liquidity_check"
    RISK_CHECK = "risk_check"
    CIRCUIT_BREAKER = "circuit_breaker"
    EXECUTION = "execution"


class ConfirmationMesh:
    """
    Multi-layer validation mesh for trade execution.
    Ensures signals pass all checks before reaching the broker.
    """
    
    def __init__(
        self,
        orderbook_mgr: Optional[OrderBookManager] = None,
        footprint_eng: Optional[FootprintEngine] = None
    ):
        self.orderbook_manager = orderbook_mgr or orderbook_manager
        self.footprint_engine = footprint_eng or footprint_engine
        
        # Circuit breakers per symbol
        self._circuit_breakers: Dict[str, CircuitBreakerStatus] = {}
        
        # Configuration
        self.config = ConfirmationConfig()
        
        # Execution callbacks
        self._on_approved: List[Callable] = []
        self._on_rejected: List[Callable] = []
        
        # Metrics
        self._metrics = {
            "total_requests": 0,
            "approved": 0,
            "rejected": 0,
            "rejection_reasons": {}
        }
    
    def on_approved(self, callback: Callable):
        """Register callback for approved executions"""
        self._on_approved.append(callback)
    
    def on_rejected(self, callback: Callable):
        """Register callback for rejected executions"""
        self._on_rejected.append(callback)
    
    async def validate(self, request: ConfirmationRequest) -> ConfirmationResult:
        """
        Run full validation pipeline on a confirmation request.
        Returns approval or rejection with detailed reasoning.
        """
        self._metrics["total_requests"] += 1
        symbol = request.symbol
        
        logger.info(f"Validating execution request for {symbol}")
        
        # Stage 1: Circuit Breaker Check
        breaker = self._circuit_breakers.get(symbol)
        if breaker and breaker.is_tripped:
            return await self._reject(
                request,
                "Circuit breaker tripped",
                ValidationStage.CIRCUIT_BREAKER
            )
        
        # Stage 2: Footprint Confirmation
        if not await self._validate_footprint(request):
            return await self._reject(
                request,
                "Footprint pattern not confirmed",
                ValidationStage.FOOTPRINT_CHECK
            )
        
        # Stage 3: Liquidity Check
        if request.require_liquidity:
            liquidity_result = await self._validate_liquidity(request)
            if not liquidity_result["sufficient"]:
                return await self._reject(
                    request,
                    f"Insufficient liquidity: {liquidity_result['reason']}",
                    ValidationStage.LIQUIDITY_CHECK
                )
        
        # Stage 4: Risk Check
        risk_result = await self._validate_risk(request)
        if not risk_result["passed"]:
            return await self._reject(
                request,
                f"Risk check failed: {risk_result['reason']}",
                ValidationStage.RISK_CHECK
            )
        
        # All checks passed - approve
        return await self._approve(request, liquidity_result if request.require_liquidity else None)
    
    async def _validate_footprint(self, request: ConfirmationRequest) -> bool:
        """Verify that footprint pattern supports the trade direction"""
        signal = request.signal
        
        # Check signal confidence
        if signal.confidence == SignalConfidence.LOW:
            if self.config.require_high_confidence:
                return False
        
        # Verify signal age
        signal_age = datetime.now() - signal.timestamp
        if signal_age > self.config.max_signal_age:
            logger.warning(f"Signal too old: {signal_age}")
            return False
        
        # Check delta alignment
        if request.side == Side.BUY and signal.delta < 0:
            # Buying on negative delta (selling pressure) - could be absorption
            if signal.signal_type.value != "absorption":
                return False
        elif request.side == Side.SELL and signal.delta > 0:
            # Selling on positive delta (buying pressure) - could be absorption
            if signal.signal_type.value != "absorption":
                return False
        
        return True
    
    async def _validate_liquidity(self, request: ConfirmationRequest) -> Dict:
        """Check if sufficient liquidity exists at acceptable slippage"""
        symbol = request.symbol
        quantity = request.quantity
        side = request.side
        max_slippage = request.max_slippage_pct
        
        # Get slippage estimate from orderbook
        estimate = self.orderbook_manager.estimate_slippage(symbol, side, quantity)
        
        if estimate is None:
            return {
                "sufficient": False,
                "reason": "No orderbook data available"
            }
        
        avg_price, slippage_pct = estimate
        
        if slippage_pct > max_slippage:
            return {
                "sufficient": False,
                "reason": f"Estimated slippage {slippage_pct:.2f}% exceeds max {max_slippage}%",
                "estimated_price": avg_price,
                "slippage_pct": slippage_pct
            }
        
        # Check for reasonable liquidity depth
        book = self.orderbook_manager.get_orderbook(symbol)
        if book:
            available = (
                book.total_ask_size(10) if side == Side.BUY
                else book.total_bid_size(10)
            )
            
            if available < quantity * self.config.min_liquidity_ratio:
                return {
                    "sufficient": False,
                    "reason": f"Thin liquidity: {available:.0f} vs needed {quantity:.0f}",
                    "available_liquidity": available
                }
        
        return {
            "sufficient": True,
            "estimated_price": avg_price,
            "slippage_pct": slippage_pct,
            "available_liquidity": available if book else None
        }
    
    async def _validate_risk(self, request: ConfirmationRequest) -> Dict:
        """Apply risk management rules"""
        # Position sizing check
        if request.quantity <= 0:
            return {"passed": False, "reason": "Invalid quantity"}
        
        if request.quantity > self.config.max_position_size:
            return {
                "passed": False,
                "reason": f"Quantity {request.quantity} exceeds max {self.config.max_position_size}"
            }
        
        # Notional value check (if limit price provided)
        if request.limit_price:
            notional = request.quantity * request.limit_price
            if notional > self.config.max_notional_value:
                return {
                    "passed": False,
                    "reason": f"Notional ${notional:.2f} exceeds max ${self.config.max_notional_value}"
                }
        
        return {"passed": True}
    
    async def _approve(
        self,
        request: ConfirmationRequest,
        liquidity_data: Optional[Dict]
    ) -> ConfirmationResult:
        """Create approval result and emit callbacks"""
        self._metrics["approved"] += 1
        
        result = ConfirmationResult(
            approved=True,
            signal=request.signal,
            liquidity_check=True,
            footprint_confirmed=True,
            risk_check=True,
            recommended_quantity=request.quantity,
            recommended_price=liquidity_data.get("estimated_price") if liquidity_data else None,
            available_liquidity=liquidity_data.get("available_liquidity") if liquidity_data else None
        )
        
        logger.info(f"Execution APPROVED for {request.symbol}")
        
        # Emit callbacks
        for cb in self._on_approved:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(result)
                else:
                    cb(result)
            except Exception as e:
                logger.error(f"Approval callback error: {e}")
        
        return result
    
    async def _reject(
        self,
        request: ConfirmationRequest,
        reason: str,
        stage: ValidationStage
    ) -> ConfirmationResult:
        """Create rejection result and emit callbacks"""
        self._metrics["rejected"] += 1
        self._metrics["rejection_reasons"][stage.value] = (
            self._metrics["rejection_reasons"].get(stage.value, 0) + 1
        )
        
        result = ConfirmationResult(
            approved=False,
            signal=request.signal,
            liquidity_check=(stage != ValidationStage.LIQUIDITY_CHECK),
            footprint_confirmed=(stage != ValidationStage.FOOTPRINT_CHECK),
            risk_check=(stage != ValidationStage.RISK_CHECK),
            rejection_reason=f"[{stage.value}] {reason}"
        )
        
        logger.warning(f"Execution REJECTED for {request.symbol}: {reason}")
        
        # Emit callbacks
        for cb in self._on_rejected:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(result)
                else:
                    cb(result)
            except Exception as e:
                logger.error(f"Rejection callback error: {e}")
        
        return result
    
    def trip_circuit_breaker(self, symbol: str, reason: str, cooldown_seconds: int = 300):
        """Manually trip circuit breaker for a symbol"""
        self._circuit_breakers[symbol] = CircuitBreakerStatus(
            symbol=symbol,
            is_tripped=True,
            trip_reason=reason,
            tripped_at=datetime.now(),
            cooldown_until=datetime.now() + timedelta(seconds=cooldown_seconds)
        )
        logger.warning(f"Circuit breaker TRIPPED for {symbol}: {reason}")
    
    def reset_circuit_breaker(self, symbol: str):
        """Reset circuit breaker for a symbol"""
        if symbol in self._circuit_breakers:
            self._circuit_breakers[symbol].is_tripped = False
            logger.info(f"Circuit breaker RESET for {symbol}")
    
    def get_metrics(self) -> Dict:
        """Get validation metrics"""
        return self._metrics.copy()


class ConfirmationConfig:
    """Configuration for confirmation mesh"""
    
    def __init__(self):
        # Signal validation
        self.require_high_confidence = False
        self.max_signal_age = timedelta(seconds=30)
        
        # Liquidity requirements
        self.min_liquidity_ratio = 2.0  # Need 2x quantity in book
        
        # Risk limits
        self.max_position_size = 10000
        self.max_notional_value = 100000
        
        # Circuit breaker
        self.auto_trip_consecutive_rejects = 5
        self.cooldown_seconds = 300


# Global instance
confirmation_mesh = ConfirmationMesh()
