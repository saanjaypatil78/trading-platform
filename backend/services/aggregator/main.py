"""
Signal Aggregation Service

Unifies signals from multiple sources:
- Orderflow service (footprint patterns)
- Scanner service (technical conditions)
- Brain service (AI analysis)

Provides a single endpoint for consolidated trade signals.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# Models
# =============================================================================

class SignalSource(str, Enum):
    ORDERFLOW = "orderflow"
    SCANNER = "scanner"
    BRAIN = "brain"
    MANUAL = "manual"


class SignalStrength(str, Enum):
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"


class UnifiedSignal(BaseModel):
    """Aggregated signal from multiple sources"""
    symbol: str
    direction: str  # "buy" or "sell"
    strength: SignalStrength
    confidence: float = Field(..., ge=0, le=1)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    # Source signals
    sources: List[SignalSource] = []
    source_details: Dict[str, Any] = {}
    
    # Execution guidance
    suggested_quantity: Optional[float] = None
    suggested_entry: Optional[float] = None
    suggested_stop: Optional[float] = None
    suggested_target: Optional[float] = None
    
    # Risk assessment
    risk_level: str = "medium"
    max_position_pct: float = 2.0  # % of portfolio


class SignalRequest(BaseModel):
    """Request for aggregated signals"""
    symbol: str
    include_orderflow: bool = True
    include_scanner: bool = True
    include_brain: bool = True
    account_size: Optional[float] = None


class MultiSymbolRequest(BaseModel):
    """Request signals for multiple symbols"""
    symbols: List[str]
    include_orderflow: bool = True
    include_scanner: bool = True


# =============================================================================
# Service URLs (configurable via env)
# =============================================================================
import os

ORDERFLOW_URL = os.getenv("ORDERFLOW_SERVICE_URL", "http://localhost:8008")
SCANNER_URL = os.getenv("SCANNER_SERVICE_URL", "http://localhost:8010")
BRAIN_URL = os.getenv("BRAIN_SERVICE_URL", "http://localhost:8007")
BROKER_URL = os.getenv("BROKER_SERVICE_URL", "http://localhost:8009")


# =============================================================================
# Signal Aggregator
# =============================================================================

class SignalAggregator:
    """
    Aggregates signals from multiple services into unified trade signals.
    """
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10.0)
    
    async def close(self):
        await self.client.aclose()
    
    async def get_orderflow_signal(self, symbol: str) -> Optional[Dict]:
        """Fetch orderflow signal for symbol"""
        try:
            # Get current orderbook state
            book_resp = await self.client.get(f"{ORDERFLOW_URL}/orderbook/{symbol}")
            if book_resp.status_code != 200:
                return None
            
            book = book_resp.json()
            
            # Get walls
            walls_resp = await self.client.get(f"{ORDERFLOW_URL}/walls/{symbol}")
            walls = walls_resp.json() if walls_resp.status_code == 200 else {}
            
            # Calculate signal from orderbook imbalance
            bid_depth = sum(b.get("size", 0) for b in book.get("bids", [])[:5])
            ask_depth = sum(a.get("size", 0) for a in book.get("asks", [])[:5])
            
            imbalance = bid_depth / ask_depth if ask_depth > 0 else 1
            
            direction = "buy" if imbalance > 1.3 else ("sell" if imbalance < 0.7 else None)
            
            return {
                "source": "orderflow",
                "direction": direction,
                "imbalance_ratio": imbalance,
                "bid_depth": bid_depth,
                "ask_depth": ask_depth,
                "bid_walls": walls.get("bid_walls", []),
                "ask_walls": walls.get("ask_walls", []),
                "best_bid": book.get("bids", [{}])[0].get("price") if book.get("bids") else None,
                "best_ask": book.get("asks", [{}])[0].get("price") if book.get("asks") else None,
            }
        except Exception as e:
            logger.warning(f"Orderflow signal error for {symbol}: {e}")
            return None
    
    async def get_scanner_signal(self, symbol: str) -> Optional[Dict]:
        """Fetch scanner/technical signal for symbol"""
        try:
            # Get technical indicators
            resp = await self.client.get(f"{SCANNER_URL}/indicators/{symbol}")
            if resp.status_code != 200:
                return None
            
            data = resp.json()
            indicators = data.get("indicators", {})
            
            # Analyze indicators
            rsi = indicators.get("rsi_14", 50)
            macd_data = indicators.get("macd", {})
            macd_line = macd_data.get("macd_line", 0)
            signal_line = macd_data.get("signal_line", 0)
            
            price = data.get("current_price", 0)
            sma_20 = indicators.get("sma_20", price)
            sma_50 = indicators.get("sma_50", price)
            
            # Determine direction
            bullish_signals = 0
            bearish_signals = 0
            
            if rsi < 30:
                bullish_signals += 1  # Oversold
            elif rsi > 70:
                bearish_signals += 1  # Overbought
            
            if macd_line > signal_line:
                bullish_signals += 1
            else:
                bearish_signals += 1
            
            if price > sma_20:
                bullish_signals += 1
            else:
                bearish_signals += 1
            
            direction = "buy" if bullish_signals > bearish_signals else "sell"
            confidence = max(bullish_signals, bearish_signals) / 3
            
            return {
                "source": "scanner",
                "direction": direction,
                "confidence": confidence,
                "rsi": rsi,
                "macd": macd_line,
                "macd_signal": signal_line,
                "price": price,
                "sma_20": sma_20,
                "sma_50": sma_50,
            }
        except Exception as e:
            logger.warning(f"Scanner signal error for {symbol}: {e}")
            return None
    
    async def get_brain_analysis(
        self, 
        symbol: str, 
        indicators: Dict,
        account_size: Optional[float] = None
    ) -> Optional[Dict]:
        """Get AI brain analysis"""
        try:
            # Entry analysis
            entry_resp = await self.client.post(
                f"{BRAIN_URL}/entry-analysis",
                json={
                    "symbol": symbol,
                    "rsi": indicators.get("rsi", 50),
                    "macd": indicators.get("macd", 0),
                    "macd_signal": indicators.get("macd_signal", 0),
                    "volume": 1,
                    "avg_volume": 1
                }
            )
            
            entry_data = entry_resp.json() if entry_resp.status_code == 200 else {}
            
            # Risk assessment (if account size provided)
            risk_data = {}
            if account_size and indicators.get("price"):
                price = indicators["price"]
                stop_pct = 0.02  # 2% stop loss
                
                risk_resp = await self.client.post(
                    f"{BRAIN_URL}/risk-assessment",
                    json={
                        "account_size": account_size,
                        "risk_percent": 2,
                        "entry_price": price,
                        "stop_loss": price * (1 - stop_pct)
                    }
                )
                if risk_resp.status_code == 200:
                    risk_data = risk_resp.json()
            
            return {
                "source": "brain",
                "entry_decision": entry_data.get("result", {}).get("decision"),
                "entry_confidence": entry_data.get("result", {}).get("confidence"),
                "position_size": risk_data.get("result", {}).get("position_size"),
                "risk_amount": risk_data.get("result", {}).get("risk_amount"),
            }
        except Exception as e:
            logger.warning(f"Brain analysis error for {symbol}: {e}")
            return None
    
    async def aggregate_signal(self, request: SignalRequest) -> UnifiedSignal:
        """
        Aggregate signals from all sources into a unified signal.
        """
        symbol = request.symbol
        signals = []
        source_details = {}
        
        # Fetch signals from all sources in parallel
        tasks = []
        
        if request.include_orderflow:
            tasks.append(("orderflow", self.get_orderflow_signal(symbol)))
        
        if request.include_scanner:
            tasks.append(("scanner", self.get_scanner_signal(symbol)))
        
        # Execute parallel fetches
        results = await asyncio.gather(*[t[1] for t in tasks], return_exceptions=True)
        
        for (name, _), result in zip(tasks, results):
            if isinstance(result, dict) and result:
                signals.append(result)
                source_details[name] = result
        
        # Get brain analysis with scanner indicators
        if request.include_brain and "scanner" in source_details:
            brain_result = await self.get_brain_analysis(
                symbol,
                source_details["scanner"],
                request.account_size
            )
            if brain_result:
                signals.append(brain_result)
                source_details["brain"] = brain_result
        
        # Aggregate direction votes
        buy_votes = sum(1 for s in signals if s.get("direction") == "buy")
        sell_votes = sum(1 for s in signals if s.get("direction") == "sell")
        total_votes = buy_votes + sell_votes
        
        if total_votes == 0:
            direction = "hold"
            confidence = 0.0
            strength = SignalStrength.WEAK
        else:
            direction = "buy" if buy_votes > sell_votes else "sell"
            confidence = max(buy_votes, sell_votes) / max(len(signals), 1)
            
            if confidence >= 0.8:
                strength = SignalStrength.STRONG
            elif confidence >= 0.5:
                strength = SignalStrength.MODERATE
            else:
                strength = SignalStrength.WEAK
        
        # Build unified signal
        sources = [SignalSource(s["source"]) for s in signals if "source" in s]
        
        return UnifiedSignal(
            symbol=symbol,
            direction=direction,
            strength=strength,
            confidence=confidence,
            sources=sources,
            source_details=source_details,
            suggested_quantity=source_details.get("brain", {}).get("position_size"),
            suggested_entry=source_details.get("orderflow", {}).get("best_ask") if direction == "buy" else source_details.get("orderflow", {}).get("best_bid"),
        )


# =============================================================================
# FastAPI Application
# =============================================================================

aggregator = SignalAggregator()

app = FastAPI(
    title="Signal Aggregation Service",
    description="Unified trade signals from orderflow, scanner, and AI brain",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown():
    await aggregator.close()


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "sources": {
            "orderflow": ORDERFLOW_URL,
            "scanner": SCANNER_URL,
            "brain": BRAIN_URL
        }
    }


@app.post("/signal", response_model=UnifiedSignal)
async def get_signal(request: SignalRequest):
    """Get aggregated signal for a single symbol"""
    return await aggregator.aggregate_signal(request)


@app.post("/signals")
async def get_signals(request: MultiSymbolRequest):
    """Get aggregated signals for multiple symbols"""
    tasks = [
        aggregator.aggregate_signal(SignalRequest(
            symbol=s,
            include_orderflow=request.include_orderflow,
            include_scanner=request.include_scanner
        ))
        for s in request.symbols
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    signals = []
    for symbol, result in zip(request.symbols, results):
        if isinstance(result, UnifiedSignal):
            signals.append(result.dict())
        else:
            signals.append({"symbol": symbol, "error": str(result)})
    
    return {"signals": signals}


@app.post("/execute")
async def execute_signal(request: SignalRequest):
    """
    Get signal and optionally execute via broker.
    Validates through confirmation mesh before execution.
    """
    # Get aggregated signal
    signal = await aggregator.aggregate_signal(request)
    
    if signal.strength == SignalStrength.WEAK:
        return {
            "executed": False,
            "reason": "Signal too weak",
            "signal": signal.dict()
        }
    
    # Execute via broker's confirmation endpoint
    try:
        async with httpx.AsyncClient() as client:
            exec_resp = await client.post(
                f"{BROKER_URL}/api/v1/orders/execute-confirmed",
                json={
                    "symbol": request.symbol,
                    "side": signal.direction.upper(),
                    "quantity": signal.suggested_quantity or 100,
                    "signal_type": signal.sources[0].value if signal.sources else "manual",
                    "confidence": "high" if signal.confidence > 0.7 else "medium",
                    "max_slippage_pct": 0.5
                },
                timeout=15.0
            )
            
            exec_data = exec_resp.json()
            
            return {
                "executed": exec_data.get("executed", False),
                "order_id": exec_data.get("order_id"),
                "status": exec_data.get("status"),
                "signal": signal.dict()
            }
    except Exception as e:
        return {
            "executed": False,
            "error": str(e),
            "signal": signal.dict()
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8011)
