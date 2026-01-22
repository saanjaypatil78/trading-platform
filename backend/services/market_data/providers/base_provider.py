from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import datetime
from shared.models import Quote, OHLCV, HistoricalData, CompanyInfo, SearchResult


class BaseProvider(ABC):
    """Abstract base class for market data providers"""
    
    def __init__(self, name: str):
        self.name = name
        self.is_available = True
        self.last_error: Optional[str] = None
        self.rate_limit_remaining: Optional[int] = None
    
    @abstractmethod
    async def get_quote(self, symbol: str) -> Optional[Quote]:
        """Get real-time quote for a symbol"""
        pass
    
    @abstractmethod
    async def get_ohlcv(
        self, 
        symbol: str, 
        interval: str = "1d",
        limit: int = 100
    ) -> Optional[List[OHLCV]]:
        """Get OHLCV data for a symbol"""
        pass
    
    @abstractmethod
    async def get_historical(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d"
    ) -> Optional[HistoricalData]:
        """Get historical data for a date range"""
        pass
    
    @abstractmethod
    async def search_symbols(self, query: str) -> Optional[List[SearchResult]]:
        """Search for symbols"""
        pass
    
    @abstractmethod
    async def get_company_info(self, symbol: str) -> Optional[CompanyInfo]:
        """Get company fundamental information"""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is available"""
        pass
    
    def mark_unavailable(self, error: str):
        """Mark provider as unavailable"""
        self.is_available = False
        self.last_error = error
    
    def mark_available(self):
        """Mark provider as available"""
        self.is_available = True
        self.last_error = None
