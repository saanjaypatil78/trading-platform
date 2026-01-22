import httpx
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from .base_provider import BaseProvider
from shared.models import Quote, OHLCV, HistoricalData, CompanyInfo, SearchResult
from shared.config import settings
import logging

logger = logging.getLogger(__name__)


class FinnhubProvider(BaseProvider):
    """Finnhub market data provider"""
    
    def __init__(self):
        super().__init__("Finnhub")
        self.api_key = settings.FINNHUB_API_KEY
        self.base_url = "https://finnhub.io/api/v1"
    
    def _get_nse_symbol(self, symbol: str) -> str:
        """Convert symbol to NSE format for Finnhub"""
        # Finnhub uses format: SYMBOL.NS for NSE
        if not symbol.endswith(".NS"):
            return f"{symbol}.NS"
        return symbol
    
    async def get_quote(self, symbol: str) -> Optional[Quote]:
        """Get real-time quote from Finnhub"""
        if not self.api_key:
            logger.warning("Finnhub API key not configured")
            return None
        
        try:
            nse_symbol = self._get_nse_symbol(symbol)
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/quote",
                    params={"symbol": nse_symbol, "token": self.api_key}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("c") == 0:  # No data available
                        return None
                    
                    current_price = Decimal(str(data.get("c", 0)))
                    previous_close = Decimal(str(data.get("pc", 0)))
                    change = current_price - previous_close
                    change_percent = (change / previous_close * 100) if previous_close else Decimal(0)
                    
                    quote = Quote(
                        symbol=symbol,
                        name=None,  # Finnhub doesn't return name in quote
                        open=Decimal(str(data.get("o", 0))),
                        high=Decimal(str(data.get("h", 0))),
                        low=Decimal(str(data.get("l", 0))),
                        close=current_price,
                        last_price=current_price,
                        previous_close=previous_close,
                        change=change,
                        change_percent=change_percent,
                        volume=None,  # Not in real-time quote
                        timestamp=datetime.fromtimestamp(data.get("t", datetime.now().timestamp())),
                        exchange="NSE"
                    )
                    
                    self.mark_available()
                    return quote
                elif response.status_code == 429:
                    logger.warning("Finnhub rate limit exceeded")
                    self.mark_unavailable("Rate limit exceeded")
                    return None
                else:
                    logger.error(f"Finnhub error: {response.status_code}")
                    self.mark_unavailable(f"HTTP {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Finnhub exception: {e}")
            self.mark_unavailable(str(e))
            return None
    
    async def get_ohlcv(
        self, 
        symbol: str, 
        interval: str = "D",
        limit: int = 100
    ) -> Optional[List[OHLCV]]:
        """Get OHLCV candles from Finnhub"""
        if not self.api_key:
            return None
        
        try:
            nse_symbol = self._get_nse_symbol(symbol)
            
            # Calculate time range
            end_time = int(datetime.now().timestamp())
            days = limit if interval == "D" else limit // 390  # ~390 mins per trading day
            start_time = end_time - (days * 86400)
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{self.base_url}/stock/candle",
                    params={
                        "symbol": nse_symbol,
                        "resolution": interval,
                        "from": start_time,
                        "to": end_time,
                        "token": self.api_key
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("s") == "no_data":
                        return None
                    
                    ohlcv_list = []
                    timestamps = data.get("t", [])
                    opens = data.get("o", [])
                    highs = data.get("h", [])
                    lows = data.get("l", [])
                    closes = data.get("c", [])
                    volumes = data.get("v", [])
                    
                    for i in range(len(timestamps)):
                        ohlcv = OHLCV(
                            symbol=symbol,
                            timestamp=datetime.fromtimestamp(timestamps[i]),
                            open=Decimal(str(opens[i])),
                            high=Decimal(str(highs[i])),
                            low=Decimal(str(lows[i])),
                            close=Decimal(str(closes[i])),
                            volume=int(volumes[i]),
                            interval=interval
                        )
                        ohlcv_list.append(ohlcv)
                    
                    return ohlcv_list[-limit:]  # Return last N candles
                else:
                    return None
                    
        except Exception as e:
            logger.error(f"Finnhub OHLCV error: {e}")
            return None
    
    async def get_historical(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "D"
    ) -> Optional[HistoricalData]:
        """Get historical data for date range"""
        if not self.api_key:
            return None
        
        try:
            nse_symbol = self._get_nse_symbol(symbol)
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{self.base_url}/stock/candle",
                    params={
                        "symbol": nse_symbol,
                        "resolution": interval,
                        "from": int(start_date.timestamp()),
                        "to": int(end_date.timestamp()),
                        "token": self.api_key
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("s") == "no_data":
                        return None
                    
                    ohlcv_list = []
                    timestamps = data.get("t", [])
                    opens = data.get("o", [])
                    highs = data.get("h", [])
                    lows = data.get("l", [])
                    closes = data.get("c", [])
                    volumes = data.get("v", [])
                    
                    for i in range(len(timestamps)):
                        ohlcv = OHLCV(
                            symbol=symbol,
                            timestamp=datetime.fromtimestamp(timestamps[i]),
                            open=Decimal(str(opens[i])),
                            high=Decimal(str(highs[i])),
                            low=Decimal(str(lows[i])),
                            close=Decimal(str(closes[i])),
                            volume=int(volumes[i]),
                            interval=interval
                        )
                        ohlcv_list.append(ohlcv)
                    
                    return HistoricalData(
                        symbol=symbol,
                        interval=interval,
                        data=ohlcv_list,
                        start_date=start_date,
                        end_date=end_date
                    )
                else:
                    return None
                    
        except Exception as e:
            logger.error(f"Finnhub historical error: {e}")
            return None
    
    async def search_symbols(self, query: str) -> Optional[List[SearchResult]]:
        """Search for symbols"""
        if not self.api_key:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/search",
                    params={"q": query, "token": self.api_key}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results = []
                    
                    # Filter for NSE stocks only
                    for item in data.get("result", []):
                        if ".NS" in item.get("symbol", ""):
                            result = SearchResult(
                                symbol=item["symbol"].replace(".NS", ""),
                                name=item.get("description", ""),
                                exchange="NSE",
                                type=item.get("type", "stock")
                            )
                            results.append(result)
                    
                    return results
                else:
                    return None
                    
        except Exception as e:
            logger.error(f"Finnhub search error: {e}")
            return None
    
    async def get_company_info(self, symbol: str) -> Optional[CompanyInfo]:
        """Get company profile from Finnhub"""
        if not self.api_key:
            return None
        
        try:
            nse_symbol = self._get_nse_symbol(symbol)
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/stock/profile2",
                    params={"symbol": nse_symbol, "token": self.api_key}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if not data:
                        return None
                    
                    info = CompanyInfo(
                        symbol=symbol,
                        name=data.get("name", ""),
                        sector=data.get("finnhubIndustry"),
                        industry=data.get("finnhubIndustry"),
                        market_cap=Decimal(str(data.get("marketCapitalization", 0) * 1000000)) if data.get("marketCapitalization") else None,
                        pe_ratio=None,  # Not in profile2
                        dividend_yield=None,
                        fifty_two_week_high=None,
                        fifty_two_week_low=None,
                        description=data.get("description"),
                        website=data.get("weburl")
                    )
                    
                    return info
                else:
                    return None
                    
        except Exception as e:
            logger.error(f"Finnhub company info error: {e}")
            return None
    
    async def health_check(self) -> bool:
        """Check provider health"""
        if not self.api_key:
            return False
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.base_url}/quote",
                    params={"symbol": "AAPL", "token": self.api_key}
                )
                return response.status_code == 200
        except:
            return False
