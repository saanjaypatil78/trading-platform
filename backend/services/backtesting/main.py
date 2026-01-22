from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import logging
import sys
import os
from contextlib import asynccontextmanager

# Add parent directories to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from shared.config import settings
from shared.cache import cache
from .models import BacktestConfig, BacktestResult
from .backtest_service import BacktestService
from .timeframe_validator import TimeframeValidator

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global service instance
backtest_service: BacktestService | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management"""
    global backtest_service
    
    logger.info("Starting Backtesting Service...")
    
    # Connect to cache
    await cache.connect()
    
    # Initialize backtest service
    backtest_service = BacktestService()
    
    logger.info("Backtesting Service started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Backtesting Service...")
    await cache.disconnect()
    logger.info("Backtesting Service shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Backtesting Service",
    description="High-performance backtesting engine for trading strategies",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "backtesting"
    }


@app.post("/api/v1/backtest/execute", response_model=BacktestResult)
async def execute_backtest(
    config: BacktestConfig,
    risk_acknowledged: bool = False,
    user_id: str = "anonymous"
):
    """
    Execute a backtest with the specified configuration
    
    - **strategy**: Strategy configuration with indicators and rules
    - **symbols**: List of symbols to backtest (single symbol supported for now)
    - **start_date**: Backtest start date
    - **end_date**: Backtest end date
    - **initial_capital**: Starting capital amount
    - **commission**: Commission rate (default 0.1%)
    - **slippage**: Slippage rate (default 0.05%)
    - **engine**: Engine to use ("vectorbt", "backtrader", "both")
    
    Returns comprehensive backtest results with performance metrics and trade history.
    """
    if not backtest_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        result = await backtest_service.execute_backtest(
            config,
            user_id=user_id,
            risk_acknowledged=risk_acknowledged
        )
        return result
    
    except ValueError as e:
        error_detail = str(e)
        
        # Check if this is a timeframe warning
        if isinstance(e.args[0], dict) and e.args[0].get('type') == 'timeframe_warning':
            # Return structured warning for frontend to display
            raise HTTPException(
                status_code=422,  # Unprocessable Entity
                detail=e.args[0]
            )
        
        raise HTTPException(status_code=400, detail=error_detail)
    
    except Exception as e:
        logger.error(f"Backtest execution failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")


@app.post("/api/v1/backtest/execute-async")
async def execute_backtest_async(
    config: BacktestConfig,
    background_tasks: BackgroundTasks
):
    """
    Execute backtest asynchronously in background
    Returns immediately with backtest ID for status checking
    """
    if not backtest_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    import uuid
    backtest_id = str(uuid.uuid4())
    
    # Add to background tasks
    background_tasks.add_task(
        _execute_backtest_background,
        backtest_id,
        config
    )
    
    return {
        "backtest_id": backtest_id,
        "status": "queued",
        "message": "Backtest queued for execution"
    }


async def _execute_backtest_background(backtest_id: str, config: BacktestConfig):
    """Background task for async backtest execution"""
    try:
        result = await backtest_service.execute_backtest(config)
        
        # Store result in cache
        await cache.set(
            f"backtest:{backtest_id}:result",
            result.json(),
            ttl=86400  # 24 hours
        )
    
    except Exception as e:
        logger.error(f"Background backtest failed: {str(e)}")
        await cache.set(
            f"backtest:{backtest_id}:error",
            str(e),
            ttl=86400
        )


@app.get("/api/v1/backtest/status/{backtest_id}")
async def get_backtest_status(backtest_id: str):
    """Get status of an async backtest"""
    # Check if completed
    result = await cache.get(f"backtest:{backtest_id}:result")
    if result:
        return {
            "backtest_id": backtest_id,
            "status": "completed",
            "result": result
        }
    
    # Check if failed
    error = await cache.get(f"backtest:{backtest_id}:error")
    if error:
        return {
            "backtest_id": backtest_id,
            "status": "failed",
            "error": error
        }
    
    # Check if still running
    context = await cache.get(f"backtest:{backtest_id}:context")
    if context:
        return {
            "backtest_id": backtest_id,
            "status": "running",
            "progress": context.get('processed_bars', 0) / context.get('total_bars', 1) * 100
        }
    
    return {
        "backtest_id": backtest_id,
        "status": "not_found"
    }


@app.get("/api/v1/backtest/templates")
async def get_strategy_templates():
    """Get predefined strategy templates"""
    templates = [
        {
            "id": "rsi_mean_reversion",
            "name": "RSI Mean Reversion",
            "description": "Buy when RSI < 30, sell when RSI > 70",
            "indicators": {
                "RSI": {"period": 14}
            },
            "entry_rules": "RSI(14) < 30",
            "exit_rules": "RSI(14) > 70"
        },
        {
            "id": "sma_crossover",
            "name": "SMA Crossover",
            "description": "Buy when SMA(10) crosses above SMA(30)",
            "indicators": {
                "SMA": {"period": 10},
                "SMA_SLOW": {"period": 30}
            },
            "entry_rules": "SMA(10) > SMA(30)",
            "exit_rules": "SMA(10) < SMA(30)"
        }
    ]
    
    return templates


@app.get("/api/v1/backtest/timeframes")
async def get_timeframe_info():
    """
    Get information about supported timeframes with recommendations
    """
    return {
        "supported_timeframes": [
            "1m", "5m", "15m", "30m", "1h", "2h", "4h", "1d"
        ],
        "recommendations": TimeframeValidator.get_recommended_timeframes(),
        "warnings": {
            "1m": "HIGH-FREQUENCY TRADING - Requires acknowledgment",
            "5m": "SCALPING - Requires acknowledgment"
        }
    }


@app.post("/api/v1/backtest/validate-timeframe")
async def validate_timeframe(interval: str, user_id: str = "anonymous"):
    """
    Validate a timeframe and get warnings if applicable
    
    Returns warning information if timeframe is risky
    """
    is_valid, warning = TimeframeValidator.validate_timeframe(interval)
    
    if warning:
        # Calculate estimated costs for this timeframe
        cost_estimate = TimeframeValidator.calculate_estimated_costs(interval)
        
        return {
            "interval": interval,
            "is_risky": True,
            "warning": warning,
            "cost_estimate": cost_estimate,
            "requires_acknowledgment": True
        }
    
    return {
        "interval": interval,
        "is_risky": False,
        "warning": None,
        "requires_acknowledgment": False
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.API_HOST, port=8004)
