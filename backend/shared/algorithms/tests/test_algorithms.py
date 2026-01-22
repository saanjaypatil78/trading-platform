"""
Unit Tests for FACTRADE Algorithm Modules
"""

import pytest
import sys
import os

# Add paths for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from backend.shared.algorithms.tokenomics import (
    calculate_tax_amount,
    calculate_tax_distribution,
    calculate_referral_rewards,
    TransactionType,
)

from backend.shared.algorithms.staking import (
    calculate_dynamic_apy,
    calculate_stake_rewards,
    calculate_compound_value,
    LockPeriod,
)


class TestTokenomics:
    """Tests for tokenomics module"""
    
    def test_calculate_tax_amount_sell(self):
        """Test sell tax calculation (2% = 200 bps)"""
        amount = 1000
        tax = calculate_tax_amount(amount, TransactionType.SELL)
        assert tax == 20.0  # 2% of 1000
    
    def test_calculate_tax_amount_buy(self):
        """Test buy tax calculation (2%)"""
        amount = 5000
        tax = calculate_tax_amount(amount, TransactionType.BUY)
        assert tax == 100.0  # 2% of 5000
    
    def test_calculate_tax_amount_transfer(self):
        """Test transfer tax calculation (1% = 100 bps)"""
        amount = 1000
        tax = calculate_tax_amount(amount, TransactionType.TRANSFER)
        assert tax == 10.0  # 1% of 1000
    
    def test_calculate_tax_distribution(self):
        """Test tax distribution breakdown (25% each)"""
        tax_amount = 100
        result = calculate_tax_distribution(tax_amount)
        
        assert result is not None
        assert result.marketing == 25.0
        assert result.treasury == 25.0
        assert result.burn == 25.0
        assert result.holder_rewards == 25.0
        assert result.total == 100.0
    
    def test_calculate_referral_rewards(self):
        """Test 5-tier referral rewards calculation"""
        trading_volume = 10000
        result = calculate_referral_rewards(trading_volume)
        
        assert result is not None
        # Total pool = 25% of 10000 = 2500
        assert result.total == 2500.0
        
        # Level 1 gets 40% of 2500 = 1000
        assert result.level1 == 1000.0
        # Level 2 gets 20% = 500
        assert result.level2 == 500.0
        # Level 3 gets 15% = 375
        assert result.level3 == 375.0
        # Level 4 gets 15% = 375
        assert result.level4 == 375.0
        # Level 5 gets 10% = 250
        assert result.level5 == 250.0


class TestStaking:
    """Tests for staking module"""
    
    def test_calculate_dynamic_apy_low_tvl(self):
        """Test APY at low TVL (should be max)"""
        apy = calculate_dynamic_apy(5)  # 5M TVL
        assert apy == 25.0  # Max APY
    
    def test_calculate_dynamic_apy_medium_tvl(self):
        """Test APY at medium TVL"""
        apy = calculate_dynamic_apy(75)  # 75M TVL
        assert apy == 18.0  # 50-100M range
    
    def test_calculate_dynamic_apy_high_tvl(self):
        """Test APY at high TVL (should be base)"""
        apy = calculate_dynamic_apy(600)  # 600M TVL
        assert apy == 12.0  # Base APY
    
    def test_calculate_stake_rewards_30_days(self):
        """Test stake rewards for 30-day lock"""
        result = calculate_stake_rewards(1000, LockPeriod.DAYS_30)
        
        assert result.principal == 1000
        assert result.apy_used == 20.0  # 20% APR for 30-day lock
        assert result.days_staked == 30
        # Rewards = 1000 * 0.20 * (30/365) ≈ 16.44
        assert 16.0 < result.rewards < 17.0
    
    def test_calculate_stake_rewards_with_dynamic_apy(self):
        """Test stake rewards with dynamic APY based on TVL"""
        result = calculate_stake_rewards(
            1000, 
            LockPeriod.DAYS_30,
            tvl_millions=50  # 50M TVL = 18% base * 2.0 multiplier = 36%
        )
        
        # With 36% APY for 30 days:
        # Rewards = 1000 * 0.36 * (30/365) ≈ 29.59
        assert result.apy_used == 36.0
        assert 29.0 < result.rewards < 30.0
    
    def test_calculate_compound_value_daily(self):
        """Test daily compounding for 1 year"""
        final = calculate_compound_value(
            principal=1000,
            apy=20,
            days=365,
            compound_frequency=1
        )
        
        # With daily compounding at 20% APY:
        # Should be slightly more than simple interest (1200)
        assert final > 1200
        assert final < 1230  # But not too much more
    
    def test_calculate_compound_value_short_period(self):
        """Test compounding for short period"""
        final = calculate_compound_value(
            principal=1000,
            apy=20,
            days=30,
            compound_frequency=1
        )
        
        # For 30 days, should be close to simple interest
        assert 1015 < final < 1020


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
