from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import logging
from datetime import datetime
from typing import Optional
import sys
import os

# Add parent directories to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from shared.config import settings
from shared.cache import cache
from .connection_manager import ConnectionManager
from .redis_subscriber import RedisSubscriber
from .models import (
    SubscribeMessage, UnsubscribeMessage, QuoteUpdate, 
    OHLCUpdate, ScanAlert, SystemMessage, HeartbeatMessage,
    ErrorMessage
)

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="WebSocket Service",
    description="Real-time market data streaming via WebSocket",
    version="1.0.0"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global connection manager
manager = ConnectionManager()

# Global Redis subscriber
redis_subscriber: Optional[RedisSubscriber] = None

# Heartbeat task
heartbeat_task = None


async def handle_redis_message(channel: str, message: dict):
    """
    Callback for Redis messages
    Broadcasts to appropriate WebSocket clients
    """
    try:
        logger.debug(f"Received message from {channel}")
        
        # Parse channel to determine message type and symbol
        # Format: "market_data:quotes:SYMBOL" or "scanner:alerts"
        parts = channel.split(":")
        
        if len(parts) >= 3 and parts[0] == "market_data":
            msg_type = parts[1]
            symbol = parts[2]
            
            if msg_type == "quotes":
                # Broadcast quote update to symbol subscribers
                await manager.broadcast_to_symbol(symbol, message)
            elif msg_type == "ohlc":
                # Broadcast OHLC update to symbol subscribers
                await manager.broadcast_to_symbol(symbol, message)
        
        elif parts[0] == "scanner" and parts[1] == "alerts":
            # Broadcast scanner alerts to all connections
            await manager.broadcast_to_all(message)
        
        elif parts[0] == "system":
            # Broadcast system messages to all
            await manager.broadcast_to_all(message)
    
    except Exception as e:
        logger.error(f"Error handling Redis message: {e}")


async def heartbeat_loop():
    """Send periodic heartbeat to all connections"""
    while True:
        try:
            await asyncio.sleep(30)  # Every 30 seconds
            
            heartbeat_msg = HeartbeatMessage().dict()
            await manager.broadcast_to_all(heartbeat_msg)
            
            logger.debug(f"Heartbeat sent to {manager.get_connection_count()} connections")
        
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in heartbeat loop: {e}")


@app.on_event("startup")
async def startup():
    """Initialize services on startup"""
    global redis_subscriber, heartbeat_task
    
    logger.info("Starting WebSocket Service...")
    
    # Connect to Redis cache
    await cache.connect()
    if cache.redis_client:
        # Initialize Redis Pub/Sub subscriber
        redis_subscriber = RedisSubscriber(broadcast_callback=handle_redis_message)
        await redis_subscriber.connect()
    
    # Subscribe to relevant channels
        await redis_subscriber.subscribe_to_pattern("market_data:*")
        await redis_subscriber.subscribe_to_pattern("scanner:*")
        await redis_subscriber.subscribe_to_channel("system:notifications")
    
    # Start listening to Redis
        redis_subscriber.start_listening()
    
    # Start heartbeat loop
    heartbeat_task = asyncio.create_task(heartbeat_loop())
    
    logger.info("WebSocket Service started successfully")


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    global heartbeat_task
    
    logger.info("Shutting down WebSocket Service...")
    
    # Cancel heartbeat
    if heartbeat_task:
        heartbeat_task.cancel()
        try:
            await heartbeat_task
        except asyncio.CancelledError:
            pass
    
    # Disconnect Redis
    if redis_subscriber:
        await redis_subscriber.disconnect()
    
    # Disconnect cache
    await cache.disconnect()
    
    logger.info("WebSocket Service shutdown complete")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "websocket",
        "connections": manager.get_connection_count(),
        "subscribed_symbols": len(manager.get_all_subscribed_symbols())
    }


@app.get("/stats")
async def get_stats():
    """Get connection statistics"""
    return manager.get_connection_info()


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="JWT authentication token")
):
    """
    Main WebSocket endpoint for real-time data
    
    Usage:
        ws://localhost:8003/ws?token=YOUR_JWT_TOKEN
    
    Message Format:
        Subscribe: {"action": "subscribe", "symbol": "RELIANCE"}
        Unsubscribe: {"action": "unsubscribe", "symbol": "RELIANCE"}
    """
    # TODO: Validate JWT token for authentication
    # For now, accept all connections
    user_id = "anonymous"  # Extract from JWT in production
    
    await manager.connect(websocket, user_id=user_id)
    
    try:
        # Send welcome message
        welcome_msg = SystemMessage(
            level="info",
            message=f"Connected to WebSocket service. Total connections: {manager.get_connection_count()}"
        )
        await manager.send_personal_message(welcome_msg.dict(), websocket)
        
        # Handle incoming messages
        while True:
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                action = message.get("action")
                
                if action == "subscribe":
                    symbol = message.get("symbol")
                    if symbol:
                        await manager.subscribe(websocket, symbol)
                        
                        response = SystemMessage(
                            level="info",
                            message=f"Subscribed to {symbol}"
                        )
                        await manager.send_personal_message(response.dict(), websocket)
                
                elif action == "unsubscribe":
                    symbol = message.get("symbol")
                    if symbol:
                        await manager.unsubscribe(websocket, symbol)
                        
                        response = SystemMessage(
                            level="info",
                            message=f"Unsubscribed from {symbol}"
                        )
                        await manager.send_personal_message(response.dict(), websocket)
                
                elif action == "ping":
                    # Respond to client ping
                    pong = HeartbeatMessage()
                    await manager.send_personal_message(pong.dict(), websocket)
                
                else:
                    error_msg = ErrorMessage(
                        error_code="UNKNOWN_ACTION",
                        error_message=f"Unknown action: {action}"
                    )
                    await manager.send_personal_message(error_msg.dict(), websocket)
            
            except json.JSONDecodeError:
                error_msg = ErrorMessage(
                    error_code="INVALID_JSON",
                    error_message="Invalid JSON format"
                )
                await manager.send_personal_message(error_msg.dict(), websocket)
            
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                error_msg = ErrorMessage(
                    error_code="PROCESSING_ERROR",
                    error_message=str(e)
                )
                await manager.send_personal_message(error_msg.dict(), websocket)
    
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
        logger.info("Client disconnected")
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.API_HOST, port=8003)
