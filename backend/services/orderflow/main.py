"""
Orderflow Service - Main FastAPI Application

Exposes REST and WebSocket endpoints for:
- L2 market depth streaming
- Footprint signal detection
- Execution confirmation
"""

import os
import logging
import asyncio
from typing import Optional, List
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .l2_models import (
    OrderBookSnapshot, FootprintSignal, ConfirmationRequest, 
    ConfirmationResult, SignalType, Side
)
from .l2_provider import AlpacaL2Provider, MassiveL2Provider
from .orderbook_manager import orderbook_manager
from .footprint_engine import footprint_engine, DetectionConfig
from .confirmation_mesh import confirmation_mesh

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# L2 providers
l2_providers = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    logger.info("Starting Orderflow Service...")
    
    # Initialize L2 providers
    if os.getenv("ALPACA_API_KEY"):
        l2_providers["alpaca"] = AlpacaL2Provider(
            api_key=os.getenv("ALPACA_API_KEY"),
            api_secret=os.getenv("ALPACA_API_SECRET", ""),
            paper=os.getenv("ALPACA_PAPER", "true").lower() == "true"
        )
        logger.info("Alpaca L2 provider configured")
    
    if os.getenv("MASSIVE_API_KEY"):
        l2_providers["massive"] = MassiveL2Provider(
            api_key=os.getenv("MASSIVE_API_KEY"),
            realtime=os.getenv("MASSIVE_REALTIME", "false").lower() == "true"
        )
        logger.info("Massive L2 provider configured")
    
    # Fallback to mock provider if no API keys configured
    if not l2_providers:
        from .mock_provider import MockL2Provider
        l2_providers["mock"] = MockL2Provider(
            base_price=150.0,  # AAPL-like price
            tick_size=0.01,
            levels=10,
            volatility=0.0005
        )
        logger.warning("⚠️  No API keys found - using MOCK L2 provider for development")
    
    # Wire up callbacks
    for provider in l2_providers.values():
        provider.on_orderbook(orderbook_manager.update_snapshot)
        provider.on_trade(footprint_engine.process_trade)
    
    yield
    
    # Cleanup
    logger.info("Shutting down Orderflow Service...")
    for provider in l2_providers.values():
        await provider.disconnect()


