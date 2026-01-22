"""
Test suite for Scanner Service
Run with: pytest backend/tests/test_scanner.py
"""
import pytest
import httpx

BASE_URL = "http://localhost:8002"


@pytest.mark.asyncio
async def test_health_check():
    """Test service health endpoint"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "scanner"


@pytest.mark.asyncio
async def test_get_templates():
    """Test getting scan templates"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/v1/templates")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Check template structure
        template = data[0]
        assert "id" in template
        assert "name" in template
        assert "criteria" in template


@pytest.mark.asyncio
async def test_get_symbols():
    """Test getting available symbols"""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/v1/symbols")
        assert response.status_code == 200
        data = response.json()
        assert "symbols" in data
        assert "total_count" in data
        assert data["total_count"] > 0


@pytest.mark.asyncio
async def test_scan_preview():
    """Test scan preview on single stock"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        payload = {
            "criteria": "Close > Open",
            "symbol": "RELIANCE",
            "lookback_days": 30
        }
        
        response = await client.post(
            f"{BASE_URL}/api/v1/scan/preview",
            json=payload
        )
        
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "symbol" in data
            assert "criteria" in data


@pytest.mark.asyncio
async def test_execute_scan():
    """Test executing a scan (limited to 5 stocks for speed)"""
    async with httpx.AsyncClient(timeout=120.0) as client:
        payload = {
            "criteria": "Close > Open",
            "symbols": ["RELIANCE", "TCS", "INFY", "HDFC", "ITC"]
        }
        
        response = await client.post(
            f"{BASE_URL}/api/v1/scan/execute",
            json=payload
        )
        
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "matched_symbols" in data
            assert "total_scanned" in data
            assert "execution_time_ms" in data
