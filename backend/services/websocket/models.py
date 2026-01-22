from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime
from decimal import Decimal


class WSMessage(BaseModel):
    """Base WebSocket message model"""
    type: str
    timestamp: datetime = datetime.now()


class SubscribeMessage(BaseModel):
    """Client subscription request"""
    action: Literal["subscribe"]
    symbol: str


class UnsubscribeMessage(BaseModel):
    """Client unsubscribe request"""
    action: Literal["unsubscribe"]
    symbol: str


class QuoteUpdate(WSMessage):
    """Real-time quote update"""
    type: Literal["quote"] = "quote"
    symbol: str
    last_price: Decimal
    change: Optional[Decimal] = None
    change_percent: Optional[Decimal] = None
    volume: Optional[int] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None


class OHLCUpdate(WSMessage):
    """OHLCV candle update"""
    type: Literal["ohlc"] = "ohlc"
    symbol: str
    interval: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


class ScanAlert(WSMessage):
    """Scanner alert notification"""
    type: Literal["scan_alert"] = "scan_alert"
    scan_id: str
    scan_name: str
    matched_symbols: list[str]
    total_matched: int


class SystemMessage(WSMessage):
    """System notification"""
    type: Literal["system"] = "system"
    level: Literal["info", "warning", "error"]
    message: str


class HeartbeatMessage(WSMessage):
    """Heartbeat/ping message"""
    type: Literal["heartbeat"] = "heartbeat"


class ErrorMessage(WSMessage):
    """Error message"""
    type: Literal["error"] = "error"
    error_code: str
    error_message: str
