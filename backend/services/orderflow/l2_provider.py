"""
L2 Market Data Providers

WebSocket clients for Level 2 orderbook and trade data:
- Alpaca Markets (stocks/crypto) per https://docs.alpaca.markets
- Massive (stocks) per https://massive.com/docs/websocket
"""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import List, Callable, Optional
from datetime import datetime

import websockets

from .l2_models import (
    OrderBookSnapshot, OrderBookLevel, OrderBookDelta,
    TradeExecution, Side
)

logger = logging.getLogger(__name__)


class L2DataProvider(ABC):
    """Abstract base class for L2 data providers"""
    
    def __init__(self):
        self._is_connected = False
        self._subscriptions: List[str] = []
        self._orderbook_callbacks: List[Callable] = []
        self._trade_callbacks: List[Callable] = []
    
    @property
    def is_connected(self) -> bool:
        return self._is_connected
    
    def on_orderbook(self, callback: Callable):
        """Register callback for orderbook updates"""
        self._orderbook_callbacks.append(callback)
    
    def on_trade(self, callback: Callable):
        """Register callback for trade executions"""
        self._trade_callbacks.append(callback)
    
    async def _emit_orderbook(self, snapshot: OrderBookSnapshot):
        """Emit orderbook to all callbacks"""
        for cb in self._orderbook_callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(snapshot)
                else:
                    cb(snapshot)
            except Exception as e:
                logger.error(f"Orderbook callback error: {e}")
    
    async def _emit_trade(self, trade: TradeExecution):
        """Emit trade to all callbacks"""
        for cb in self._trade_callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(trade)
                else:
                    cb(trade)
            except Exception as e:
                logger.error(f"Trade callback error: {e}")
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the data provider"""
        pass
    
    @abstractmethod
    async def disconnect(self):
        """Close connection"""
        pass
    
    @abstractmethod
    async def subscribe(self, symbol: str) -> bool:
        """Subscribe to L2 updates for a symbol"""
        pass
    
    @abstractmethod
    async def unsubscribe(self, symbol: str):
        """Unsubscribe from symbol"""
        pass


class AlpacaL2Provider(L2DataProvider):
    """
    Alpaca Markets L2 Data Provider
    
    Supports:
    - Stock quotes and trades via wss://stream.data.alpaca.markets/v2/sip (paid)
    - Stock quotes via wss://stream.data.alpaca.markets/v2/iex (free)
    - Crypto via wss://stream.data.alpaca.markets/v1beta3/crypto/us
    
    Authentication: API key + secret in auth message
    Docs: https://docs.alpaca.markets/docs/getting-started
    """
    
    # WebSocket endpoints
    STOCK_SIP_URL = "wss://stream.data.alpaca.markets/v2/sip"
    STOCK_IEX_URL = "wss://stream.data.alpaca.markets/v2/iex"
    CRYPTO_URL = "wss://stream.data.alpaca.markets/v1beta3/crypto/us"
    
    # Paper trading endpoints
    STOCK_SIP_PAPER = "wss://stream.data.sandbox.alpaca.markets/v2/sip"
    STOCK_IEX_PAPER = "wss://stream.data.sandbox.alpaca.markets/v2/iex"
    
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        paper: bool = True,
        use_sip: bool = False,  # SIP requires paid subscription
        asset_class: str = "stock"  # "stock" or "crypto"
    ):
        super().__init__()
        self.api_key = api_key
        self.api_secret = api_secret
        self.paper = paper
        self.use_sip = use_sip
        self.asset_class = asset_class
        
        self._ws = None
        self._listen_task: Optional[asyncio.Task] = None
        
        # Select appropriate endpoint
        if asset_class == "crypto":
            self._ws_url = self.CRYPTO_URL
        elif paper:
            self._ws_url = self.STOCK_SIP_PAPER if use_sip else self.STOCK_IEX_PAPER
        else:
            self._ws_url = self.STOCK_SIP_URL if use_sip else self.STOCK_IEX_URL
    
    async def connect(self) -> bool:
        """Connect to Alpaca streaming API"""
        try:
            logger.info(f"Connecting to Alpaca: {self._ws_url}")
            self._ws = await websockets.connect(self._ws_url)
            
            # Authenticate
            auth_msg = {
                "action": "auth",
                "key": self.api_key,
                "secret": self.api_secret
            }
            await self._ws.send(json.dumps(auth_msg))
            
            # Wait for auth response
            response = await asyncio.wait_for(self._ws.recv(), timeout=10)
            data = json.loads(response)
            
            if isinstance(data, list) and len(data) > 0:
                msg = data[0]
                if msg.get("T") == "success" and msg.get("msg") == "authenticated":
                    logger.info("Alpaca authentication successful")
                    self._is_connected = True
                    self._listen_task = asyncio.create_task(self._listen())
                    return True
                elif msg.get("T") == "error":
                    logger.error(f"Alpaca auth error: {msg.get('msg')}")
                    return False
            
            # Check for connection message first
            if isinstance(data, list) and data[0].get("T") == "success":
                # Wait for actual auth response after sending auth
                response = await asyncio.wait_for(self._ws.recv(), timeout=10)
                data = json.loads(response)
                if isinstance(data, list) and data[0].get("msg") == "authenticated":
                    logger.info("Alpaca authentication successful")
                    self._is_connected = True
                    self._listen_task = asyncio.create_task(self._listen())
                    return True
            
            logger.error(f"Unexpected auth response: {data}")
            return False
            
        except Exception as e:
            logger.error(f"Alpaca connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Close WebSocket connection"""
        self._is_connected = False
        if self._listen_task:
            self._listen_task.cancel()
        if self._ws:
            await self._ws.close()
        logger.info("Alpaca connection closed")
    
    async def subscribe(self, symbol: str) -> bool:
        """Subscribe to quotes and trades for a symbol"""
        if not self._is_connected or not self._ws:
            return False
        
        try:
            # Subscribe to quotes and trades
            sub_msg = {
                "action": "subscribe",
                "quotes": [symbol],
                "trades": [symbol]
            }
            await self._ws.send(json.dumps(sub_msg))
            self._subscriptions.append(symbol)
            logger.info(f"Alpaca subscribed to {symbol}")
            return True
        except Exception as e:
            logger.error(f"Alpaca subscribe error: {e}")
            return False
    
    async def unsubscribe(self, symbol: str):
        """Unsubscribe from symbol"""
        if not self._is_connected or not self._ws:
            return
        
        try:
            unsub_msg = {
                "action": "unsubscribe",
                "quotes": [symbol],
                "trades": [symbol]
            }
            await self._ws.send(json.dumps(unsub_msg))
            if symbol in self._subscriptions:
                self._subscriptions.remove(symbol)
            logger.info(f"Alpaca unsubscribed from {symbol}")
        except Exception as e:
            logger.error(f"Alpaca unsubscribe error: {e}")
    
    async def _listen(self):
        """Listen for incoming messages"""
        try:
            async for message in self._ws:
                data = json.loads(message)
                
                # Handle array of messages
                if isinstance(data, list):
                    for msg in data:
                        await self._process_message(msg)
                else:
                    await self._process_message(data)
                    
        except websockets.ConnectionClosed:
            logger.warning("Alpaca connection closed")
            self._is_connected = False
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Alpaca listen error: {e}")
            self._is_connected = False
    
    async def _process_message(self, msg: dict):
        """Process individual message from Alpaca"""
        msg_type = msg.get("T")
        
        if msg_type == "q":  # Quote
            # Build orderbook snapshot from quote
            snapshot = OrderBookSnapshot(
                symbol=msg.get("S", ""),
                timestamp=datetime.fromisoformat(msg.get("t", "").replace("Z", "+00:00")),
                bids=[OrderBookLevel(
                    price=msg.get("bp", 0),  # bid price
                    size=msg.get("bs", 0),   # bid size
                    order_count=1
                )],
                asks=[OrderBookLevel(
                    price=msg.get("ap", 0),  # ask price
                    size=msg.get("as", 0),   # ask size
                    order_count=1
                )]
            )
            await self._emit_orderbook(snapshot)
            
        elif msg_type == "t":  # Trade
            # Determine side based on trade conditions or price movement
            # In Alpaca, we infer from trade conditions
            side = Side.BUY  # Default, would need more context
            
            trade = TradeExecution(
                symbol=msg.get("S", ""),
                timestamp=datetime.fromisoformat(msg.get("t", "").replace("Z", "+00:00")),
                price=msg.get("p", 0),
                size=msg.get("s", 0),
                side=side,
                trade_id=str(msg.get("i", ""))
            )
            await self._emit_trade(trade)


