"""
Upstox Market Data Provider
Implementation of BaseProvider for Upstox API.
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import asyncio
from upstox_client import (
    Configuration, 
    ApiClient, 
    HistoryApi, 
    MarketQuoteApi
)
from ratelimit import limits, sleep_and_retry

from shared.models import Quote, OHLCV, HistoricalData, CompanyInfo, SearchResult
from shared.config import settings
from .base_provider import BaseProvider

logger = logging.getLogger(__name__)

# Rate limit constants (free tier/starter assumptions, adjust as needed)
CALLS_PER_SECOND = 1
ONE_SECOND = 1

class UpstoxProvider(BaseProvider):
    """
    Market data provider using Upstox API.
    """
    
    def __init__(self, api_key: str, access_token: Optional[str] = None):
        super().__init__("Upstox")
        self.api_key = api_key
        # Use settings if passed api_key is empty/default
        if not self.api_key or self.api_key == "NOT_SET":
            self.api_key = settings.UPSTOX_API_KEY
            
        self.config = Configuration()
        if access_token:
            self.config.access_token = access_token
        
        self.api_client = ApiClient(self.config)
        self.history_api = HistoryApi(self.api_client)
        self.quote_api = MarketQuoteApi(self.api_client)

    @sleep_and_retry
    @limits(calls=CALLS_PER_SECOND, period=ONE_SECOND)
    def _rate_limited_call(self, func, *args, **kwargs):
        """Helper to wrap API calls with rate limiting only if enabled"""
        if settings.RATELIMIT_ENABLED:
            return func(*args, **kwargs)
        return func(*args, **kwargs)

    async def get_quote(self, symbol: str) -> Optional[Quote]:
        """Fetch latest quote from Upstox."""
        try:
            # Upstox requires instrument_key, e.g., 'NSE_EQ|INE002A01018'
            # For simplicity, we assume symbol is already in correct format or handled by a mapper
            # Use rate limited call
            response = self._rate_limited_call(self.quote_api.get_market_quote_ohlc, symbol, "2.0")
            data = response.data[symbol]
            
            return Quote(
                symbol=symbol,
                price=data.last_price,
                change=data.last_price - data.ohlc.close,
                change_percent=((data.last_price - data.ohlc.close) / data.ohlc.close) * 100 if data.ohlc.close else 0,
                volume=data.volume,
                bid=data.last_price, # Upstox OHLC endpoint might not have bid/ask directly
                ask=data.last_price,
                timestamp=datetime.now(),
                provider=self.name
            )
        except Exception as e:
            logger.error(f"Upstox quote error for {symbol}: {e}")
            return None

    async def get_ohlcv(
        self, 
        symbol: str, 
        interval: str = "1d",
        limit: int = 100
    ) -> Optional[List[OHLCV]]:
        """Fetch historical OHLCV data."""
        try:
            # Map interval to Upstox format: 1minute, 30minute, day, month
            upstox_interval = "day"
            if interval == "1m": upstox_interval = "1minute"
            elif interval == "5m": upstox_interval = "5minute"
            elif interval == "15m": upstox_interval = "15minute"
            elif interval == "30m": upstox_interval = "30minute"
            elif interval == "1h": upstox_interval = "60minute"

            to_date = datetime.now().strftime("%Y-%m-%d")
            # Calculate from_date based on limit/interval
            # Simple approximation: limit * value
            days_lookup = {
                "1minute": 1, "5minute": 5, "15minute": 15, "30minute": 30, "60minute": 60, "day": 1440
            }
            minutes_per_candle = days_lookup.get(upstox_interval, 1440)
            delta_days = (limit * minutes_per_candle) // 1440 + 5 # Buffer
            from_date = (datetime.now() - timedelta(days=delta_days)).strftime("%Y-%m-%d")

            # Get historical candles
            response = self._rate_limited_call(
                self.history_api.get_historical_candle_data1,
                symbol, upstox_interval, to_date, from_date, api_version="2.0"
            )
            
            candles = []
            for c in response.data.candles[:limit]:
                # Upstox candle format: [timestamp, open, high, low, close, volume, oi]
                candles.append(OHLCV(
                    symbol=symbol,
                    timestamp=datetime.fromisoformat(c[0].replace("Z", "+00:00")),
                    open=float(c[1]),
                    high=float(c[2]),
                    low=float(c[3]),
                    close=float(c[4]),
                    volume=int(c[5])
                ))
            
            # Sort by timestamp ascending (oldest first)
            candles.sort(key=lambda x: x.timestamp)
            
            return candles
        except Exception as e:
            logger.error(f"Upstox OHLCV error for {symbol}: {e}")
            return None

    async def get_historical(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d"
    ) -> Optional[HistoricalData]:
        candles = await self.get_ohlcv(symbol, interval, limit=1000)
        if candles:
            return HistoricalData(symbol=symbol, data=candles, interval=interval)
        return None

    async def search_symbols(self, query: str) -> Optional[List[SearchResult]]:
        # Upstox doesn't have a direct search API in the SDK usually, 
        # often requires downloading an instrument CSV.
        # Placeholder for search logic.
        return []

    async def get_company_info(self, symbol: str) -> Optional[CompanyInfo]:
        return None

    async def health_check(self) -> bool:
        try:
            # Simple check with a common symbol
            # Simple check with a common symbol
            self._rate_limited_call(self.quote_api.get_market_quote_ohlc, "NSE_EQ|INE002A01018", "2.0")
            return True
        except:
            return False
