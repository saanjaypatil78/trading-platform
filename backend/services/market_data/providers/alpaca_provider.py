
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from .base_provider import BaseProvider
from shared.models import Quote, OHLCV, HistoricalData, CompanyInfo, SearchResult

logger = logging.getLogger(__name__)

class AlpacaProvider(BaseProvider):
    """
    Alpaca Market Data Provider (v2).
    """
    
    def __init__(self, api_key: str, api_secret: str, base_url: str = "https://paper-api.alpaca.markets"):
        self.name = "alpaca"
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        
        # We will lazy-load the client to avoid import errors if SDK not present
        self.client = None 

    async def _get_client(self):
        if not self.client:
            try:
                from alpaca.data.historical import StockHistoricalDataClient
                from alpaca.data.requests import StockBarsRequest
                from alpaca.data.timeframe import TimeFrame
                self.client = StockHistoricalDataClient(self.api_key, self.api_secret)
                self.TimeFrame = TimeFrame
                self.StockBarsRequest = StockBarsRequest
            except ImportError:
                logger.error("alpaca-py not installed. Install with `pip install alpaca-py`")
                raise

        return self.client

    async def get_quote(self, symbol: str) -> Optional[Quote]:
        # Implementation for real-time quote
        # Using Snapshot API usually
        return None  # Placeholder for now

    async def get_ohlcv(self, symbol: str, interval: str = "1d", limit: int = 100) -> Optional[List[OHLCV]]:
        client = await self._get_client()
        try:
            # Map interval to TimeFrame
            tf = self.TimeFrame.Day
            if interval == "1h": tf = self.TimeFrame.Hour
            elif interval == "1m": tf = self.TimeFrame.Minute
            
            request_params = self.StockBarsRequest(
                symbol_or_symbols=[symbol],
                timeframe=tf,
                limit=limit
            )
            
            bars = client.get_stock_bars(request_params)
            data = bars[symbol]
            
            ohlcv_list = []
            for bar in data:
                ohlcv_list.append(OHLCV(
                    symbol=symbol,
                    timestamp=bar.timestamp,
                    open=bar.open,
                    high=bar.high,
                    low=bar.low,
                    close=bar.close,
                    volume=bar.volume
                ))
            return ohlcv_list
            
        except Exception as e:
            logger.error(f"Alpaca OHLCV error: {e}")
            return None

    async def get_historical(self, symbol: str, start_date: datetime, end_date: datetime, interval: str = "1d") -> Optional[HistoricalData]:
        candles = await self.get_ohlcv(symbol, interval, limit=1000) # Simplified limit
        if candles:
            return HistoricalData(symbol=symbol, data=candles, interval=interval)
        return None

    async def health_check(self) -> bool:
        try:
            await self._get_client()
            return True
        except:
            return False

    async def search_symbols(self, query: str) -> Optional[List[SearchResult]]:
        # Placeholder
        return []

    async def get_company_info(self, symbol: str) -> Optional[CompanyInfo]:
        # Placeholder
        return None
