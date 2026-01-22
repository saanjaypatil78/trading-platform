
import unittest
import sys
import os
import shutil

# Assume running from project root
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Set dummy env vars to satisfy pydantic
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("JWT_SECRET_KEY", "dummy_secret_for_tests")

from backend.services.market_data.providers.alpaca_provider import AlpacaProvider
from backend.services.reporting.pdf_generator import PDFGenerator
from backend.services.scanner.condition_parser import ConditionParser
from backend.services.backtesting.models import BacktestResult, PerformanceMetrics

class TestPivotFeatures(unittest.TestCase):
    
    def test_alpaca_import(self):
        """Verify Alpaca Provider Instantiation"""
        provider = AlpacaProvider("key", "secret")
        self.assertEqual(provider.name, "alpaca")
        print("SUCCESS: Alpaca Provider loaded.")

    def test_pdf_generation(self):
        """Test PDF Report Generation"""
        # Mock result
        result = BacktestResult(
            backtest_id="test_123",
            config={
                "symbols": ["RELIANCE"], 
                "strategy": {
                    "name": "RSI_Test",
                    "type": "rsi", 
                    "indicators": {"RSI": {"period": 14}},
                    "entry_rules": "RSI < 30",
                    "exit_rules": "RSI > 70",
                    "params": {"period": 14}
                },
                "initial_capital": 100000,
                "start_date": datetime.now().date(),
                "end_date": datetime.now().date(),
                "interval": "1d",
            },
            performance=PerformanceMetrics(
                total_return=15.5,
                total_return_percent=15.5,
                sharpe_ratio=1.2,
                win_rate=65.0,
                total_trades=20,
                winning_trades=13,
                losing_trades=7,
                profit_factor=1.5,
                max_drawdown=5.0,
                max_drawdown_percent=5.0,
                average_win=100.0,
                average_loss=50.0,
                largest_win=500.0,
                largest_loss=200.0,
                cagr=0.0
            ),
            trades=[],
            equity_curve=[],
            executed_at=datetime.now(),
            execution_time_ms=100,
            engine_used="vectorbt",
            validation_status="passed"
        )
        # Use object access for config if the model casts it, 
        # but here we passed a dict, so pydantic might cast it to BacktestConfig model.
        # However, for the PDF generator, we just need attribute access.
        # Let's ensure it ends up as an object or dict accessible in PDFGenerator.
        # The PDF Generator does: result.config.strategy.get(...)
        # If Pydantic validates it, result.config is a model.

        result.config.strategy = {"type": "RSI_Strategy"}

        path = PDFGenerator.generate_backtest_report(result, "test_report.pdf")
        self.assertTrue(os.path.exists(path))
        print(f"SUCCESS: PDF generated at {path}")
        
        # Cleanup
        if os.path.exists(path):
            os.remove(path)

    def test_scanner_parser(self):
        """Test AI Scanner Logic Parsing"""
        # 1. Natural Language
        nl_prompt = "RSI above 70"
        expr1 = ConditionParser.parse_natural_language(nl_prompt)
        self.assertEqual(expr1, "RSI > 70")
        
        # 2. JSON Logic
        json_rule = {
            "operator": "AND",
            "rules": [
                {"field": "RSI", "op": ">", "value": 70},
                {"field": "close", "op": ">", "value": "SMA_20"}
            ]
        }
        expr2 = ConditionParser.parse_json_logic(json_rule)
        self.assertEqual(expr2, "RSI > 70 and close > SMA_20")
        print(f"SUCCESS: Scanner Logic Parsed: {expr2}")

from unittest.mock import MagicMock
from datetime import datetime

if __name__ == '__main__':
    unittest.main()
