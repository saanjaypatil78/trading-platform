from typing import List, Dict, Set
from fastapi import WebSocket, WebSocketDisconnect
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for real-time data streaming
    Supports subscription-based broadcasting per symbol
    """
    
    def __init__(self):
        # Active connections mapped by symbol
        self.symbol_connections: Dict[str, Set[WebSocket]] = {}
        # All active connections
        self.active_connections: List[WebSocket] = []
        # Connection metadata (user_id, connected_at, etc.)
        self.connection_metadata: Dict[WebSocket, dict] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str = None):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_metadata[websocket] = {
            "user_id": user_id,
            "connected_at": datetime.now(),
            "subscriptions": set()
        }
        logger.info(f"New WebSocket connection. Total connections: {len(self.active_connections)}")
    
    async def disconnect(self, websocket: WebSocket):
        """Handle WebSocket disconnection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            
            # Remove from all symbol subscriptions
            metadata = self.connection_metadata.get(websocket, {})
            subscriptions = metadata.get("subscriptions", set())
            
            for symbol in subscriptions:
                if symbol in self.symbol_connections:
                    self.symbol_connections[symbol].discard(websocket)
                    if not self.symbol_connections[symbol]:
                        # Remove empty symbol subscriptions
                        del self.symbol_connections[symbol]
            
            # Clean up metadata
            if websocket in self.connection_metadata:
                del self.connection_metadata[websocket]
            
            logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def subscribe(self, websocket: WebSocket, symbol: str):
        """Subscribe connection to specific symbol updates"""
        if symbol not in self.symbol_connections:
            self.symbol_connections[symbol] = set()
        
        self.symbol_connections[symbol].add(websocket)
        
        if websocket in self.connection_metadata:
            self.connection_metadata[websocket]["subscriptions"].add(symbol)
        
        logger.info(f"WebSocket subscribed to {symbol}. Subscribers: {len(self.symbol_connections[symbol])}")
    
    async def unsubscribe(self, websocket: WebSocket, symbol: str):
        """Unsubscribe connection from symbol updates"""
        if symbol in self.symbol_connections:
            self.symbol_connections[symbol].discard(websocket)
            
            if not self.symbol_connections[symbol]:
                del self.symbol_connections[symbol]
        
        if websocket in self.connection_metadata:
            self.connection_metadata[websocket]["subscriptions"].discard(symbol)
        
        logger.info(f"WebSocket unsubscribed from {symbol}")
    
    async def broadcast_to_all(self, message: dict):
        """Broadcast message to all connected clients"""
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            await self.disconnect(conn)
    
    async def broadcast_to_symbol(self, symbol: str, message: dict):
        """Broadcast message to all clients subscribed to a symbol"""
        if symbol not in self.symbol_connections:
            return
        
        disconnected = []
        subscribers = list(self.symbol_connections[symbol])
        
        for connection in subscribers:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {symbol} subscriber: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            await self.disconnect(conn)
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific connection"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            await self.disconnect(websocket)
    
    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return len(self.active_connections)
    
    def get_symbol_subscriber_count(self, symbol: str) -> int:
        """Get number of subscribers for a symbol"""
        return len(self.symbol_connections.get(symbol, set()))
    
    def get_all_subscribed_symbols(self) -> List[str]:
        """Get list of all symbols with active subscriptions"""
        return list(self.symbol_connections.keys())
    
    def get_connection_info(self) -> dict:
        """Get connection statistics"""
        return {
            "total_connections": len(self.active_connections),
            "tracked_symbols": len(self.symbol_connections),
            "subscriptions_by_symbol": {
                symbol: len(connections) 
                for symbol, connections in self.symbol_connections.items()
            }
        }
