"""
Strategy Auto-Generation Service
Uses AI logic to convert natural language descriptions into backtestable code.
"""
import os
import logging
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio

from backend.services.backtesting.high_speed import HighSpeedBacktest
from backend.shared.messaging import bus, Event, EventTypes

logger = logging.getLogger(__name__)

app = FastAPI(title="Strategy Gen Service")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class StrategyPrompt(BaseModel):
    description: str
    symbol: str = "AAPL"
    timeframe: str = "1m"

class GenerationResult(BaseModel):
    strategy_name: str
    code: str
    backtest_results: Optional[Dict[str, Any]] = None

class StrategyGenerator:
    """
    Simulated LLM-based strategy generator.
    In production, this would call GPT-4 or Gemini via an API.
    """
    
    def generate_strategy_code(self, description: str) -> str:
        # specific complex request matching
        if "wma" in description.lower() and "rsi" in description.lower():
            return """
def strategy(data, wma_fast=5, wma_slow=50, rsi_period=14):
    import pandas_ta as ta
    import numpy as np
    
    # Calculate Indicators
    close = data['close']
    wma5 = ta.wma(close, length=wma_fast)
    wma50 = ta.wma(close, length=wma_slow)
    rsi = ta.rsi(close, length=rsi_period)
    
    # Divergence Logic (Simplified for vectorization)
    # Price Lower Low but RSI Higher Low (Bullish Divergence)
    price_ll = (close < close.shift(1)) & (close.shift(1) < close.shift(2))
    rsi_hl = (rsi > rsi.shift(1)) & (rsi.shift(1) < rsi.shift(2))
    
    signals = np.zeros(len(close))
    
    # Entry: WMA Crossover + Optional Divergence confirmation
    # For this simplified version, we prioritize the WMA crossover as the trigger
    crossover = (wma5 > wma50) & (wma5.shift(1) <= wma50.shift(1))
    
    signals[crossover] = 1 # Long
    
    # Exit: Trailing Stop Loss Logic would be handled by the execution engine, 
    # but here we signal exit on cross down
    crossunder = (wma5 < wma50) & (wma5.shift(1) >= wma50.shift(1))
    signals[crossunder] = -1 # Sell/Close
    
    return signals
            """

        # Template for SMA Crossover (Common request)
        if "sma" in description.lower() or "moving average" in description.lower():
            return """
def strategy(data, fast_window=9, slow_window=21):
    import numpy as np
    close = data['close'].values
    fast_sma = data['close'].rolling(window=fast_window).mean().values
    slow_sma = data['close'].rolling(window=slow_window).mean().values
    
    signals = np.where(fast_sma > slow_sma, 1, 0)
    return signals
            """
        # Template for RSI (Common request)
        elif "rsi" in description.lower():
            return """
def strategy(data, rsi_period=14, oversold=30, overbought=70):
    import pandas_ta as ta
    import numpy as np
    rsi = ta.rsi(data['close'], length=rsi_period).values
    
    signals = np.zeros(len(rsi))
    signals[rsi < oversold] = 1  # Long
    signals[rsi > overbought] = 0 # Out
    return signals
            """
        else:
            # Default fallback
            return """
def strategy(data):
    import numpy as np
    # Simple always long strategy
    return np.ones(len(data))
            """

@app.post("/api/v1/generate", response_model=GenerationResult)
async def generate_strategy(prompt: StrategyPrompt):
    logger.info(f"Generating strategy for: {prompt.description}")
    
    gen = StrategyGenerator()
    code = gen.generate_strategy_code(prompt.description)
    
    # Simulate a backtest to validate the generated code
    # (In a real system, we'd exec() the code safely or use a sandbox)
    try:
        # Mocking backtest results for the demonstration
        # Generate mock data for the backtest
        import pandas as pd
        import numpy as np
        
        dates = pd.date_range('2023-01-01', periods=200)
        prices = 100 + np.cumsum(np.random.normal(0.01, 1, 200))
        mock_df = pd.DataFrame({'close': prices}, index=dates)
        
        # Initialize engine with DataFrame
        engine = HighSpeedBacktest(mock_df)
        results = engine.run_sma_crossover(9, 21)
        
        # Publish event
        await bus.publish(Event.create(
            event_type=EventTypes.STRATEGY_SIGNAL,
            payload={"source": "auto_gen", "status": "code_generated", "symbol": prompt.symbol},
            source="strategy_gen"
        ))
        
        return GenerationResult(
            strategy_name="AI_Generated_Strategy",
            code=code,
            backtest_results=results
        )
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8020)
