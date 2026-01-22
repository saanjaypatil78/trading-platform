"""
Market Data Service - Simulated HFT-ready tick feed.
Publishes high-frequency price updates to the MessageBus.
"""
import asyncio
import random
from datetime import datetime
from backend.shared.messaging import bus, Event, EventTypes
from backend.shared.state import state, StateKeys

class MarketDataService:
    """
    Simulates a real-time data feed (Websocket style).
    """
    def __init__(self):
        self.symbols = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "NVDA", "AAPL", "TSLA"]
        self.prices = {s: random.uniform(100, 3000) for s in self.symbols}
        self.running = False

    async def start(self):
        self.running = True
        print("[MarketData] Starting simulated tick feed...")
        while self.running:
            # Simulate high-frequency updates for random symbols
            symbol = random.choice(self.symbols)
            change = random.uniform(-0.05, 0.05) # 0.05% change
            self.prices[symbol] *= (1 + change/100)
            
            price = round(self.prices[symbol], 2)
            
            # 1. Update State Store (Fast access)
            state.hset(StateKeys.LTP, symbol, price)
            
            # 2. Publish Event (Reactive reaction)
            await bus.publish(Event.create(
                event_type=EventTypes.TICK_DATA,
                payload={
                    "symbol": symbol,
                    "price": price,
                    "v": random.randint(10, 1000),
                    "t": int(datetime.now().timestamp() * 1000)
                },
                source="market_data_service"
            ))
            
            # Simulate 100 updates per second (10ms delay)
            await asyncio.sleep(0.01)

    def stop(self):
        self.running = False

if __name__ == "__main__":
    mds = MarketDataService()
    asyncio.run(mds.start())
