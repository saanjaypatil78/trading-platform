"""
Order Service - REST API
Unified order management interface (OpenAlgo-style).
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from backend.services.broker.paper_broker import PaperBroker
from backend.services.broker.adapter import OrderType, OrderSide, ProductType

app = FastAPI(title="Order Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize paper broker with 10 lakh capital
broker = PaperBroker(initial_capital=1000000)
broker.connect({})

# ============================================================================
# Request Models
# ============================================================================
class PlaceOrderRequest(BaseModel):
    symbol: str
    side: str  # "BUY" or "SELL"
    quantity: int
    order_type: str = "MARKET"  # MARKET, LIMIT, SL, SL-M
    product: str = "MIS"  # MIS, CNC, NRML
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    exchange: str = "NSE"

class ModifyOrderRequest(BaseModel):
    quantity: Optional[int] = None
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    order_type: Optional[str] = None

# ============================================================================
# API Endpoints
# ============================================================================
@app.get("/health")
async def health_check():
    funds = broker.get_funds()
    return {
        "status": "healthy",
        "broker": "paper",
        "capital": funds["total_capital"],
        "available": funds["available_cash"]
    }

@app.post("/api/v1/orders/place")
async def place_order(request: PlaceOrderRequest):
    """Place a new order."""
    try:
        order = broker.place_order(
            symbol=request.symbol,
            side=OrderSide(request.side),
            quantity=request.quantity,
            order_type=OrderType(request.order_type),
            product=ProductType(request.product),
            price=request.price,
            trigger_price=request.trigger_price,
            exchange=request.exchange
        )
        return order.dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/v1/orders/{order_id}")
async def modify_order(order_id: str, request: ModifyOrderRequest):
    """Modify an existing order."""
    try:
        order = broker.modify_order(
            order_id=order_id,
            quantity=request.quantity,
            price=request.price,
            trigger_price=request.trigger_price,
            order_type=OrderType(request.order_type) if request.order_type else None
        )
        return order.dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/v1/orders/{order_id}")
async def cancel_order(order_id: str):
    """Cancel an order."""
    success = broker.cancel_order(order_id)
    if not success:
        raise HTTPException(status_code=404, detail="Order not found or cannot be cancelled")
    return {"status": "cancelled", "order_id": order_id}

@app.get("/api/v1/orders")
async def get_orders():
    """Get all orders."""
    orders = broker.get_orders()
    return {"orders": [o.dict() for o in orders]}

@app.get("/api/v1/orders/{order_id}")
async def get_order(order_id: str):
    """Get a specific order."""
    order = broker.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order.dict()

@app.get("/api/v1/positions")
async def get_positions():
    """Get current positions."""
    positions = broker.get_positions()
    return {"positions": [p.dict() for p in positions]}

@app.get("/api/v1/holdings")
async def get_holdings():
    """Get holdings."""
    holdings = broker.get_holdings()
    return {"holdings": [h.dict() for h in holdings]}

@app.get("/api/v1/funds")
async def get_funds():
    """Get available funds."""
    return broker.get_funds()

@app.get("/api/v1/quote/{symbol}")
async def get_quote(symbol: str, exchange: str = "NSE"):
    """Get real-time quote for a symbol."""
    return broker.get_quote(symbol, exchange)

# ============================================================================
# Webhook Endpoint (TradingView integration)
# ============================================================================
class WebhookSignal(BaseModel):
    symbol: str
    action: str  # "buy", "sell", "close"
    quantity: Optional[int] = 1
    price: Optional[float] = None
    strategy: Optional[str] = None

@app.post("/api/v1/webhook")
async def webhook_handler(signal: WebhookSignal):
    """
    Handle incoming webhook signals from TradingView, Amibroker, etc.
    """
    try:
        action = signal.action.lower()
        
        if action == "buy":
            order = broker.place_order(
                symbol=signal.symbol,
                side=OrderSide.BUY,
                quantity=signal.quantity or 1,
                order_type=OrderType.MARKET,
                product=ProductType.MIS
            )
        elif action == "sell":
            order = broker.place_order(
                symbol=signal.symbol,
                side=OrderSide.SELL,
                quantity=signal.quantity or 1,
                order_type=OrderType.MARKET,
                product=ProductType.MIS
            )
        elif action == "close":
            # Close all positions for this symbol
            positions = broker.get_positions()
            for pos in positions:
                if pos.symbol == signal.symbol and pos.quantity > 0:
                    order = broker.place_order(
                        symbol=signal.symbol,
                        side=OrderSide.SELL,
                        quantity=pos.quantity,
                        order_type=OrderType.MARKET,
                        product=pos.product
                    )
            return {"status": "positions_closed", "symbol": signal.symbol}
        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {action}")
        
        return {
            "status": "signal_processed",
            "order_id": order.order_id,
            "order_status": order.status.value
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8009)
