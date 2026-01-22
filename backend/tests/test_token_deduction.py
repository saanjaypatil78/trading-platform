
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Assume running from project root
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from backend.shared.algorithms.tokenomics import FactradeToken
# usage_tracker imports 'state' which needs mocking
with patch('backend.services.auth.usage_tracker.state') as mock_state:
    from backend.services.auth.usage_tracker import UsageTracker

class TestTokenDeduction(unittest.TestCase):
    
    def test_factrade_costs(self):
        """Verify defined costs match pricing strategy"""
        self.assertEqual(FactradeToken.get_required_credits("HISTORICAL_DATA"), 1.0)
        self.assertEqual(FactradeToken.get_required_credits("LIVE_TRADE"), 0.05)

    def test_deduct_credits_success(self):
        """Test successful deduction balance math"""
        new_bal = FactradeToken.deduct_credits(10.0, "HISTORICAL_DATA")
        self.assertEqual(new_bal, 9.0)

    def test_deduct_credits_fail(self):
        """Test insufficient funds"""
        with self.assertRaises(ValueError):
            FactradeToken.deduct_credits(0.5, "HISTORICAL_DATA") # Need 1.0

    @patch('backend.services.auth.usage_tracker.state')
    def test_usage_tracker_debit(self, mock_state):
        """Test UsageTracker using mocked Redis state"""
        # Mock get_balance
        mock_state.hget.return_value = "10.0" 
        
        # Perform Debit
        success = UsageTracker.debit_user("test_user", "HISTORICAL_DATA")
        
        self.assertTrue(success)
        # Verify it set the new balance (9.0)
        mock_state.hset.assert_called_with(
            "user_wallets", 
            "wallet:fact_balance:test_user", 
            9.0
        )
        print("SUCCESS: UsageTracker correctly deducted tokens.")

if __name__ == '__main__':
    unittest.main()
