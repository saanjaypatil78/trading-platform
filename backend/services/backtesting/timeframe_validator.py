"""
Timeframe validation and warning system
Prevents users from accidentally entering HFT/scalping without understanding risks
"""
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class TimeframeValidator:
    """
    Validates timeframe selection and provides warnings for risky configurations
    """
    
    # Regulatory and practical warnings
    WARNINGS = {
        "1m": {
            "level": "CRITICAL",
            "title": "⚠️ HIGH-FREQUENCY TRADING ALERT",
            "message": """
YOU ARE ATTEMPTING 1-MINUTE TIMEFRAME TRADING

🚨 CRITICAL WARNINGS:
1. This is considered High-Frequency Trading (HFT)
2. Can be FLAGGED by exchanges and regulatory authorities
3. Requires special broker permissions in many jurisdictions
4. Very high transaction costs due to frequent trades
5. Extremely difficult to be profitable at this timeframe
6. Data quality issues can cause major losses

📋 REGULATORY RISKS (India - SEBI):
- May require algorithmic trading registration
- Subject to enhanced surveillance
- Can lead to account restrictions or penalties
- Brokers may block or limit HFT activity

💡 RECOMMENDATION:
Stick to 15-minute or higher timeframes for retail trading.
Use 1-hour or daily for most strategies.

⚖️ PREDEFINED RULEBOOK:
✓ Swing Trading: 1h, 4h, 1d timeframes
✓ Day Trading: 15m, 30m, 1h timeframes  
✗ Avoid: 1m, 5m (scalping/HFT territory)

DO YOU UNDERSTAND THE RISKS?
            """,
            "requires_acknowledgment": True
        },
        "5m": {
            "level": "WARNING",
            "title": "⚠️ SCALPING ALERT",
            "message": """
YOU ARE ATTEMPTING 5-MINUTE SCALPING

⚠️ IMPORTANT WARNINGS:
1. This is scalping - very short-term trading
2. High transaction costs eat into profits
3. Requires intense focus and screen time
4. Success rate is typically very low for retail traders
5. Data latency can cause significant slippage

💰 COST CONSIDERATIONS:
- Each trade costs 0.1-0.3% in commissions + taxes
- Need 3-5% price movement just to break even
- Most scalping attempts lose money over time

📊 STATISTICS:
- 90%+ of scalpers lose money long-term
- Requires professional infrastructure for success
- Not suitable for part-time traders

💡 RECOMMENDATION:
Consider 15-minute or 1-hour timeframes instead.
Focus on quality trades, not quantity.

⚖️  PREDEFINED RULEBOOK:
✓ Prefer: 15m, 30m, 1h for active trading
✗ Risky: 5m and below (scalping)

PROCEED WITH CAUTION
            """,
            "requires_acknowledgment": True
        }
    }
    
    @staticmethod
    def validate_timeframe(interval: str) -> tuple[bool, Dict | None]:
        """
        Validate timeframe and return warning if applicable
        
        Returns:
            (is_valid, warning_dict or None)
        """
        # Check if warning exists for this timeframe
        if interval in TimeframeValidator.WARNINGS:
            warning = TimeframeValidator.WARNINGS[interval]
            logger.warning(
                f"User attempting {interval} timeframe - "
                f"{warning['level']} warning issued"
            )
            return False, warning
        
        # Acceptable timeframes
        return True, None
    
    @staticmethod
    def get_recommended_timeframes() -> Dict[str, str]:
        """Get recommended timeframes with descriptions"""
        return {
            "1h": "✅ RECOMMENDED - Best for swing trading, good data quality",
            "4h": "✅ RECOMMENDED - Excellent for part-time traders",
            "1d": "✅ RECOMMENDED - Best for long-term strategies, low costs",
            "15m": "⚠️ ACCEPTABLE - Active day trading, requires attention",
            "30m": "⚠️ ACCEPTABLE - Day trading, moderate frequency",
            "2h": "✅ RECOMMENDED - Good balance of frequency and reliability",
            "5m": "❌ NOT RECOMMENDED - Scalping, very high risk",
            "1m": "❌ PROHIBITED - HFT territory, can be flagged"
        }
    
    @staticmethod
    def calculate_estimated_costs(
        interval: str,
        days: int = 30
    ) -> Dict:
        """
        Calculate estimated trading costs for a timeframe
        Helps users understand the financial impact
        """
        # Average trades per day for each timeframe
        trades_per_day = {
            "1m": 100,   # Extreme HFT
            "5m": 30,    # Scalping
            "15m": 10,   # Active day trading
            "30m": 5,    # Moderate day trading
            "1h": 2,     # Swing/position trading
            "4h": 1,     # Position trading
            "1d": 0.5,   # Long-term trading
        }
        
        avg_trades = trades_per_day.get(interval, 2) * days
        commission_per_trade = 0.001  # 0.1%
        min_profit_needed = 0.025  # Need 2.5% just to break even (both sides)
        
        return {
            "estimated_trades_per_month": int(avg_trades),
            "commission_rate": commission_per_trade * 100,
            "minimum_profit_per_trade_percent": min_profit_needed * 100,
            "warning": f"Need ~{min_profit_needed * 100}% price movement per trade to break even"
        }


class RiskAcknowledgment:
    """
    Tracks user acknowledgments of trading risks
    Required before allowing sub-5min timeframes
    """
    
    acknowledged_risks: Dict[str, bool] = {}
    
    @staticmethod
    def require_acknowledgment(user_id: str, interval: str) -> bool:
        """
        Check if user has acknowledged risks for this timeframe
        """
        key = f"{user_id}:{interval}"
        return RiskAcknowledgment.acknowledged_risks.get(key, False)
    
    @staticmethod
    async def record_acknowledgment(
        user_id: str,
        interval: str,
        acknowledged: bool
    ) -> None:
        """Record user's risk acknowledgment"""
        key = f"{user_id}:{interval}"
        RiskAcknowledgment.acknowledged_risks[key] = acknowledged
        
        if acknowledged:
            logger.warning(
                f"User {user_id} acknowledged risks for {interval} timeframe. "
                f"Proceeding at their own risk."
            )
