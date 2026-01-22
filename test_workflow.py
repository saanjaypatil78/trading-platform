"""
Test the Workflow modules (Action Center, Monitoring, Notifications).
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

def test_action_center():
    """Test Action Center with Auto and Semi-Auto modes."""
    from backend.shared.workflow import ActionCenter, ExecutionMode
    
    # Test AUTO mode
    print("--- Testing AUTO Mode ---")
    ac_auto = ActionCenter(mode=ExecutionMode.AUTO)
    
    result = ac_auto.submit_action(
        action_type="place_order",
        payload={"symbol": "RELIANCE", "side": "BUY", "qty": 10},
        source="scanner"
    )
    assert result["mode"] == "auto"
    assert result["status"] == "executed"
    print(f"Auto mode result: {result['status']}")
    
    # Test SEMI_AUTO mode
    print("\n--- Testing SEMI-AUTO Mode ---")
    ac_semi = ActionCenter(mode=ExecutionMode.SEMI_AUTO)
    
    result = ac_semi.submit_action(
        action_type="place_order",
        payload={"symbol": "TCS", "side": "SELL", "qty": 5},
        source="webhook"
    )
    assert result["mode"] == "semi-auto"
    assert result["status"] == "pending_approval"
    print(f"Semi-auto mode result: {result['status']}")
    
    # Check pending
    pending = ac_semi.get_pending()
    assert len(pending) == 1
    print(f"Pending actions: {len(pending)}")
    
    # Approve
    approval = ac_semi.approve_action(result["action_id"])
    assert approval["status"] == "approved_and_executed"
    print(f"Approval result: {approval['status']}")
    
    print("[PASS] Action Center test")

def test_smart_router():
    """Test Smart Router with latency-based routing."""
    from backend.shared.workflow import SmartRouter
    
    router = SmartRouter()
    
    # Register mock brokers
    router.register_broker("zerodha", None, priority=1)
    router.register_broker("angel", None, priority=2)
    
    # Route orders
    for i in range(10):
        result = router.route_order({"symbol": "INFY", "qty": 10})
        assert result["status"] == "executed"
    
    stats = router.get_broker_stats()
    print(f"Broker stats: {stats}")
    
    print("[PASS] Smart Router test")

def test_monitoring():
    """Test Latency and Traffic monitors."""
    from backend.shared.workflow import LatencyMonitor, TrafficMonitor, PnLTracker
    
    # Test Latency Monitor
    print("\n--- Testing Latency Monitor ---")
    lm = LatencyMonitor()
    
    for i in range(50):
        lm.record_order_latency(f"ORD{i}", "zerodha", "place", 15 + i % 10)
    
    stats = lm.get_stats()
    print(f"Latency stats: avg={stats['avg_ms']:.1f}ms, p95={stats['p95_ms']:.1f}ms")
    
    # Test Traffic Monitor
    print("\n--- Testing Traffic Monitor ---")
    tm = TrafficMonitor()
    
    for i in range(100):
        status = 200 if i % 10 != 0 else 500
        tm.record_request(
            endpoint="/api/v1/orders",
            method="POST",
            status_code=status,
            latency_ms=20 + i % 30
        )
    
    overview = tm.get_overview()
    print(f"Traffic: {overview['total_requests']} requests, {overview['error_count']} errors")
    
    # Test PnL Tracker
    print("\n--- Testing PnL Tracker ---")
    pnl = PnLTracker()
    
    pnl.record_trade("RELIANCE", "BUY", 10, 2500, 2550, 500)
    pnl.record_trade("TCS", "SELL", 5, 3500, 3450, -250)
    
    summary = pnl.get_summary()
    print(f"P&L: Total={summary['total_pnl']}, Win Rate={summary['win_rate']:.0f}%")
    
    print("[PASS] Monitoring test")

if __name__ == "__main__":
    print("=" * 50)
    print("Testing Action Center")
    print("=" * 50)
    test_action_center()
    
    print("\n" + "=" * 50)
    print("Testing Smart Router")
    print("=" * 50)
    test_smart_router()
    
    print("\n" + "=" * 50)
    print("Testing Monitoring")
    print("=" * 50)
    test_monitoring()
    
    print("\n" + "=" * 50)
    print("ALL WORKFLOW TESTS PASSED!")
    print("=" * 50)
