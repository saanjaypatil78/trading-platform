"""
Tests for Scanner and Broker services.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

def test_indicators():
    """Test technical indicators."""
    from backend.services.scanner.indicators import rsi, sma, ema, macd, bollinger_bands
    
    # Generate test data
    prices = [100 + i * 0.5 for i in range(50)]  # Uptrending prices
    
    # Test SMA
    sma_val = sma(prices, 20)
    assert sma_val is not None
    print(f"SMA(20): {sma_val:.2f}")
    
    # Test RSI
    rsi_val = rsi(prices, 14)
    assert rsi_val is not None
    assert 0 <= rsi_val <= 100
    print(f"RSI(14): {rsi_val:.2f}")
    
    # Test MACD
    macd_result = macd(prices)
    assert macd_result["macd"] is not None
    print(f"MACD: {macd_result['macd']:.2f}")
    
    # Test Bollinger
    bb = bollinger_bands(prices, 20)
    assert bb["upper"] is not None
    print(f"Bollinger: Upper={bb['upper']:.2f}, Middle={bb['middle']:.2f}, Lower={bb['lower']:.2f}")
    
    print("[PASS] Indicators test")

def test_scanner():
    """Test scanner conditions and engine."""
    from backend.services.scanner.conditions import Condition, ScannerConditions, Operator, ConditionEvaluator
    from backend.services.scanner.scanner_engine import ScannerEngine
    
    # Create test data
    stock_data = {
        "RELIANCE": {"closes": [2500 + i * 10 for i in range(50)], "volumes": [1000000] * 50},
        "TCS": {"closes": [3500 - i * 5 for i in range(50)], "volumes": [500000] * 50},
    }
    
    # Test RSI overbought scanner
    engine = ScannerEngine()
    results = engine.scan_template("rsi_overbought", stock_data)
    print(f"RSI Overbought scan: {len(results)} matches")
    
    # Test custom condition
    conditions = ScannerConditions(
        conditions=[
            Condition(left="sma(close, 20)", operator=Operator.GT, right="sma(close, 50)")
        ],
        logic="AND"
    )
    results = engine.scan(conditions, stock_data)
    print(f"SMA crossover scan: {len(results)} matches")
    
    print("[PASS] Scanner test")

def test_paper_broker():
    """Test paper trading broker."""
    from backend.services.broker.paper_broker import PaperBroker
    from backend.services.broker.adapter import OrderSide, OrderType, ProductType, OrderStatus
    
    broker = PaperBroker(initial_capital=100000)
    broker.connect({})
    
    # Check initial funds
    funds = broker.get_funds()
    assert funds["total_capital"] == 100000
    print(f"Initial capital: {funds['total_capital']}")
    
    # Place a market buy order
    order = broker.place_order(
        symbol="RELIANCE",
        side=OrderSide.BUY,
        quantity=10,
        order_type=OrderType.MARKET,
        product=ProductType.MIS
    )
    assert order.status == OrderStatus.COMPLETE
    print(f"Order placed: {order.order_id}, Status: {order.status.value}, Avg Price: {order.average_price:.2f}")
    
    # Check positions
    positions = broker.get_positions()
    assert len(positions) == 1
    print(f"Position: {positions[0].symbol}, Qty: {positions[0].quantity}")
    
    # Check funds reduced
    funds = broker.get_funds()
    assert funds["available_cash"] < 100000
    print(f"Available cash: {funds['available_cash']:.2f}")
    
    # Place a sell order to close
    sell_order = broker.place_order(
        symbol="RELIANCE",
        side=OrderSide.SELL,
        quantity=10,
        order_type=OrderType.MARKET,
        product=ProductType.MIS
    )
    assert sell_order.status == OrderStatus.COMPLETE
    print(f"Sell order: {sell_order.order_id}, Status: {sell_order.status.value}")
    
    print("[PASS] Paper broker test")

if __name__ == "__main__":
    print("=" * 50)
    print("Testing Indicators")
    print("=" * 50)
    test_indicators()
    
    print("\n" + "=" * 50)
    print("Testing Scanner")
    print("=" * 50)
    test_scanner()
    
    print("\n" + "=" * 50)
    print("Testing Paper Broker")
    print("=" * 50)
    test_paper_broker()
    
    print("\n" + "=" * 50)
    print("ALL TESTS PASSED!")
    print("=" * 50)
