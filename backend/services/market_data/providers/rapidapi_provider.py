import httpx
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from .base_provider import BaseProvider
from shared.models import Quote, OHLCV, HistoricalData, CompanyInfo, SearchResult
from shared.config import settings
import logging

logger = logging.getLogger(__name__)


class RapidAPIProvider(BaseProvider):
    """RapidAPI Indian Stock Exchange data provider"""
    
    def __init__(self):
        super().__init__("RapidAPI")
        self.api_key = settings.RAPIDAPI_KEY
        self.api_host = settings.RAPIDAPI_HOST
        self.base_url = f"https://{self.api_host}"
        self.headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": self.api_host
        }
    
    async def get_quote(self, symbol: str) -> Optional[Quote]:
        """Get real-time quote from RapidAPI"""
        if not self.api_key:
            logger.warning("RapidAPI key not configured")
            return None
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Example endpoint - adjust based on actual RapidAPI structure
                response = await client.get(
                    f"{self.base_url}/quote/{symbol}",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Parse response to Quote model
                    quote = Quote(
                        symbol=symbol,
                        name=data.get("name"),
                        open=Decimal(str(data.get("open", 0))),
                        high=Decimal(str(data.get("high", 0))),
                        low=Decimal(str(data.get("low", 0))),
                        close=Decimal(str(data.get("close", 0))),
                        last_price=Decimal(str(data.get("lastPrice", 0))),
                        previous_close=Decimal(str(data.get("previousClose", 0))),
                        change=Decimal(str(data.get("change", 0))),
                        change_percent=Decimal(str(data.get("pChange", 0))),
                        volume=int(data.get("totalTradedVolume", 0)),
                        timestamp=datetime.now(),
                        exchange=data.get("exchange", "NSE")
                    )
                    
                    self.mark_available()
                    return quote
                else:
                    logger.error(f"RapidAPI error: {response.status_code}")
                    self.mark_unavailable(f"HTTP {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"RapidAPI exception: {e}")
            self.mark_unavailable(str(e))
            return None
    
    async def get_ohlcv(
        self, 
        symbol: str, 
        interval: str = "1d",
        limit: int = 100
    ) -> Optional[List[OHLCV]]:
        """Get OHLCV data from RapidAPI"""
        if not self.api_key:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{self.base_url}/historical/{symbol}",
                    headers=self.headers,
                    params={"interval": interval, "limit": limit}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    ohlcv_list = []
                    
                    for item in data.get("data", []):
                        ohlcv = OHLCV(
                            symbol=symbol,
                            timestamp=datetime.fromisoformat(item["timestamp"]),
                            open=Decimal(str(item["open"])),
                            high=Decimal(str(item["high"])),
                            low=Decimal(str(item["low"])),
                            close=Decimal(str(item["close"])),
                            volume=int(item["volume"]),
                            interval=interval
                        )
                        ohlcv_list.append(ohlcv)
                    
                    return ohlcv_list
                else:
                    return None
                    
        except Exception as e:
            logger.error(f"RapidAPI OHLCV error: {e}")
            return None
    
    async def get_historical(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d"
    ) -> Optional[HistoricalData]:
        """Get historical data for date range"""
        # Implementation similar to get_ohlcv but with date filtering
        ohlcv_data = await self.get_ohlcv(symbol, interval, limit=1000)
        
        if not ohlcv_data:
            return None
        
        # Filter by date range
        filtered = [
            candle for candle in ohlcv_data
            if start_date <= candle.timestamp <= end_date
        ]
        
        return HistoricalData(
            symbol=symbol,
            interval=interval,
            data=filtered,
            start_date=start_date,
            end_date=end_date
        )
    
    async def search_symbols(self, query: str) -> Optional[List[SearchResult]]:
        """Search for symbols"""
        if not self.api_key:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/search",
                    headers=self.headers,
                    params={"q": query}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results = []
                    
                    for item in data.get("results", []):
                        result = SearchResult(
                            symbol=item["symbol"],
                            name=item["name"],
                            exchange=item.get("exchange", "NSE"),
                            type=item.get("type", "stock")
                        )
                        results.append(result)
                    
                    return results
                else:
                    return None
                    
        except Exception as e:
            logger.error(f"RapidAPI search error: {e}")
            return None
    
    async def get_company_info(self, symbol: str) -> Optional[CompanyInfo]:
        """Get company information"""
        if not self.api_key:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/company/{symbol}",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    info = CompanyInfo(
                        symbol=symbol,
                        name=data.get("name", ""),
                        sector=data.get("sector"),
                        industry=data.get("industry"),
                        market_cap=Decimal(str(data.get("marketCap", 0))),
                        pe_ratio=Decimal(str(data.get("peRatio", 0))) if data.get("peRatio") else None,
                        dividend_yield=Decimal(str(data.get("dividendYield", 0))) if data.get("dividendYield") else None,
                        fifty_two_week_high=Decimal(str(data.get("52WeekHigh", 0))) if data.get("52WeekHigh") else None,
                        fifty_two_week_low=Decimal(str(data.get("52WeekLow", 0))) if data.get("52WeekLow") else None,
                        description=data.get("description"),
                        website=data.get("website")
                    )
                    
                    return info
                else:
                    return None
                    
        except Exception as e:
            logger.error(f"RapidAPI company info error: {e}")
            return None
    
    async def health_check(self) -> bool:
        """Check provider health"""
        if not self.api_key:
            return False
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.base_url}/health",
                    headers=self.headers
                )
                return response.status_code == 200
        except:
            return False
