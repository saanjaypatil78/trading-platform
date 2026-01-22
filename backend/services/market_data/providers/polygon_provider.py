"""
Polygon.io Market Data Provider
Implementation of BaseProvider for Polygon.io institutional data.
"""
import logging
from typing import Optional, List
from datetime import datetime
from polygon import RESTClient

from shared.models import Quote, OHLCV, HistoricalData, CompanyInfo, SearchResult
from .base_provider import BaseProvider
from shared.config import settings

logger = logging.getLogger(__name__)

class PolygonProvider(BaseProvider):
    def __init__(self, api_key: str):
        super().__init__("Polygon.io")
        self.client = RESTClient(api_key=api_key)

    async def get_quote(self, symbol: str) -> Optional[Quote]:
        try:
            res = self.client.get_last_quote(symbol)
            return Quote(
                symbol=symbol,
                price=(res.ask_price + res.bid_price) / 2,
                change=0, # Need daily agg for change
                change_percent=0,
                volume=0,
                bid=res.bid_price,
                ask=res.ask_price,
                timestamp=datetime.fromtimestamp(res.participant_timestamp / 1e9),
                provider=self.name
            )
        except Exception as e:
            logger.error(f"Polygon error for {symbol}: {e}")
            return None

    async def get_ohlcv(
        self, 
        symbol: str, 
        interval: str = "1d",
        limit: int = 100
    ) -> Optional[List[OHLCV]]:
        try:
            # Map interval to multiplier/timespan
            multiplier = 1
            timespan = "day"
            if interval.endswith("m"):
                multiplier = int(interval[:-1])
                timespan = "minute"
            elif interval.endswith("h"):
                multiplier = int(interval[:-1])
                timespan = "hour"
            
            # polygon client get_aggs handles this
            aggs = self.client.get_aggs(
                ticker=symbol,
                multiplier=multiplier,
                timespan=timespan,
                from_="2000-01-01", # polygon client handles pagination
                to="2100-01-01",
                limit=limit
            )
            
            candles = []
            for a in aggs:
                candles.append(OHLCV(
                    timestamp=datetime.fromtimestamp(a.timestamp / 1000),
                    open=a.open,
                    high=a.high,
                    low=a.low,
                    close=a.close,
                    volume=a.volume
                ))
            return candles
        except Exception as e:
            logger.error(f"Polygon OHLCV error for {symbol}: {e}")
            return None

    async def get_historical(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d"
    ) -> Optional[HistoricalData]:
        candles = await self.get_ohlcv(symbol, interval, limit=1000) # Simplified
        if candles:
            return HistoricalData(symbol=symbol, data=candles)
        return None

    async def search_symbols(self, query: str) -> Optional[List[SearchResult]]:
        try:
            res = self.client.list_tickers(search=query, limit=10)
            results = []
            for t in res:
                results.append(SearchResult(
                    symbol=t.ticker,
                    name=t.name,
                    exchange=t.primary_exchange,
                    type="stock"
                ))
            return results
        except Exception as e:
            logger.error(f"Polygon search error: {e}")
            return None

    async def get_company_info(self, symbol: str) -> Optional[CompanyInfo]:
        try:
            details = self.client.get_ticker_details(symbol)
            return CompanyInfo(
                symbol=symbol,
                name=details.name,
                description=details.description,
                industry=details.sic_description,
                sector=None,
                website=details.homepage_url,
                market_cap=details.market_cap
            )
        except Exception as e:
            logger.error(f"Polygon company info error: {e}")
            return None

    async def health_check(self) -> bool:
        try:
            # Simple check
            self.client.get_last_quote("AAPL")
            return True
        except:
            return False
