"""
Demo Script - Test Orderflow System with Mock Data

Run this to see the orderflow service in action without any API keys.
"""

import asyncio
import httpx


async def main():
    base_url = "http://localhost:8008"  # Orderflow service
    broker_url = "http://localhost:8009"  # Broker service
    
    print("=" * 60)
    print("🚀 Orderflow System Demo")
    print("=" * 60)
    
    async with httpx.AsyncClient() as client:
        # 1. Health check
        print("\n📊 Checking service health...")
        resp = await client.get(f"{base_url}/health")
        health = resp.json()
        print(f"   Status: {health['status']}")
        print(f"   Providers: {health['providers']}")
        
        # 2. Subscribe to mock data
        print("\n📡 Subscribing to AAPL L2 data...")
        resp = await client.post(f"{base_url}/subscribe", json={
            "symbol": "AAPL",
            "provider": "mock"
        })
        print(f"   {resp.json()}")
        
        # Wait for some data to accumulate
        print("\n⏳ Waiting for mock data to generate...")
        await asyncio.sleep(3)
        
        # 3. Get orderbook
        print("\n📈 Fetching orderbook...")
        resp = await client.get(f"{base_url}/orderbook/AAPL")
        if resp.status_code == 200:
            book = resp.json()
            print(f"   Best Bid: ${book['bids'][0]['price']:.2f} x {book['bids'][0]['size']:.0f}")
            print(f"   Best Ask: ${book['asks'][0]['price']:.2f} x {book['asks'][0]['size']:.0f}")
        
        # 4. Check for walls
        print("\n🧱 Checking for bid/ask walls...")
        resp = await client.get(f"{base_url}/walls/AAPL")
        walls = resp.json()
        if walls.get("bid_walls"):
            print(f"   Bid Walls: {walls['bid_walls']}")
        if walls.get("ask_walls"):
            print(f"   Ask Walls: {walls['ask_walls']}")
        else:
            print("   No significant walls detected")
        
        # 5. Estimate slippage
        print("\n💧 Estimating slippage for 500 share buy order...")
        resp = await client.get(f"{base_url}/slippage/AAPL", params={
            "side": "buy",
            "quantity": 500
        })
        if resp.status_code == 200:
            slip = resp.json()
            print(f"   Estimated Avg Price: ${slip['estimated_avg_price']:.2f}")
            print(f"   Estimated Slippage: {slip['estimated_slippage_pct']:.3f}%")
        
        # 6. Validate a hypothetical trade
        print("\n✅ Validating trade signal...")
        resp = await client.post(f"{base_url}/validate", json={
            "symbol": "AAPL",
            "side": "buy",
            "quantity": 100,
            "signal_type": "absorption",
            "confidence": "high",
            "max_slippage_pct": 0.5
        })
        validation = resp.json()
        if validation.get("approved"):
            print("   ✅ APPROVED for execution!")
            print(f"   Recommended Quantity: {validation.get('recommended_quantity')}")
        else:
            print("   ❌ REJECTED")
            print(f"   Reason: {validation.get('rejection_reason')}")
        
        # 7. Get metrics
        print("\n📉 Confirmation mesh metrics...")
        resp = await client.get(f"{base_url}/metrics")
        metrics = resp.json()
        print(f"   Total Requests: {metrics['total_requests']}")
        print(f"   Approved: {metrics['approved']}")
        print(f"   Rejected: {metrics['rejected']}")
        
        print("\n" + "=" * 60)
        print("✨ Demo completed! Services are ready for use.")
        print("=" * 60)
        print("\nNext steps:")
        print("  1. Connect frontend to WebSocket /ws/l2/{symbol}")
        print("  2. Import n8n workflow from infrastructure/n8n/")
        print("  3. Add real API keys when ready")


if __name__ == "__main__":
    print("\nTo run this demo:")
    print("  1. Start orderflow service: python -m backend.services.orderflow.main")
    print("  2. Run this script: python scripts/demo_orderflow.py\n")
    
    try:
        asyncio.run(main())
    except httpx.ConnectError:
        print("\n❌ Could not connect to services. Please start them first:")
        print("   python -m backend.services.orderflow.main")
