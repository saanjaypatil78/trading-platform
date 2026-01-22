"""
Polygon.io Market Data Provider
Integrates institutional-grade L1/L2 data into the platform.
"""
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from polygon import RESTClient

from backend.shared.messaging import bus, Event, EventTypes
from backend.shared.state import state

class PolygonProvider:
    def __init__(self, api_key: str):
        self.client = RESTClient(api_key=api_key)
        self.active_tickers = []

    def get_latest_quote(self, symbol: str) -> Dict[str, Any]:
        """Fetch latest L1 quote from Polygon."""
        try:
            res = self.client.get_last_quote(symbol)
            data = {
                "symbol": symbol,
                "ask": res.ask_price,
                "bid": res.bid_price,
                "ask_size": res.ask_size,
                "bid_size": res.bid_size,
                "timestamp": res.participant_timestamp / 1e6 # Conv to ms
            }
            # Cache in StateStore
            state.set(f"ltp:{symbol}", (res.ask_price + res.bid_price) / 2)
            return data
        except Exception as e:
            print(f"[Polygon] Failed to get quote for {symbol}: {e}")
            return {}

    def get_historical_ohlc(
        self, 
        symbol: str, 
        multiplier: int = 1, 
        timespan: str = "minute", 
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Fetch historical aggregates."""
        if not from_date:
            from_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        if not to_date:
            to_date = datetime.now().strftime("%Y-%m-%d")

        try:
            aggs = self.client.get_aggs(
                ticker=symbol,
                multiplier=multiplier,
                timespan=timespan,
                from_=from_date,
                to=to_date
            )
            
            history = []
            for b in aggs:
                history.append({
                    "timestamp": b.timestamp,
                    "open": b.open,
                    "high": b.high,
                    "low": b.low,
                    "close": b.close,
                    "volume": b.volume
                })
            return history
        except Exception as e:
            print(f"[Polygon] Historical fetch failed: {e}")
            return []

    async def stream_ticks(self, symbols: List[str]):
        """
        Placeholder for WebSocket implementation.
        In a real HFT system, this would maintain a persistent WS connection.
        """
        print(f"[Polygon] Starting simulation stream for {symbols}")
        while True:
            for s in symbols:
                # In real scenario, this would be a WS callback
                quote = self.get_latest_quote(s)
                if quote:
                    await bus.publish(Event.create(
                        event_type=EventTypes.TICK,
                        payload=quote,
                        source="polygon_provider"
                    ))
            await time.sleep(1) # Frequency limit for basic tier
