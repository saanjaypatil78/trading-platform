from backend.services.strategy_analyzer import StrategyAnalyzer
from backend.shared.brain.memory import KnowledgeGraph
import json

def test_memory_integration():
    # Create a shared memory instance
    memory = KnowledgeGraph()
    
    # Seed some prior knowledge
    memory.create_entities([
        {"name": "AAPL", "entity_type": "stock", "observations": [
            "Historically bullish in Q4",
            "Watch for iPhone launch events"
        ]}
    ])
    
    # Create analyzer with memory
    analyzer = StrategyAnalyzer(memory=memory)
    
    # Run analysis 1: AAPL with overbought RSI
    print("--- Analysis 1: AAPL (RSI 75) ---")
    result1 = analyzer.analyze_market("AAPL", {"price": 150, "rsi": 75})
    print(f"Decision: {result1['decision']}")
    for step in result1['reasoning_trace']:
        print(f"  [{step['thought_number']}] {step['thought']}")
    
    # Run analysis 2: Analyze AAPL again - should now have MORE context
    print("\n--- Analysis 2: AAPL (RSI 45) - Should recall prior signal ---")
    result2 = analyzer.analyze_market("AAPL", {"price": 155, "rsi": 45})
    print(f"Decision: {result2['decision']}")
    for step in result2['reasoning_trace']:
        print(f"  [{step['thought_number']}] {step['thought']}")
    
    # Show the memory growth
    print("\n--- Memory State ---")
    print(json.dumps(memory.get_related("AAPL"), indent=2))

if __name__ == "__main__":
    test_memory_integration()
