"""
System Orchestrator - Runs all EDA services together.
Demonstrates the full pipeline: Data -> Scanner -> Brain -> Router -> Exec.
"""
import asyncio
from backend.services.market_data_service import MarketDataService
from backend.services.broker.router_service import RouterService
from backend.services.scanner.scanner_engine import ScannerEngine
from backend.services.scanner.conditions import ScannerConditions, Condition, Operator
from backend.shared.messaging import bus, Event, EventTypes
from backend.shared.state import state, StateKeys

async def run_scanner_loop(engine: ScannerEngine):
    """Periodically scan the universe."""
    print("[Orchestrator] Scanner loop started.")
    universe = ["RELIANCE", "TCS", "INFY", "NVDA", "AAPL", "TSLA"]
    conditions = ScannerConditions(
        conditions=[Condition(left="rsi(14)", operator=Operator.LT, right="30")],
        logic="AND"
    )
    
    while True:
        # Generate simulated OHLCV data for scanning
        # In real world, this would be pulled from the Tick history in StateStore
        mock_universe_data = {}
        for s in universe:
            # Create dummy price series
            base = state.hget(StateKeys.LTP, s) or random_price()
            mock_universe_data[s] = {
                "closes": [base * (1 + random_price()/10000) for _ in range(50)],
                "highs": [base * 1.01 for _ in range(50)],
                "lows": [base * 0.99 for _ in range(50)],
                "volumes": [random_price() * 100 for _ in range(50)]
            }
            
        await engine.scan(conditions, mock_universe_data)
        await asyncio.sleep(5) # Scan every 5 seconds

def random_price():
    import random
    return random.uniform(100, 2000)

async def monitor_events():
    """Log all events in the system for debugging."""
    async def logger(event: Event):
        print(f"  [EVENT] {event.timestamp} | {event.event_type} | {event.source}")
    
    await bus.subscribe("*", logger)

async def main():
    # 1. Initialize Services
    data_svc = MarketDataService()
    router_svc = RouterService()
    scanner = ScannerEngine()
    
    # 2. Setup monitor
    await monitor_events()
    
    # 3. Create Tasks
    tasks = [
        asyncio.create_task(data_svc.start()),
        asyncio.create_task(router_svc.start()),
        asyncio.create_task(run_scanner_loop(scanner))
    ]
    
    print("\n" + "="*60)
    print("   UINFRASTRUCTURE EDA ORCHESTRATOR ACTIVE")
    print("="*60 + "\n")
    
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        data_svc.stop()
        print("\nShutdown complete.")

if __name__ == "__main__":
    asyncio.run(main())