class MassiveL2Provider(L2DataProvider):
    """
    Massive L2 Data Provider
    
    WebSocket Endpoints:
    - Delayed: wss://socket-delayed.massive.com/stocks
    - Real-time: wss://socket.massive.com/stocks
    
    Authentication: Send API key in JSON message after connecting
    Docs: https://massive.com/docs/websocket/quickstart
    """
    
    DELAYED_URL = "wss://socket-delayed.massive.com/stocks"
    REALTIME_URL = "wss://socket.massive.com/stocks"
    
    def __init__(
        self,
        api_key: str,
        realtime: bool = False  # Realtime requires subscription
    ):
        super().__init__()
        self.api_key = api_key
        self.realtime = realtime
        
        self._ws = None
        self._listen_task: Optional[asyncio.Task] = None
        self._ws_url = self.REALTIME_URL if realtime else self.DELAYED_URL
    
    async def connect(self) -> bool:
        """Connect to Massive WebSocket"""
        try:
            logger.info(f"Connecting to Massive: {self._ws_url}")
            self._ws = await websockets.connect(self._ws_url)
            
            # Wait for connection acknowledgment
            response = await asyncio.wait_for(self._ws.recv(), timeout=10)
            data = json.loads(response)
            logger.debug(f"Massive connection response: {data}")
            
            # Authenticate with API key
            auth_msg = {"action": "auth", "params": self.api_key}
            await self._ws.send(json.dumps(auth_msg))
            
            # Wait for auth response
            response = await asyncio.wait_for(self._ws.recv(), timeout=10)
            data = json.loads(response)
            
            if data.get("status") == "auth_success" or data.get("ev") == "status":
                logger.info("Massive authentication successful")
                self._is_connected = True
                self._listen_task = asyncio.create_task(self._listen())
                return True
            else:
                logger.error(f"Massive auth failed: {data}")
                return False
                
        except Exception as e:
            logger.error(f"Massive connection failed: {e}")
            return False
    
    async def disconnect(self):
        """Close WebSocket connection"""
        self._is_connected = False
        if self._listen_task:
            self._listen_task.cancel()
        if self._ws:
            await self._ws.close()
        logger.info("Massive connection closed")
    
    async def subscribe(self, symbol: str) -> bool:
        """
        Subscribe to L2/trade data for a symbol.
        
        Massive channels:
        - T.{symbol} - Trades
        - Q.{symbol} - Quotes (NBBO)
        - AM.{symbol} - Aggregates per minute
        """
        if not self._is_connected or not self._ws:
            return False
        
        try:
            # Subscribe to trades and quotes
            sub_msg = {
                "action": "subscribe",
                "params": f"T.{symbol},Q.{symbol}"
            }
            await self._ws.send(json.dumps(sub_msg))
            self._subscriptions.append(symbol)
            logger.info(f"Massive subscribed to {symbol}")
            return True
        except Exception as e:
            logger.error(f"Massive subscribe error: {e}")
            return False
    
    async def unsubscribe(self, symbol: str):
        """Unsubscribe from symbol"""
        if not self._is_connected or not self._ws:
            return
        
        try:
            unsub_msg = {
                "action": "unsubscribe",
                "params": f"T.{symbol},Q.{symbol}"
            }
            await self._ws.send(json.dumps(unsub_msg))
            if symbol in self._subscriptions:
                self._subscriptions.remove(symbol)
            logger.info(f"Massive unsubscribed from {symbol}")
        except Exception as e:
            logger.error(f"Massive unsubscribe error: {e}")
    
    async def _listen(self):
        """Listen for incoming messages"""
        try:
            async for message in self._ws:
                data = json.loads(message)
                
                # Massive may send arrays during high volume
                if isinstance(data, list):
                    for msg in data:
                        await self._process_message(msg)
                else:
                    await self._process_message(data)
                    
        except websockets.ConnectionClosed:
            logger.warning("Massive connection closed")
            self._is_connected = False
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Massive listen error: {e}")
            self._is_connected = False
    
    async def _process_message(self, msg: dict):
        """
        Process message from Massive.
        
        Event types (ev field):
        - T: Trade
        - Q: Quote (NBBO)
        - AM: Aggregate per minute
        - status: Status message
        """
        ev = msg.get("ev")
        
        if ev == "Q":  # Quote
            snapshot = OrderBookSnapshot(
                symbol=msg.get("sym", ""),
                timestamp=datetime.fromtimestamp(msg.get("t", 0) / 1000),  # Unix ms
                bids=[OrderBookLevel(
                    price=msg.get("bp", 0),  # bid price
                    size=msg.get("bs", 0),   # bid size
                    order_count=1
                )],
                asks=[OrderBookLevel(
                    price=msg.get("ap", 0),  # ask price
                    size=msg.get("as", 0),   # ask size
                    order_count=1
                )]
            )
            await self._emit_orderbook(snapshot)
            
        elif ev == "T":  # Trade
            trade = TradeExecution(
                symbol=msg.get("sym", ""),
                timestamp=datetime.fromtimestamp(msg.get("t", 0) / 1000),  # Unix ms
                price=msg.get("p", 0),
                size=msg.get("s", 0),
                side=Side.BUY,  # Massive doesn't provide side directly
                trade_id=str(msg.get("i", ""))
            )
            await self._emit_trade(trade)
            
        elif ev == "AM":  # Aggregate minute
            # Can use for OHLCV bars
            logger.debug(f"Massive AM: {msg.get('sym')} close={msg.get('c')}")
            
        elif ev == "status":
            logger.debug(f"Massive status: {msg.get('message')}")


# Backwards compatibility alias
PolygonL2Provider = MassiveL2Provider  # Massive replaces Polygon
