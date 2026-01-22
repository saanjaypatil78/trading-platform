from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from shared.config import settings
from shared.cache import cache
from shared.models import Quote, OHLCV, HistoricalData, CompanyInfo, SearchResult, ProviderHealth
from .aggregator import aggregator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    logger.info("Starting Market Data Service...")
    await cache.connect()
    logger.info("Connected to Redis cache")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Market Data Service...")
    await cache.disconnect()
    logger.info("Disconnected from Redis cache")


# Create FastAPI app
app = FastAPI(
    title="Market Data Service",
    description="Multi-provider market data aggregation with failover",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Service health check"""
    return {"status": "healthy", "service": "market-data"}


@app.get("/api/v1/providers/health", response_model=List[ProviderHealth])
async def get_providers_health():
    """Get health status of all data providers"""
    return await aggregator.get_provider_health()


@app.get("/api/v1/quote/{symbol}", response_model=Quote)
async def get_quote(
    symbol: str,
    use_cache: bool = Query(True, description="Use cached data if available")
):
    """
    Get real-time quote for a symbol
    
    - **symbol**: Stock symbol (e.g., RELIANCE, TCS, INFY)
    - **use_cache**: Whether to use cached data (default: true)
    """
    quote = await aggregator.get_quote(symbol, use_cache=use_cache)
    
    if not quote:
        raise HTTPException(status_code=404, detail=f"Quote not found for symbol: {symbol}")
    
    return quote


@app.get("/api/v1/quotes", response_model=dict[str, Optional[Quote]])
async def get_bulk_quotes(
    symbols: List[str] = Query(..., description="List of symbols")
):
    """Get quotes for multiple symbols"""
    return await aggregator.get_bulk_quotes(symbols)


@app.get("/api/v1/ohlcv/{symbol}", response_model=List[OHLCV])
async def get_ohlcv(
    symbol: str,
    interval: str = Query("1d", description="Interval: 1m, 5m, 15m, 1h, 1d"),
    limit: int = Query(100, ge=1, le=1000, description="Number of candles"),
    use_cache: bool = Query(True)
):
    """
    Get OHLCV candle data
    
    - **symbol**: Stock symbol
    - **interval**: Candle interval (1m, 5m, 15m, 1h, 1d)
    - **limit**: Number of candles to fetch (max 1000)
    """
    ohlcv = await aggregator.get_ohlcv(symbol, interval, limit, use_cache)
    
    if not ohlcv:
        raise HTTPException(status_code=404, detail=f"OHLCV data not found for {symbol}")
    
    return ohlcv


@app.get("/api/v1/historical/{symbol}", response_model=HistoricalData)
async def get_historical(
    symbol: str,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    interval: str = Query("1d", description="Interval"),
    use_cache: bool = Query(True)
):
    """
    Get historical data for a date range
    
    - **symbol**: Stock symbol
    - **start_date**: Start date (default: 1 year ago)
    - **end_date**: End date (default: today)
    - **interval**: Data interval (1d, 1w, 1m)
    """
    # Parse dates
    if not end_date:
        end = datetime.now()
    else:
        end = datetime.strptime(end_date, "%Y-%m-%d")
    
    if not start_date:
        start = end - timedelta(days=365)
    else:
        start = datetime.strptime(start_date, "%Y-%m-%d")
    
    historical = await aggregator.get_historical(symbol, start, end, interval, use_cache)
    
    if not historical:
        raise HTTPException(status_code=404, detail=f"Historical data not found for {symbol}")
    
    return historical


@app.get("/api/v1/search", response_model=List[SearchResult])
async def search_symbols(
    q: str = Query(..., min_length=1, description="Search query")
):
    """
    Search for stock symbols
    
    - **q**: Search query (company name or symbol)
    """
    results = await aggregator.search_symbols(q)
    
    if not results:
        return []
    
    return results


@app.get("/api/v1/company/{symbol}", response_model=CompanyInfo)
async def get_company_info(
    symbol: str,
    use_cache: bool = Query(True)
):
    """
    Get company fundamental information
    
    - **symbol**: Stock symbol
    """
    info = await aggregator.get_company_info(symbol, use_cache)
    
    if not info:
        raise HTTPException(status_code=404, detail=f"Company info not found for {symbol}")
    
    return info


@app.delete("/api/v1/cache/{symbol}")
async def clear_cache_for_symbol(symbol: str):
    """Clear all cached data for a symbol"""
    cache_keys = [
        f"quote:{symbol}",
        f"company:{symbol}",
    ]
    
    for key in cache_keys:
        await cache.delete(key)
    
    return {"message": f"Cache cleared for {symbol}"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.API_HOST, port=settings.API_PORT)
