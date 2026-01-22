"""
Test WebSocket connections
Run with: python backend/tests/test_websocket_manual.py
"""
import asyncio
import websockets
import json


async def test_websocket():
    """Test WebSocket connection and subscriptions"""
    uri = "ws://localhost:8003/ws"
    
    print("Connecting to WebSocket...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected!")
            
            # Wait for welcome message
            message = await websocket.recv()
            print(f"📩 Received: {message}")
            
            # Subscribe to RELIANCE
            subscribe_msg = json.dumps({
                "action": "subscribe",
                "symbol": "RELIANCE"
            })
            await websocket.send(subscribe_msg)
            print(f"📤 Sent: {subscribe_msg}")
            
            # Receive subscription confirmation
            message = await websocket.recv()
            print(f"📩 Received: {message}")
            
            # Subscribe to TCS
            subscribe_msg = json.dumps({
                "action": "subscribe",
                "symbol": "TCS"
            })
            await websocket.send(subscribe_msg)
            print(f"📤 Sent: {subscribe_msg}")
            
            # Receive confirmation
            message = await websocket.recv()
            print(f"📩 Received: {message}")
            
            # Listen for updates (30 seconds)
            print("\n⏱️  Listening for updates for 30 seconds...")
            print("(Market data updates will appear if services are publishing)")
            
            try:
                for _ in range(30):
                    message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(message)
                    msg_type = data.get("type", "unknown")
                    print(f"📊 {msg_type.upper()}: {message[:100]}...")
            except asyncio.TimeoutError:
                print("⏸️  No updates received (this is normal if market data isn't publishing)")
            
            # Unsubscribe
            unsubscribe_msg = json.dumps({
                "action": "unsubscribe",
                "symbol": "RELIANCE"
            })
            await websocket.send(unsubscribe_msg)
            print(f"\n📤 Sent: {unsubscribe_msg}")
            
            message = await websocket.recv()
            print(f"📩 Received: {message}")
            
            print("\n✅ WebSocket test completed successfully!")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_websocket())
