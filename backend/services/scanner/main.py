"""
Scanner Service - REST API
Exposes scanner functionality via HTTP endpoints.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from backend.services.scanner.scanner_engine import ScannerEngine, ScanResult
from backend.services.scanner.conditions import ScannerConditions, Condition, Operator, SCANNER_TEMPLATES

app = FastAPI(title="Scanner Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

scanner = ScannerEngine()

# ============================================================================
# Request/Response Models
# ============================================================================
class ConditionInput(BaseModel):
    left: str
    operator: str  # ">", "<", ">=", etc.
    right: str

class ScanRequest(BaseModel):
    conditions: List[ConditionInput]
    logic: str = "AND"
    symbols: Optional[List[str]] = None  # If None, use default universe

class TemplateScanRequest(BaseModel):
    template: str
    symbols: Optional[List[str]] = None

class ScanResponse(BaseModel):
    total_scanned: int
    matches: int
    results: List[Dict[str, Any]]

# ============================================================================
# Mock Stock Data (In production, fetch from Market Data Service)
# ============================================================================
def get_mock_universe(symbols: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
    """Generate mock stock data for testing."""
    import random
    random.seed(42)
    
    default_symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", 
                       "WIPRO", "BHARTIARTL", "ITC", "SBIN", "AXISBANK",
                       "MARUTI", "TATAMOTORS", "TATASTEEL", "HINDALCO", "ONGC"]
    
    target_symbols = symbols or default_symbols
    universe = {}
    
    for symbol in target_symbols:
        # Generate 200 days of random price data
        base_price = random.uniform(500, 3000)
        closes = [base_price]
        for _ in range(199):
            change = random.uniform(-0.03, 0.03)
            closes.append(closes[-1] * (1 + change))
        
        volumes = [random.uniform(100000, 5000000) for _ in range(200)]
        
        universe[symbol] = {
            "closes": closes,
            "volumes": volumes,
            "highs": [c * random.uniform(1.0, 1.02) for c in closes],
            "lows": [c * random.uniform(0.98, 1.0) for c in closes],
            "opens": [c * random.uniform(0.99, 1.01) for c in closes]
        }
    
    return universe

# ============================================================================
# API Endpoints
# ============================================================================
@app.get("/health")
async def health_check():
    return {"status": "healthy", "templates": scanner.get_available_templates()}

@app.get("/templates")
async def list_templates():
    """List available scanner templates."""
    return {"templates": scanner.get_available_templates()}

@app.post("/scan", response_model=ScanResponse)
async def run_scan(request: ScanRequest):
    """Run a custom scanner with specified conditions."""
    try:
        # Build conditions
        conditions = []
        op_map = {
            ">": Operator.GT, ">=": Operator.GTE,
            "<": Operator.LT, "<=": Operator.LTE,
            "==": Operator.EQ, "!=": Operator.NEQ,
        }
        
        for c in request.conditions:
            conditions.append(Condition(
                left=c.left,
                operator=op_map.get(c.operator, Operator.GT),
                right=c.right
            ))
        
        scanner_conditions = ScannerConditions(conditions=conditions, logic=request.logic)
        
        # Get stock data
        universe = get_mock_universe(request.symbols)
        
        # Run scan
        results = await scanner.scan(scanner_conditions, universe)
        
        return ScanResponse(
            total_scanned=len(universe),
            matches=len(results),
            results=[r.dict() for r in results]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/template/{template_name}", response_model=ScanResponse)
async def run_template_scan(template_name: str, request: Optional[TemplateScanRequest] = None):
    """Run a pre-built scanner template."""
    try:
        if template_name not in scanner.get_available_templates():
            raise HTTPException(status_code=404, detail=f"Template '{template_name}' not found")
        
        symbols = request.symbols if request else None
        universe = get_mock_universe(symbols)
        
        if hasattr(scanner, 'scan_template'): 
             # Refactor scan_template to be async or wrap it
             # Attempting to scan manually using template conditions
             from backend.services.scanner.conditions import SCANNER_TEMPLATES
             template_conditions = SCANNER_TEMPLATES.get(template_name)
             results = await scanner.scan(template_conditions, universe)
        else:
             matched_templates = SCANNER_TEMPLATES.get(template_name)
             results = await scanner.scan(matched_templates, universe)
        
        return ScanResponse(
            total_scanned=len(universe),
            matches=len(results),
            results=[r.dict() for r in results]
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/indicators/{symbol}")
async def get_indicators(symbol: str):
    """Get current indicator values for a symbol."""
    universe = get_mock_universe([symbol])
    
    if symbol not in universe:
        raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found")
    
    data = universe[symbol]
    closes = data["closes"]
    
    from backend.services.scanner.indicators import rsi, sma, ema, macd, bollinger_bands
    
    return {
        "symbol": symbol,
        "current_price": closes[-1],
        "indicators": {
            "rsi_14": rsi(closes, 14),
            "sma_20": sma(closes, 20),
            "sma_50": sma(closes, 50),
            "sma_200": sma(closes, 200),
            "ema_12": ema(closes, 12),
            "ema_26": ema(closes, 26),
            "macd": macd(closes),
            "bollinger": bollinger_bands(closes, 20),
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8008)
