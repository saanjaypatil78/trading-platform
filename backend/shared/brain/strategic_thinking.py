"""
Strategic Thinking Patterns for Trading
Each pattern represents a different reasoning approach for specific scenarios.
"""
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
from backend.shared.brain.sequential_thinking import SequentialThinker
from backend.shared.brain.memory import KnowledgeGraph

class ThinkingStrategy(Enum):
    """Available thinking strategies for different trading scenarios."""
    ENTRY_ANALYSIS = "entry_analysis"
    RISK_ASSESSMENT = "risk_assessment"
    REGIME_DETECTION = "regime_detection"
    PORTFOLIO_REBALANCE = "portfolio_rebalance"
    EARNINGS_PLAY = "earnings_play"


class StrategicThinker:
    """
    Orchestrates different thinking patterns based on the trading scenario.
    Each strategy follows a distinct chain-of-thought flow.
    """
    
    def __init__(self, memory: Optional[KnowledgeGraph] = None):
        self.memory = memory or KnowledgeGraph()
        self._strategies: Dict[ThinkingStrategy, Callable] = {
            ThinkingStrategy.ENTRY_ANALYSIS: self._entry_analysis_chain,
            ThinkingStrategy.RISK_ASSESSMENT: self._risk_assessment_chain,
            ThinkingStrategy.REGIME_DETECTION: self._regime_detection_chain,
            ThinkingStrategy.PORTFOLIO_REBALANCE: self._portfolio_rebalance_chain,
            ThinkingStrategy.EARNINGS_PLAY: self._earnings_play_chain,
        }
    
    def think(self, strategy: ThinkingStrategy, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a specific thinking strategy with the given context.
        """
        if strategy not in self._strategies:
            raise ValueError(f"Unknown strategy: {strategy}")
        
        return self._strategies[strategy](context)
    
    # =========================================================================
    # STRATEGY 1: Entry Analysis (Buy/Sell/Hold)
    # =========================================================================
    def _entry_analysis_chain(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Multi-indicator entry analysis with confirmation logic."""
        thinker = SequentialThinker()
        symbol = ctx.get("symbol", "UNKNOWN")
        
        # Step 1: Recall Memory
        prior = self._recall(symbol)
        if prior:
            thinker.add_thought(f"Memory: {prior}", total_thoughts_estimate=6)
        
        # Step 2: Primary Indicator (RSI)
        rsi = ctx.get("rsi", 50)
        rsi_signal = "neutral"
        if rsi > 70:
            rsi_signal = "overbought"
            thinker.add_thought(f"RSI={rsi} -> Overbought. Looking for confirmation.", 6)
        elif rsi < 30:
            rsi_signal = "oversold"
            thinker.add_thought(f"RSI={rsi} -> Oversold. Potential buying opportunity.", 6)
        else:
            thinker.add_thought(f"RSI={rsi} -> Neutral zone. No strong momentum signal.", 6)
        
        # Step 3: Secondary Indicator (MACD)
        macd = ctx.get("macd", 0)
        macd_signal_line = ctx.get("macd_signal", 0)
        macd_cross = "bullish" if macd > macd_signal_line else "bearish"
        thinker.add_thought(f"MACD Cross: {macd_cross.upper()}. MACD={macd:.2f}, Signal={macd_signal_line:.2f}", 6)
        
        # Step 4: Volume Confirmation
        volume = ctx.get("volume", 0)
        avg_volume = ctx.get("avg_volume", 1)
        vol_ratio = volume / avg_volume if avg_volume else 1
        vol_confirm = vol_ratio > 1.5
        thinker.add_thought(
            f"Volume: {volume:,.0f} ({vol_ratio:.1f}x avg). {'Strong confirmation!' if vol_confirm else 'Weak volume.'}",
            6
        )
        
        # Step 5: Decision Matrix
        decision = "HOLD"
        confidence = "Low"
        
        if rsi_signal == "oversold" and macd_cross == "bullish" and vol_confirm:
            decision = "BUY"
            confidence = "High"
            thinker.add_thought("All indicators aligned bullish -> Strong BUY signal.", 6)
        elif rsi_signal == "overbought" and macd_cross == "bearish" and vol_confirm:
            decision = "SELL"
            confidence = "High"
            thinker.add_thought("All indicators aligned bearish -> Strong SELL signal.", 6)
        elif rsi_signal == "oversold" and macd_cross == "bullish":
            decision = "BUY"
            confidence = "Medium"
            thinker.add_thought("RSI+MACD bullish but volume weak -> Moderate BUY.", 6, branch_id="weak_volume")
        elif rsi_signal == "overbought" and macd_cross == "bearish":
            decision = "SELL"
            confidence = "Medium"
            thinker.add_thought("RSI+MACD bearish but volume weak -> Moderate SELL.", 6, branch_id="weak_volume")
        else:
            thinker.add_thought("Mixed signals -> No clear edge. HOLD.", 6)
        
        # Step 6: Final Recommendation
        thinker.add_thought(f"DECISION: {decision} ({confidence} confidence)", 6, next_needed=False)
        
        # Learn
        self._learn(symbol, f"{decision} ({confidence})", rsi)
        
        return {
            "symbol": symbol,
            "strategy": "entry_analysis",
            "decision": decision,
            "confidence": confidence,
            "trace": thinker.get_trajectory()
        }
    
    # =========================================================================
    # STRATEGY 2: Risk Assessment (Position Sizing)
    # =========================================================================
    def _risk_assessment_chain(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate position size based on risk parameters."""
        thinker = SequentialThinker()
        
        account_size = ctx.get("account_size", 10000)
        risk_percent = ctx.get("risk_percent", 2)  # Default 2% risk
        entry_price = ctx.get("entry_price", 100)
        stop_loss = ctx.get("stop_loss", 95)
        
        # Step 1: Calculate risk amount
        risk_amount = account_size * (risk_percent / 100)
        thinker.add_thought(f"Account: ${account_size:,.0f}. Risk {risk_percent}% = ${risk_amount:.2f}", 4)
        
        # Step 2: Calculate per-share risk
        per_share_risk = entry_price - stop_loss
        thinker.add_thought(f"Entry: ${entry_price}, Stop: ${stop_loss}. Risk/share: ${per_share_risk:.2f}", 4)
        
        # Step 3: Calculate position size
        if per_share_risk <= 0:
            thinker.add_thought("ERROR: Stop loss must be below entry price!", 4, branch_id="error")
            return {"error": "Invalid stop loss", "trace": thinker.get_trajectory()}
        
        position_size = int(risk_amount / per_share_risk)
        position_value = position_size * entry_price
        thinker.add_thought(f"Position: {position_size} shares (${position_value:,.0f})", 4)
        
        # Step 4: Sanity check
        if position_value > account_size * 0.25:
            thinker.add_thought(
                f"WARNING: Position is {(position_value/account_size)*100:.0f}% of account. Consider reducing.",
                4,
                branch_id="warning"
            )
        else:
            thinker.add_thought("Position size within acceptable range.", 4, next_needed=False)
        
        return {
            "strategy": "risk_assessment",
            "position_size": position_size,
            "position_value": position_value,
            "risk_amount": risk_amount,
            "trace": thinker.get_trajectory()
        }
    
    # =========================================================================
    # STRATEGY 3: Market Regime Detection
    # =========================================================================
    def _regime_detection_chain(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Detect current market regime (Bull/Bear/Sideways)."""
        thinker = SequentialThinker()
        
        # Step 1: Moving Average Analysis
        price = ctx.get("price", 100)
        sma_50 = ctx.get("sma_50", 100)
        sma_200 = ctx.get("sma_200", 100)
        
        thinker.add_thought(f"Price: ${price}, SMA50: ${sma_50}, SMA200: ${sma_200}", 4)
        
        # Step 2: Trend Detection
        if sma_50 > sma_200 and price > sma_50:
            regime = "BULL"
            thinker.add_thought("Golden Cross + Price above MAs -> BULL Market", 4)
        elif sma_50 < sma_200 and price < sma_50:
            regime = "BEAR"
            thinker.add_thought("Death Cross + Price below MAs -> BEAR Market", 4)
        else:
            regime = "SIDEWAYS"
            thinker.add_thought("MAs intertwined or price between them -> SIDEWAYS/Choppy", 4)
        
        # Step 3: Volatility Check
        atr = ctx.get("atr", 2)
        atr_percent = (atr / price) * 100
        volatility = "HIGH" if atr_percent > 3 else "LOW" if atr_percent < 1 else "NORMAL"
        thinker.add_thought(f"ATR: ${atr:.2f} ({atr_percent:.1f}% of price) -> {volatility} volatility", 4)
        
        # Step 4: Strategy Recommendation
        if regime == "BULL" and volatility != "HIGH":
            recommendation = "Favor long positions, trend-following strategies."
        elif regime == "BEAR" and volatility != "HIGH":
            recommendation = "Favor short positions or stay cash."
        elif volatility == "HIGH":
            recommendation = "High volatility: Reduce position sizes, use wider stops."
        else:
            recommendation = "Range-bound: Mean reversion strategies may work."
        
        thinker.add_thought(f"Regime: {regime} | Volatility: {volatility} | {recommendation}", 4, next_needed=False)
        
        return {
            "strategy": "regime_detection",
            "regime": regime,
            "volatility": volatility,
            "recommendation": recommendation,
            "trace": thinker.get_trajectory()
        }
    
    # =========================================================================
    # STRATEGY 4: Portfolio Rebalancing
    # =========================================================================
    def _portfolio_rebalance_chain(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze portfolio drift and recommend rebalancing actions."""
        thinker = SequentialThinker()
        
        holdings = ctx.get("holdings", {})  # {"AAPL": 5000, "GOOGL": 3000, ...}
        targets = ctx.get("targets", {})    # {"AAPL": 40, "GOOGL": 30, ...} in %
        
        total = sum(holdings.values())
        thinker.add_thought(f"Portfolio Value: ${total:,.0f}", 5)
        
        # Step 1: Calculate current allocations
        current = {k: (v / total) * 100 for k, v in holdings.items()}
        
        # Step 2: Calculate drift
        actions = []
        for symbol, target_pct in targets.items():
            current_pct = current.get(symbol, 0)
            drift = current_pct - target_pct
            if abs(drift) > 5:  # 5% threshold
                action = "SELL" if drift > 0 else "BUY"
                amount = abs(drift / 100) * total
                actions.append({"symbol": symbol, "action": action, "amount": amount})
                thinker.add_thought(
                    f"{symbol}: Current {current_pct:.1f}% vs Target {target_pct}% -> {action} ${amount:,.0f}",
                    5
                )
        
        # Step 3: Summary
        if actions:
            thinker.add_thought(f"Rebalancing needed: {len(actions)} trades required.", 5, next_needed=False)
        else:
            thinker.add_thought("Portfolio is within tolerance. No rebalancing needed.", 5, next_needed=False)
        
        return {
            "strategy": "portfolio_rebalance",
            "actions": actions,
            "trace": thinker.get_trajectory()
        }
    
    # =========================================================================
    # STRATEGY 5: Earnings Play Analysis
    # =========================================================================
    def _earnings_play_chain(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze earnings event for options or directional play."""
        thinker = SequentialThinker()
        symbol = ctx.get("symbol", "UNKNOWN")
        
        # Step 1: Recall historical earnings behavior
        prior = self._recall(symbol)
        if prior:
            thinker.add_thought(f"Historical Pattern: {prior}", 5)
        
        # Step 2: IV Analysis (Implied Volatility)
        iv = ctx.get("iv", 50)
        iv_rank = ctx.get("iv_rank", 50)  # 0-100
        thinker.add_thought(f"IV: {iv}%, IV Rank: {iv_rank}%", 5)
        
        # Step 3: Expected Move
        expected_move = ctx.get("expected_move", 5)  # percentage
        thinker.add_thought(f"Expected Move: +/-{expected_move}%", 5)
        
        # Step 4: Strategy Selection
        if iv_rank > 70:
            strategy = "SELL PREMIUM"
            rationale = "High IV Rank -> Options are expensive. Sell strangles/straddles."
            thinker.add_thought(f"High IV -> {strategy}. {rationale}", 5)
        elif iv_rank < 30:
            strategy = "BUY PREMIUM"
            rationale = "Low IV Rank -> Options are cheap. Buy calls/puts if directional bias."
            thinker.add_thought(f"Low IV -> {strategy}. {rationale}", 5)
        else:
            strategy = "DIRECTIONAL"
            rationale = "Neutral IV. Consider directional bias or skip."
            thinker.add_thought(f"Neutral IV -> {strategy}. {rationale}", 5)
        
        thinker.add_thought(f"Earnings Play: {strategy}", 5, next_needed=False)
        
        return {
            "symbol": symbol,
            "strategy_name": "earnings_play",
            "recommended_strategy": strategy,
            "rationale": rationale,
            "trace": thinker.get_trajectory()
        }
    
    # =========================================================================
    # Memory Helpers
    # =========================================================================
    def _recall(self, symbol: str) -> str:
        related = self.memory.get_related(symbol)
        if not related:
            return ""
        observations = related.get("entity", {}).get("observations", [])
        return "; ".join(observations[-3:]) if observations else ""
    
    def _learn(self, symbol: str, decision: str, indicator_value: float):
        import time
        ts = time.strftime("%Y-%m-%d %H:%M")
        obs = f"{decision} at indicator={indicator_value} on {ts}"
        if symbol not in self.memory.entities:
            self.memory.create_entities([{"name": symbol, "entity_type": "stock", "observations": [obs]}])
        else:
            self.memory.add_observations(symbol, [obs])