app = FastAPI(
    title="Orderflow Service",
    description="L2 market depth and footprint detection API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Request/Response Models
# =============================================================================

class SubscribeRequest(BaseModel):
    symbol: str
    provider: str = "alpaca"


class ExecuteRequest(BaseModel):
    symbol: str
    side: Side
    quantity: float
    signal_type: SignalType
    confidence: str = "medium"
    max_slippage_pct: float = 0.5


class HealthResponse(BaseModel):
    status: str
    providers: List[str]
    active_symbols: List[str]
    connection_count: int


# =============================================================================
# REST Endpoints
# =============================================================================

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Check service health and status"""
    return HealthResponse(
        status="healthy",
        providers=list(l2_providers.keys()),
        active_symbols=list(orderbook_manager._orderbooks.keys()),
        connection_count=len(orderbook_manager._orderbooks)
    )


@app.post("/subscribe")
async def subscribe_symbol(request: SubscribeRequest):
    """Subscribe to L2 updates for a symbol"""
    provider = l2_providers.get(request.provider)
    if not provider:
        raise HTTPException(status_code=400, detail=f"Provider {request.provider} not configured")
    
    if not provider.is_connected:
        connected = await provider.connect()
        if not connected:
            raise HTTPException(status_code=500, detail="Failed to connect to provider")
    
    success = await provider.subscribe(request.symbol)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to subscribe")
    
    return {"status": "subscribed", "symbol": request.symbol, "provider": request.provider}


@app.post("/unsubscribe")
async def unsubscribe_symbol(request: SubscribeRequest):
    """Unsubscribe from L2 updates"""
    provider = l2_providers.get(request.provider)
    if provider:
        await provider.unsubscribe(request.symbol)
    return {"status": "unsubscribed", "symbol": request.symbol}


@app.get("/orderbook/{symbol}", response_model=Optional[OrderBookSnapshot])
async def get_orderbook(symbol: str):
    """Get current orderbook snapshot for symbol"""
    book = orderbook_manager.get_orderbook(symbol)
    if not book:
        raise HTTPException(status_code=404, detail=f"No orderbook data for {symbol}")
    return book


@app.get("/walls/{symbol}")
async def get_walls(symbol: str):
    """Get current bid/ask walls for symbol"""
    return orderbook_manager.get_walls(symbol)


@app.get("/slippage/{symbol}")
async def estimate_slippage(
    symbol: str,
    side: Side = Query(...),
    quantity: float = Query(...)
):
    """Estimate execution slippage for an order"""
    result = orderbook_manager.estimate_slippage(symbol, side, quantity)
    if result is None:
        raise HTTPException(status_code=400, detail="Insufficient data for slippage estimate")
    
    avg_price, slippage_pct = result
    return {
        "symbol": symbol,
        "side": side,
        "quantity": quantity,
        "estimated_avg_price": avg_price,
        "estimated_slippage_pct": slippage_pct
    }


@app.post("/analyze/{symbol}")
async def analyze_footprint(symbol: str, window_seconds: int = 60):
    """Analyze footprint patterns for symbol"""
    # Flush buffer to get latest cluster
    cluster = await footprint_engine.flush_buffer(symbol)
    
    if not cluster:
        return {"signals": [], "message": "No trade data to analyze"}
    
    # Get recent signals (stored during analysis)
    # In production, you'd have a signal store
    return {
        "cluster": {
            "period_start": cluster.period_start,
            "period_end": cluster.period_end,
            "total_delta": cluster.total_delta,
            "buy_volume": cluster.total_buy_volume,
            "sell_volume": cluster.total_sell_volume,
            "poc": cluster.poc,
            "imbalances": len(cluster.imbalances())
        }
    }


@app.post("/validate", response_model=ConfirmationResult)
async def validate_execution(request: ExecuteRequest):
    """Validate execution through confirmation mesh"""
    # Build signal from request
    signal = FootprintSignal(
        symbol=request.symbol,
        signal_type=request.signal_type,
        direction=request.side,
        confidence=request.confidence,
        price_level=0,  # Would come from real signal
        delta=0,
        price_movement=0,
        description=f"Manual request for {request.symbol}"
    )
    
    # Build confirmation request
    confirm_req = ConfirmationRequest(
        signal=signal,
        symbol=request.symbol,
        side=request.side,
        quantity=request.quantity,
        max_slippage_pct=request.max_slippage_pct
    )
    
    # Validate
    result = await confirmation_mesh.validate(confirm_req)
    return result


@app.get("/metrics")
async def get_metrics():
    """Get confirmation mesh metrics"""
    return confirmation_mesh.get_metrics()


@app.post("/circuit-breaker/{symbol}/trip")
async def trip_circuit_breaker(symbol: str, reason: str = "Manual trip"):
    """Manually trip circuit breaker for symbol"""
    confirmation_mesh.trip_circuit_breaker(symbol, reason)
    return {"status": "tripped", "symbol": symbol, "reason": reason}


@app.post("/circuit-breaker/{symbol}/reset")
async def reset_circuit_breaker(symbol: str):
    """Reset circuit breaker for symbol"""
    confirmation_mesh.reset_circuit_breaker(symbol)
    return {"status": "reset", "symbol": symbol}


# =============================================================================
# WebSocket Endpoints
# =============================================================================

@app.websocket("/ws/l2/{symbol}")
async def websocket_l2(websocket: WebSocket, symbol: str, provider: str = "alpaca"):
    """Stream L2 orderbook updates"""
    await websocket.accept()
    logger.info(f"WebSocket connected for L2: {symbol}")
    
    l2_provider = l2_providers.get(provider)
    if not l2_provider:
        await websocket.close(code=1008, reason=f"Provider {provider} not available")
        return
    
    # Connect and subscribe if needed
    if not l2_provider.is_connected:
        await l2_provider.connect()
    await l2_provider.subscribe(symbol)
    
    # Callback to send updates
    async def send_update(snapshot: OrderBookSnapshot):
        if snapshot.symbol == symbol:
            try:
                await websocket.send_json(snapshot.model_dump(mode="json"))
            except Exception:
                pass
    
    l2_provider.on_orderbook(send_update)
    
    try:
        while True:
            # Keep connection alive, handle client messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for L2: {symbol}")
        await l2_provider.unsubscribe(symbol)


@app.websocket("/ws/signals/{symbol}")
async def websocket_signals(websocket: WebSocket, symbol: str):
    """Stream footprint signals"""
    await websocket.accept()
    logger.info(f"WebSocket connected for signals: {symbol}")
    
    # Callback to send signals
    async def send_signal(signal: FootprintSignal):
        if signal.symbol == symbol:
            try:
                await websocket.send_json(signal.model_dump(mode="json"))
            except Exception:
                pass
    
    footprint_engine.on_signal(send_signal)
    
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for signals: {symbol}")


# =============================================================================
# Run Application
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8008)
