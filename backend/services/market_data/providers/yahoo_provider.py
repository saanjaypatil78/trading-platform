import yfinance as yf
from typing import Optional, List
from datetime import datetime, timedelta
from decimal import Decimal
from .base_provider import BaseProvider
from shared.models import Quote, OHLCV, HistoricalData, CompanyInfo, SearchResult
from shared.config import settings
import logging
import pandas as pd

logger = logging.getLogger(__name__)


class YahooFinanceProvider(BaseProvider):
    """Yahoo Finance data provider (free, no API key required)"""
    
    def __init__(self):
        super().__init__("YahooFinance")
    
    def _get_nse_symbol(self, symbol: str) -> str:
        """Convert symbol to Yahoo Finance NSE format"""
        # Yahoo uses format: SYMBOL.NS for NSE
        if not symbol.endswith(".NS"):
            return f"{symbol}.NS"
        return symbol
    
    async def get_quote(self, symbol: str) -> Optional[Quote]:
        """Get real-time quote from Yahoo Finance"""
        try:
            nse_symbol = self._get_nse_symbol(symbol)
            ticker = yf.Ticker(nse_symbol)
            info = ticker.info
            
            if not info or "regularMarketPrice" not in info:
                return None
            
            current_price = Decimal(str(info.get("regularMarketPrice", 0)))
            previous_close = Decimal(str(info.get("previousClose", 0)))
            change = current_price - previous_close
            change_percent = (change / previous_close * 100) if previous_close else Decimal(0)
            
            quote = Quote(
                symbol=symbol,
                name=info.get("longName") or info.get("shortName"),
                open=Decimal(str(info.get("regularMarketOpen", 0))),
                high=Decimal(str(info.get("dayHigh", 0))),
                low=Decimal(str(info.get("dayLow", 0))),
                close=current_price,
                last_price=current_price,
                previous_close=previous_close,
                change=change,
                change_percent=change_percent,
                volume=int(info.get("regularMarketVolume", 0)),
                timestamp=datetime.now(),
                exchange="NSE"
            )
            
            self.mark_available()
            return quote
            
        except Exception as e:
            logger.error(f"Yahoo Finance exception: {e}")
            self.mark_unavailable(str(e))
            return None
    
    async def get_ohlcv(
        self, 
        symbol: str, 
        interval: str = "1d",
        limit: int = 100
    ) -> Optional[List[OHLCV]]:
        """Get OHLCV data from Yahoo Finance"""
        try:
            nse_symbol = self._get_nse_symbol(symbol)
            ticker = yf.Ticker(nse_symbol)
            
            # Map interval format
            yf_interval = interval.lower() if interval != "D" else "1d"
            
            # Get historical data
            hist = ticker.history(period=f"{limit}d", interval=yf_interval)
            
            if hist.empty:
                return None
            
            ohlcv_list = []
            for index, row in hist.iterrows():
                ohlcv = OHLCV(
                    symbol=symbol,
                    timestamp=index.to_pydatetime(),
                    open=Decimal(str(row["Open"])),
                    high=Decimal(str(row["High"])),
                    low=Decimal(str(row["Low"])),
                    close=Decimal(str(row["Close"])),
                    volume=int(row["Volume"]),
                    interval=interval
                )
                ohlcv_list.append(ohlcv)
            
            return ohlcv_list[-limit:]
            
        except Exception as e:
            logger.error(f"Yahoo Finance OHLCV error: {e}")
            return None
    
    async def get_historical(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d"
    ) -> Optional[HistoricalData]:
        """Get historical data for date range"""
        try:
            nse_symbol = self._get_nse_symbol(symbol)
            ticker = yf.Ticker(nse_symbol)
            
            # Map interval format
            yf_interval = interval.lower() if interval != "D" else "1d"
            
            # Get historical data
            hist = ticker.history(
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                interval=yf_interval
            )
            
            if hist.empty:
                return None
            
            ohlcv_list = []
            for index, row in hist.iterrows():
                ohlcv = OHLCV(
                    symbol=symbol,
                    timestamp=index.to_pydatetime(),
                    open=Decimal(str(row["Open"])),
                    high=Decimal(str(row["High"])),
                    low=Decimal(str(row["Low"])),
                    close=Decimal(str(row["Close"])),
                    volume=int(row["Volume"]),
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
            
        except Exception as e:
            logger.error(f"Yahoo Finance historical error: {e}")
            return None
    
    async def search_symbols(self, query: str) -> Optional[List[SearchResult]]:
        """Search for symbols (limited functionality in yfinance)"""
        # Yahoo Finance doesn't have built-in search
        # This is a placeholder - you might want to use a separate search service
        logger.warning("Yahoo Finance search not fully implemented")
        return None
    
    async def get_company_info(self, symbol: str) -> Optional[CompanyInfo]:
        """Get company information"""
        try:
            nse_symbol = self._get_nse_symbol(symbol)
            ticker = yf.Ticker(nse_symbol)
            info = ticker.info
            
            if not info:
                return None
            
            company_info = CompanyInfo(
                symbol=symbol,
                name=info.get("longName", ""),
                sector=info.get("sector"),
                industry=info.get("industry"),
                market_cap=Decimal(str(info.get("marketCap", 0))) if info.get("marketCap") else None,
                pe_ratio=Decimal(str(info.get("trailingPE", 0))) if info.get("trailingPE") else None,
                dividend_yield=Decimal(str(info.get("dividendYield", 0) * 100)) if info.get("dividendYield") else None,
                fifty_two_week_high=Decimal(str(info.get("fiftyTwoWeekHigh", 0))) if info.get("fiftyTwoWeekHigh") else None,
                fifty_two_week_low=Decimal(str(info.get("fiftyTwoWeekLow", 0))) if info.get("fiftyTwoWeekLow") else None,
                description=info.get("longBusinessSummary"),
                website=info.get("website")
            )
            
            return company_info
            
        except Exception as e:
            logger.error(f"Yahoo Finance company info error: {e}")
            return None
    
    async def health_check(self) -> bool:
        """Check provider health"""
        try:
            # Try to get a quote for a known NSE stock
            ticker = yf.Ticker("RELIANCE.NS")
            info = ticker.info
            return "regularMarketPrice" in info
        except:
            return False
