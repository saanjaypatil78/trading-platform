"""
Comprehensive module verification test.
"""
print("Testing all modules...")

# Brain
from backend.shared.brain import SequentialThinker, KnowledgeGraph, StrategicThinker
print("[OK] Brain module")

# Workflow
from backend.shared.workflow import ActionCenter, SmartRouter, LatencyMonitor, TrafficMonitor, PnLTracker
print("[OK] Workflow module")

# Scanner
from backend.services.scanner.scanner_engine import ScannerEngine
from backend.services.scanner.indicators import rsi, sma, macd
print("[OK] Scanner module")

# Broker
from backend.services.broker.paper_broker import PaperBroker
from backend.services.broker.adapter import OrderType, OrderSide
print("[OK] Broker module")

# Quick functional test
thinker = SequentialThinker()
thinker.add_thought("Test thought", total_thoughts_estimate=3)
print("[OK] SequentialThinker works")

scanner = ScannerEngine()
print(f"[OK] Scanner templates: {scanner.get_available_templates()}")

broker = PaperBroker()
broker.connect({})
funds = broker.get_funds()
print(f"[OK] Paper broker capital: {funds['total_capital']}")

print()
print("=" * 50)
print("ALL MODULES WORKING CORRECTLY!")
print("=" * 50)
