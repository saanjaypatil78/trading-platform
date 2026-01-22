"""
Test suite for Market Data Service
Run with: pytest backend/tests/test_market_data.py
"""
import pytest
import httpx
from datetime import datetime

BASE_URL = "http://localhost:8001"


@pytest.mark.asyncio
async def test_health_check():
    """Test service health endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "market-data"


@pytest.mark.asyncio
async def test_get_quote():
    """Test getting real-time quote"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{BASE_URL}/api/v1/quote/RELIANCE")
        
        # Should succeed or return 404 if no provider available
        assert response.status_code in [200, 404, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert "symbol" in data
            assert "last_price" in data
            assert data["symbol"] == "RELIANCE"


@pytest.mark.asyncio
async def test_provider_health():
    """Test provider health check"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/v1/providers/health")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        
        # Should have at least one provider
        assert len(data) > 0
        
        for provider in data:
            assert "provider" in provider
            assert "is_available" in provider


@pytest.mark.asyncio
async def test_get_ohlcv():
    """Test getting OHLCV data"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/ohlcv/TCS",
            params={"interval": "1d", "limit": 10}
        )
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            assert len(data) <= 10


@pytest.mark.asyncio
async def test_search_symbols():
    """Test symbol search"""
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(
            f"{BASE_URL}/api/v1/search",
            params={"q": "RELIANCE"}
        )
        
        # May return empty if providers don't support search
        assert response.status_code in [200, 404]
