from fastapi.testclient import TestClient
import sys
import os

# Add path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from backend.services.defi.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_stake_calculation():
    payload = {
        "principal": 1000,
        "lock_period": "DAYS_30",
        "tvl_millions": 50
    }
    response = client.post("/api/v1/defi/stake", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["principal"] == 1000
    # 50M TVL -> 18% base * 2.0 mul -> 36% APY
    assert data["apy_used"] == 36.0
    assert data["days_staked"] == 30

def test_referral_calculation():
    payload = {
        "trading_volume": 10000
    }
    response = client.post("/api/v1/defi/referral", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2500.0  # 25% of 10000
    assert data["level1"] == 1000.0 # 40% of 2500

def test_tax_calculation():
    payload = {
        "amount": 1000,
        "transaction_type": "sell"
    }
    response = client.post("/api/v1/defi/tax", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["tax_amount"] == 20.0 # 2% of 1000
    assert data["distribution"]["marketing"] == 5.0 # 25% of 20
