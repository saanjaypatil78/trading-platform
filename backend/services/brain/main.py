"""
AI Brain Service - REST API for Strategic Thinking
Exposes all thinking strategies via HTTP endpoints.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from backend.shared.brain.strategic_thinking import StrategicThinker, ThinkingStrategy
from backend.shared.brain.memory import KnowledgeGraph

app = FastAPI(title="AI Brain Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Persistent memory instance (file-backed)
MEMORY_PATH = os.path.join(os.path.dirname(__file__), "brain_memory.json")
memory = KnowledgeGraph(persist_path=MEMORY_PATH)
thinker = StrategicThinker(memory=memory)

# ============================================================================
# Request/Response Models
# ============================================================================
class EntryAnalysisRequest(BaseModel):
    symbol: str
    rsi: float = 50
    macd: float = 0
    macd_signal: float = 0
    volume: float = 0
    avg_volume: float = 1

class RiskAssessmentRequest(BaseModel):
    account_size: float
    risk_percent: float = 2
    entry_price: float
    stop_loss: float

class RegimeDetectionRequest(BaseModel):
    price: float
    sma_50: float
    sma_200: float
    atr: float = 2

class PortfolioRebalanceRequest(BaseModel):
    holdings: Dict[str, float]  # {"AAPL": 5000, ...}
    targets: Dict[str, float]   # {"AAPL": 40, ...} percentages

class EarningsPlayRequest(BaseModel):
    symbol: str
    iv: float
    iv_rank: float
    expected_move: float = 5

class ThinkingResponse(BaseModel):
    strategy: str
    result: Dict[str, Any]
    trace: List[Dict[str, Any]]

# ============================================================================
# API Endpoints
# ============================================================================
@app.get("/health")
async def health_check():
    return {"status": "healthy", "memory_entities": len(memory.entities)}

@app.post("/entry-analysis", response_model=ThinkingResponse)
async def entry_analysis(request: EntryAnalysisRequest):
    """Analyze entry signals using RSI, MACD, and Volume."""
    try:
        result = thinker.think(ThinkingStrategy.ENTRY_ANALYSIS, request.dict())
        return ThinkingResponse(
            strategy="entry_analysis",
            result={"decision": result["decision"], "confidence": result["confidence"]},
            trace=result["trace"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/risk-assessment", response_model=ThinkingResponse)
async def risk_assessment(request: RiskAssessmentRequest):
    """Calculate optimal position size based on risk parameters."""
    try:
        result = thinker.think(ThinkingStrategy.RISK_ASSESSMENT, request.dict())
        return ThinkingResponse(
            strategy="risk_assessment",
            result={
                "position_size": result.get("position_size", 0),
                "position_value": result.get("position_value", 0),
                "risk_amount": result.get("risk_amount", 0)
            },
            trace=result["trace"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/regime-detection", response_model=ThinkingResponse)
async def regime_detection(request: RegimeDetectionRequest):
    """Detect current market regime (Bull/Bear/Sideways)."""
    try:
        result = thinker.think(ThinkingStrategy.REGIME_DETECTION, request.dict())
        return ThinkingResponse(
            strategy="regime_detection",
            result={
                "regime": result["regime"],
                "volatility": result["volatility"],
                "recommendation": result["recommendation"]
            },
            trace=result["trace"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/portfolio-rebalance", response_model=ThinkingResponse)
async def portfolio_rebalance(request: PortfolioRebalanceRequest):
    """Analyze portfolio drift and recommend rebalancing trades."""
    try:
        result = thinker.think(ThinkingStrategy.PORTFOLIO_REBALANCE, request.dict())
        return ThinkingResponse(
            strategy="portfolio_rebalance",
            result={"actions": result.get("actions", [])},
            trace=result["trace"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/earnings-play", response_model=ThinkingResponse)
async def earnings_play(request: EarningsPlayRequest):
    """Analyze earnings event for options strategy."""
    try:
        result = thinker.think(ThinkingStrategy.EARNINGS_PLAY, request.dict())
        return ThinkingResponse(
            strategy="earnings_play",
            result={
                "recommended_strategy": result["recommended_strategy"],
                "rationale": result["rationale"]
            },
            trace=result["trace"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Memory Endpoints
# ============================================================================
@app.get("/memory")
async def get_memory():
    """Return the full knowledge graph."""
    return memory.read_graph()

@app.get("/memory/{entity_name}")
async def get_entity_memory(entity_name: str):
    """Get memory for a specific entity."""
    result = memory.get_related(entity_name)
    if not result:
        raise HTTPException(status_code=404, detail=f"Entity {entity_name} not found")
    return result

@app.post("/memory/learn")
async def learn(entity_name: str, observation: str):
    """Add a new observation to an entity's memory."""
    if entity_name not in memory.entities:
        memory.create_entities([{"name": entity_name, "entity_type": "stock", "observations": [observation]}])
    else:
        memory.add_observations(entity_name, [observation])
    return {"status": "learned", "entity": entity_name}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)
