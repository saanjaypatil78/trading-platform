from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal


class Quote(BaseModel):
    """Real-time stock quote"""
    symbol: str
    name: Optional[str] = None
    open: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    close: Optional[Decimal] = None
    last_price: Decimal
    previous_close: Optional[Decimal] = None
    change: Optional[Decimal] = None
    change_percent: Optional[Decimal] = None
    volume: Optional[int] = None
    timestamp: datetime
    exchange: Optional[str] = None


class OHLCV(BaseModel):
    """OHLCV candle data"""
    symbol: str
    timestamp: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    interval: str = "1d"  # 1m, 5m, 15m, 1h, 1d, 1w, 1M


class HistoricalData(BaseModel):
    """Historical price data response"""
    symbol: str
    interval: str
    data: List[OHLCV]
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class CompanyInfo(BaseModel):
    """Company fundamental information"""
    symbol: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[Decimal] = None
    pe_ratio: Optional[Decimal] = None
    dividend_yield: Optional[Decimal] = None
    fifty_two_week_high: Optional[Decimal] = None
    fifty_two_week_low: Optional[Decimal] = None
    description: Optional[str] = None
    website: Optional[str] = None


class SearchResult(BaseModel):
    """Symbol search result"""
    symbol: str
    name: str
    exchange: str
    type: str = "stock"  # stock, etf, index


class MarketStatus(BaseModel):
    """Market status information"""
    exchange: str
    is_open: bool
    next_open: Optional[datetime] = None
    next_close: Optional[datetime] = None


class ProviderHealth(BaseModel):
    """Health status of data provider"""
    provider: str
    is_available: bool
    response_time_ms: Optional[float] = None
    rate_limit_remaining: Optional[int] = None
    last_error: Optional[str] = None
    last_check: datetime
