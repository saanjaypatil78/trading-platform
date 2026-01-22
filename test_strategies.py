"""
Test the Strategic Thinking Module across all 5 strategies.
"""
from backend.shared.brain.strategic_thinking import StrategicThinker, ThinkingStrategy
import json

def print_trace(trace):
    for step in trace:
        branch = f" [{step.get('branch_id', '')}]" if step.get('branch_id') else ""
        print(f"  [{step['thought_number']}]{branch} {step['thought']}")

def main():
    thinker = StrategicThinker()
    
    # =========================================================================
    # Strategy 1: Entry Analysis
    # =========================================================================
    print("=" * 60)
    print("STRATEGY 1: ENTRY ANALYSIS")
    print("=" * 60)
    result = thinker.think(ThinkingStrategy.ENTRY_ANALYSIS, {
        "symbol": "NVDA",
        "rsi": 28,          # Oversold
        "macd": 5.2,        # Above signal
        "macd_signal": 4.8,
        "volume": 50_000_000,
        "avg_volume": 30_000_000
    })
    print(f"Decision: {result['decision']} ({result['confidence']})")
    print_trace(result['trace'])
    
    # =========================================================================
    # Strategy 2: Risk Assessment
    # =========================================================================
    print("\n" + "=" * 60)
    print("STRATEGY 2: RISK ASSESSMENT")
    print("=" * 60)
    result = thinker.think(ThinkingStrategy.RISK_ASSESSMENT, {
        "account_size": 50000,
        "risk_percent": 2,
        "entry_price": 150,
        "stop_loss": 145
    })
    print(f"Position Size: {result['position_size']} shares (${result['position_value']:,.0f})")
    print_trace(result['trace'])
    
    # =========================================================================
    # Strategy 3: Regime Detection
    # =========================================================================
    print("\n" + "=" * 60)
    print("STRATEGY 3: REGIME DETECTION")
    print("=" * 60)
    result = thinker.think(ThinkingStrategy.REGIME_DETECTION, {
        "price": 450,
        "sma_50": 440,
        "sma_200": 400,
        "atr": 8
    })
    print(f"Regime: {result['regime']} | Volatility: {result['volatility']}")
    print(f"Recommendation: {result['recommendation']}")
    print_trace(result['trace'])
    
    # =========================================================================
    # Strategy 4: Portfolio Rebalance
    # =========================================================================
    print("\n" + "=" * 60)
    print("STRATEGY 4: PORTFOLIO REBALANCE")
    print("=" * 60)
    result = thinker.think(ThinkingStrategy.PORTFOLIO_REBALANCE, {
        "holdings": {"AAPL": 25000, "GOOGL": 15000, "MSFT": 10000},
        "targets": {"AAPL": 40, "GOOGL": 40, "MSFT": 20}  # Want 40/40/20
    })
    print(f"Actions Needed: {len(result['actions'])}")
    for action in result['actions']:
        print(f"  {action['action']} ${action['amount']:,.0f} of {action['symbol']}")
    print_trace(result['trace'])
    
    # =========================================================================
    # Strategy 5: Earnings Play
    # =========================================================================
    print("\n" + "=" * 60)
    print("STRATEGY 5: EARNINGS PLAY")
    print("=" * 60)
    result = thinker.think(ThinkingStrategy.EARNINGS_PLAY, {
        "symbol": "TSLA",
        "iv": 85,
        "iv_rank": 78,
        "expected_move": 8
    })
    print(f"Strategy: {result['recommended_strategy']}")
    print(f"Rationale: {result['rationale']}")
    print_trace(result['trace'])

if __name__ == "__main__":
    main()
