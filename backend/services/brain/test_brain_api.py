"""
Tests for the AI Brain Service API.
"""
from fastapi.testclient import TestClient
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))

from backend.services.brain.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["model"]["model"] == "glm-4.7"

def test_model_endpoint():
    response = client.get("/model")
    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "glm-4.7"

def test_entry_analysis_buy():
    payload = {
        "symbol": "NVDA",
        "rsi": 25,          # Oversold
        "macd": 5,
        "macd_signal": 3,   # Bullish cross
        "volume": 50000000,
        "avg_volume": 30000000  # High volume
    }
    response = client.post("/entry-analysis", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["result"]["decision"] == "BUY"
    assert data["result"]["confidence"] == "High"
    assert len(data["trace"]) > 0

def test_entry_analysis_sell():
    payload = {
        "symbol": "AAPL",
        "rsi": 75,          # Overbought
        "macd": 3,
        "macd_signal": 5,   # Bearish cross
        "volume": 100000000,
        "avg_volume": 50000000
    }
    response = client.post("/entry-analysis", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["result"]["decision"] == "SELL"

def test_risk_assessment():
    payload = {
        "account_size": 100000,
        "risk_percent": 2,
        "entry_price": 200,
        "stop_loss": 190
    }
    response = client.post("/risk-assessment", json=payload)
    assert response.status_code == 200
    data = response.json()
    # Risk = 2000, Per share risk = 10 -> Position = 200 shares
    assert data["result"]["position_size"] == 200
    assert data["result"]["position_value"] == 40000

def test_regime_detection_bull():
    payload = {
        "price": 500,
        "sma_50": 480,
        "sma_200": 400,
        "atr": 5
    }
    response = client.post("/regime-detection", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["result"]["regime"] == "BULL"

def test_portfolio_rebalance():
    payload = {
        "holdings": {"AAPL": 30000, "GOOGL": 10000, "MSFT": 10000},
        "targets": {"AAPL": 33, "GOOGL": 33, "MSFT": 34}
    }
    response = client.post("/portfolio-rebalance", json=payload)
    assert response.status_code == 200
    data = response.json()
    # GOOGL is underweight (20% vs 33%), should recommend BUY
    assert len(data["result"]["actions"]) > 0

def test_earnings_play():
    payload = {
        "symbol": "TSLA",
        "iv": 90,
        "iv_rank": 80,
        "expected_move": 10
    }
    response = client.post("/earnings-play", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["result"]["recommended_strategy"] == "SELL PREMIUM"

def test_memory_flow():
    # Learn something
    response = client.post("/memory/learn?entity_name=TEST_STOCK&observation=Test%20observation")
    assert response.status_code == 200
    
    # Retrieve it
    response = client.get("/memory/TEST_STOCK")
    assert response.status_code == 200
    data = response.json()
    assert "Test observation" in data["entity"]["observations"]
