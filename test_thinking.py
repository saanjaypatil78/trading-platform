from backend.services.strategy_analyzer import StrategyAnalyzer
import json

def test_chain():
    analyzer = StrategyAnalyzer()
    
    # Scenario 1: Overbought
    print("\n--- Scenario 1: Overbought ---")
    result1 = analyzer.analyze_market("AAPL", {"price": 150, "rsi": 75})
    print(f"Decision: {result1['decision']}")
    print(f"Thoughts: {len(result1['reasoning_trace'])}")
    
    # Scenario 2: Oversold + Down Trend (Branching)
    print("\n--- Scenario 2: Oversold + Down Trend ---")
    result2 = analyzer.analyze_market("TSLA", {"price": 200, "rsi": 25, "trend": "down"})
    print(f"Decision: {result2['decision']}")
    print(f"Reasoning: \n{json.dumps(result2['reasoning_trace'], indent=2)}")

if __name__ == "__main__":
    test_chain()
