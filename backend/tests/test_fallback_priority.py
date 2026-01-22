
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Assume running from project root
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'backend'))

# Pre-set valid env vars for ALL providers
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["REDIS_URL"] = "redis://localhost:6379"
os.environ["JWT_SECRET_KEY"] = "dummy_secret"

# Keys for providers to ensure they are enabled
os.environ["YAHOO_FINANCE_ENABLED"] = "true"
os.environ["ALPHAVANTAGE_API_KEY"] = "dummy_av"
os.environ["UPSTOX_API_KEY"] = "dummy_upstox"
os.environ["ALPACA_API_KEY"] = "dummy_alpaca"
os.environ["ALPACA_API_SECRET"] = "dummy_secret"
os.environ["ZERODHA_API_KEY"] = "dummy_zerodha"

# Force reload of config and aggregator to pick up env vars
import importlib
import backend.shared.config
importlib.reload(backend.shared.config)
from backend.services.market_data import aggregator
importlib.reload(aggregator)

from backend.services.market_data.aggregator import MarketDataAggregator

class TestFallbackPriority(unittest.TestCase):
    
    def test_initialization_order(self):
        """Verify providers are initialized in Yahoo -> AV -> Upstox -> Alpaca -> Zerodha order"""
        
        # Instantiate aggregator (will use reloaded settings)
        agg = MarketDataAggregator()
        
        provider_names = [p.name for p in agg.providers]
        print(f"Initialized Providers: {provider_names}")
        
        expected_order = ['yahoo', 'alphavantage', 'upstox', 'alpaca', 'zerodha']
        
        # Check if the sequence appears in the list
        # Note: names might vary slightly based on implementation (e.g. "yahoo_finance" vs "yahoo")
        # Let's normalize or check indices
        
        # Map class names or .name attributes from the implementation
        # In creating providers, I named them: "alphavantage", "zerodha", "alpaca"
        # YahooFinanceProvider usually names itself "yahoo" or similar. Checking file...
        
        # Let's verify index of each is increasing
        # Names from implementations:
        # Yahoo -> "YahooFinance" (from yahoo_provider.py)
        # Upstox -> "Upstox" (likely) or "upstox" (I checked upstox_provider.py earlier, let's assume Upstox or check list)
        # The failed test output showed: ['YahooFinance', 'Upstox'] so Upstox is 'Upstox'.
        # AlphaVantage -> "alphavantage" (from my create command)
        # Alpaca -> "alpaca" (from my create command)
        # Zerodha -> "zerodha" (from my create command)
        
        try:
            # Helper to find index case-insensitively or mapped
            provider_names = [p.name for p in agg.providers]
            print(f"Initialized Providers: {provider_names}")
            names_lower = [n.lower() for n in provider_names]
            
            yahoo_idx = names_lower.index('yahoofinance')
            av_idx = names_lower.index('alphavantage')
            upstox_idx = names_lower.index('upstox')
            alpaca_idx = names_lower.index('alpaca')
            zerodha_idx = names_lower.index('zerodha')
            
            self.assertTrue(yahoo_idx < av_idx, "Yahoo should be before AlphaVantage")
            self.assertTrue(av_idx < upstox_idx, "AlphaVantage should be before Upstox")
            self.assertTrue(upstox_idx < alpaca_idx, "Upstox should be before Alpaca")
            self.assertTrue(alpaca_idx < zerodha_idx, "Alpaca should be before Zerodha")
            
            print("SUCCESS: Provider Fallback Priority Verified!")
            
        except ValueError as e:
            self.fail(f"Missing provider in list: {e}. List was: {provider_names}")

if __name__ == '__main__':
    unittest.main()
