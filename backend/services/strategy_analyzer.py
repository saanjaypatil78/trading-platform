from typing import Dict, Any, List, Optional
from backend.shared.brain.sequential_thinking import SequentialThinker
from backend.shared.brain.memory import KnowledgeGraph

class StrategyAnalyzer:
    """
    Analyzes market conditions using a structured chain-of-thought process,
    enhanced with a persistent Knowledge Graph for context.
    """
    
    def __init__(self, memory: Optional[KnowledgeGraph] = None):
        """
        Initialize with an optional KnowledgeGraph for persistent memory.
        """
        self.memory = memory or KnowledgeGraph()
    
    def analyze_market(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        thinker = SequentialThinker()
        
        # Step 0: Consult Memory for prior context
        prior_context = self._recall_context(symbol)
        if prior_context:
            thinker.add_thought(
                f"Memory Recall: {prior_context}",
                total_thoughts_estimate=4
            )
        
        # Step 1: Initial Observation
        price = market_data.get('price', 0)
        rsi = market_data.get('rsi', 50)
        thinker.add_thought(
            f"Analyzing {symbol}. Current Price: {price}, RSI: {rsi}.",
            total_thoughts_estimate=4
        )
        
        # Step 2: Evaluation
        if rsi > 70:
            thinker.add_thought(
                "RSI is > 70, indicating overbought conditions. Risk of reversal is high.",
                total_thoughts_estimate=4
            )
            decision = "SELL"
            confidence = "High"
        elif rsi < 30:
            thinker.add_thought(
                "RSI is < 30, indicating oversold conditions. Semantic check: Downtrend strength?",
                total_thoughts_estimate=5
            )
            
            # Step 2b: Branching (simulated logic)
            trend = market_data.get('trend', 'neutral')
            if trend == 'down':
                 thinker.add_thought(
                    "Trend is strongly Down. Oversold RSI might just indicate momentum. Caution advised.",
                    total_thoughts_estimate=5,
                    branch_id="caution_branch"
                )
                 decision = "HOLD"
                 confidence = "Medium"
            else:
                 thinker.add_thought(
                    "Trend is Neutral/Up. Oversold RSI is a good entry signal.",
                    total_thoughts_estimate=4
                )
                 decision = "BUY"
                 confidence = "High"
        else:
            thinker.add_thought(
                "RSI is neutral (30-70). No clear momentum signal from this indicator.",
                total_thoughts_estimate=4
            )
            decision = "HOLD"
            confidence = "Low"
            
        # Step 3: Conclusion
        thinker.add_thought(
            f"Final Recommendation: {decision} with {confidence} confidence.",
            total_thoughts_estimate=4,
            next_needed=False
        )
        
        # Step 4: Learn from this analysis (update memory)
        self._learn(symbol, decision, confidence, rsi)
        
        return {
            "symbol": symbol,
            "decision": decision,
            "confidence": confidence,
            "reasoning_trace": thinker.get_trajectory()
        }
    
    def _recall_context(self, symbol: str) -> str:
        """Retrieve prior knowledge about a symbol from the knowledge graph."""
        related = self.memory.get_related(symbol)
        if not related:
            return ""
        
        entity = related.get("entity", {})
        observations = entity.get("observations", [])
        
        if observations:
            # Return the most recent observations
            return f"Prior observations for {symbol}: " + "; ".join(observations[-3:])
        return ""
    
    def _learn(self, symbol: str, decision: str, confidence: str, rsi: float):
        """Store the analysis result in the knowledge graph for future recall."""
        import time
        timestamp = time.strftime("%Y-%m-%d %H:%M")
        observation = f"{decision} signal ({confidence} conf.) at RSI {rsi} on {timestamp}"
        
        # Ensure entity exists
        if symbol not in self.memory.entities:
            self.memory.create_entities([
                {"name": symbol, "entity_type": "stock", "observations": [observation]}
            ])
        else:
            self.memory.add_observations(symbol, [observation])
