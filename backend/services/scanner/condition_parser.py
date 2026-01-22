
import logging
from typing import Dict, Any, List, Optional
import re

logger = logging.getLogger(__name__)

class ConditionParser:
    """
    Parses complex scanner conditions from:
    1. Drag-n-Drop JSON (React Flow style)
    2. AI Text Prompts (Natural Language)
    """
    
    @staticmethod
    def parse_json_logic(rule_group: Dict[str, Any]) -> str:
        """
        Convert JSON rule group to Python expression string.
        Example: {"operator": "AND", "rules": [{"field": "RSI", "op": ">", "value": 70}]}
        Returns: "(RSI > 70)"
        """
        operator = rule_group.get("operator", "AND").upper()
        rules = rule_group.get("rules", [])
        
        expressions = []
        for rule in rules:
            if "rules" in rule:
                # Nested Group
                expressions.append(f"({ConditionParser.parse_json_logic(rule)})")
            else:
                # Leaf Condition
                field = rule.get("field")
                op = rule.get("op")
                val = rule.get("value")
                expressions.append(f"{field} {op} {val}")
        
        joiner = " and " if operator == "AND" else " or "
        return joiner.join(expressions)

    @staticmethod
    def parse_natural_language(prompt: str) -> str:
        """
        Heuristic parsing of text prompts to conditions.
        (In production, this would call an LLM).
        """
        prompt = prompt.lower()
        
        # Regex heuristics for common patterns
        # "RSI above 70" -> "RSI > 70"
        if "rsi" in prompt:
            match = re.search(r"rsi\s+(above|greater than|over|crosses above)\s+(\d+)", prompt)
            if match:
                val = match.group(2)
                return f"RSI > {val}"
            
            match = re.search(r"rsi\s+(below|less than|under|crosses below)\s+(\d+)", prompt)
            if match:
                val = match.group(2)
                return f"RSI < {val}"
                
        if "sma" in prompt:
            # "Price above SMA 20"
            match = re.search(r"price\s+(above|below)\s+sma\s*(\d+)", prompt)
            if match:
                direction = ">" if match.group(1) == "above" else "<"
                period = match.group(2)
                return f"close {direction} SMA_{period}"
                
        return "True" # Fallback

    @staticmethod
    def validate_safety(expression: str) -> bool:
        """Ensure no malicious code injection in expression"""
        allowed_tokens = {
            "RSI", "SMA", "EMA", "MACD", "close", "open", "high", "low", "volume",
            "and", "or", "not", ">", "<", ">=", "<=", "==", "!=", "(", ")",
            "0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "."
        }
        # Very basic sanitizer (improve for prod)
        # Check if all words are allowed or numbers
        clean = re.sub(r"[0-9\.]+|SMA_\d+|EMA_\d+", "", expression) # Remove numbers and indicators
        words = re.findall(r"[a-zA-Z_]+", clean)
        
        for w in words:
            if w not in allowed_tokens and not w.startswith("SMA_") and not w.startswith("EMA_"):
                logger.warning(f"Unsafe token detected: {w}")
                return False
        return True
