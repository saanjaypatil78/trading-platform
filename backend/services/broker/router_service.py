"""
Router Service - Intelligent Order Routing.
Subscribes to strategy signals and routes to the best execution path.
Uses LatencyMonitor data for decision making.
"""
import asyncio
from typing import Dict, Any
from backend.shared.messaging import bus, Event, EventTypes
from backend.shared.workflow.action_center import SmartRouter
from backend.shared.workflow.monitoring import LatencyMonitor
from backend.shared.credentials import Credentials
from backend.services.auth.usage_tracker import UsageTracker
from backend.services.broker.alpaca_adapter import AlpacaAdapter
from backend.services.broker.upstox_adapter import UpstoxAdapter
from backend.services.broker.zerodha_adapter import ZerodhaAdapter

class RouterService:
    """
    EDA-powered Order Router.
    """
    def __init__(self):
        self.router = SmartRouter()
        self.monitor = LatencyMonitor()
        self.running = False

    async def start(self):
        self.running = True
        print("[Router] Service started. Listening for signals...")
        
        # Register brokers
        self.alpaca = AlpacaAdapter()
        if Credentials.is_alpaca_configured():
            print("[Router] Configured REAL Alpaca account")
            self.alpaca.connect(Credentials.get_alpaca_creds())
            self.router.register_broker("alpaca", self.alpaca, priority=1)
        else:
            print("[Router] Using MOCK Alpaca (credentials not found)")
            self.router.register_broker("alpaca", None, priority=1)

        # Register Upstox
        self.upstox = UpstoxAdapter(
            api_key=Credentials.UPSTOX_API_KEY,
            api_secret=Credentials.UPSTOX_API_SECRET,
            redirect_uri=Credentials.UPSTOX_REDIRECT_URI
        )
        if Credentials.is_upstox_configured():
            print("[Router] Configured REAL Upstox account")
            # In real usage, we'd need an access_token here
            self.router.register_broker("upstox", self.upstox, priority=2)
        else:
            print("[Router] Using MOCK Upstox (credentials not found)")
            self.router.register_broker("upstox", None, priority=2)

        self.router.register_broker("ib", None, priority=4)

        # 1. Subscribe to strategy signals
        await bus.subscribe(EventTypes.STRATEGY_SIGNAL, self.handle_signal)
        
        # 2. Subscribe to scanner matches (if auto-trading enabled)
        await bus.subscribe(EventTypes.SCAN_MATCH, self.handle_scanner_match)

    async def handle_signal(self, event: Event):
        """React to a trading signal from AI Brain or Strategy."""
        payload = event.payload
        print(f"[Router] Received SIGNAL: {payload['symbol']} {payload['action']}")
        
        # --- MONETIZATION GATE ---
        if UsageTracker.is_limit_reached():
            print(f"[Router] BLOCKED: {UsageTracker.get_monetization_message()}")
            return # Block execution
            
        # Best routing based on current stats
        route_result = self.router.route_order(payload)
        
        if route_result.get('status') != 'FAILED':
             UsageTracker.increment_trade_count()
        
        # Record latency tracking
        self.monitor.record_order_latency(
            order_id=str(event.event_id),
            broker=route_result['broker'],
            action=payload['action'],
            latency_ms=route_result['latency_ms']
        )
        
        # Notify of execution (publish event)
        await bus.publish(Event.create(
            event_type=EventTypes.ORDER_PLACED,
            payload={**payload, "broker": route_result['broker']},
            source="router_service"
        ))

    async def handle_scanner_match(self, event: Event):
        """Auto-trade scanner matches if criteria met."""
        payload = event.payload
        # Example logic: Buy if RSI < 30 on match
        if payload.get("indicator_values", {}).get("rsi", 100) < 30:
            print(f"[Router] Auto-trading scanner match: {payload['symbol']}")
            signal_event = Event.create(
                event_type=EventTypes.STRATEGY_SIGNAL,
                payload={"symbol": payload['symbol'], "action": "BUY", "qty": 10},
                source="auto_trader"
            )
            await self.handle_signal(signal_event)

if __name__ == "__main__":
    service = RouterService()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(service.start())
    loop.run_forever()
