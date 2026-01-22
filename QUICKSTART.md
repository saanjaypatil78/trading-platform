# Trading Platform - Quick Start Guide

## Prerequisites

- Docker Desktop (Windows)
- Python 3.11+ (for local development)
- Node.js 20+ (for frontend, later)
- Git

---

## Step 1: Clone and Setup

```powershell
# Navigate to project
cd C:\Users\Asus\.gemini\antigravity\scratch\trading-platform

# Copy environment template
copy .env.example .env
```

## Step 2: Configure Environment

Edit `.env` file and add your API keys:

```env
# Required for market data
RAPIDAPI_KEY=your_rapidapi_key_here
FINNHUB_API_KEY=your_finnhub_key_here

# Database (use defaults for local dev)
POSTGRES_PASSWORD=postgres123
JWT_SECRET_KEY=change_this_to_random_secret_key

# Other services use defaults
```

**Get API Keys**:
- RapidAPI: https://rapidapi.com/indian-api-hub/api/indian-stock-exchange
- Finnhub: https://finnhub.io (free tier available)

## Step 3: Start All Services

```powershell
# Start all services with Docker Compose
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

**Services Running**:
- PostgreSQL + TimescaleDB: `localhost:5432`
- Redis: `localhost:6379`
- RabbitMQ: `localhost:5672` (Management UI: `localhost:15672`)
- Market Data API: `localhost:8001`
- Scanner API: `localhost:8002`
- WebSocket: `localhost:8003`
- Prometheus: `localhost:9090`
- Grafana: `localhost:3001`

---

## Step 4: Test APIs

### Test Market Data Service

```powershell
# Health check
curl http://localhost:8001/health

# Get real-time quote
curl http://localhost:8001/api/v1/quote/RELIANCE

# Get OHLCV data
curl "http://localhost:8001/api/v1/ohlcv/TCS?interval=1d&limit=50"

# Check provider health
curl http://localhost:8001/api/v1/providers/health
```

### Test Scanner Service

```powershell
# Get predefined templates
curl http://localhost:8002/api/v1/templates

# Get available symbols
curl http://localhost:8002/api/v1/symbols

# Preview scan on single stock
curl -X POST http://localhost:8002/api/v1/scan/preview -H "Content-Type: application/json" -d "{\"criteria\": \"RSI(14) > 70\", \"symbol\": \"RELIANCE\"}"

# Execute full scan (RSI oversold)
curl -X POST http://localhost:8002/api/v1/scan/execute -H "Content-Type: application/json" -d "{\"criteria\": \"RSI(14) < 30\"}"
```

### Test WebSocket Service

Create `test-websocket.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <title>WebSocket Test</title>
</head>
<body>
    <h1>Trading Platform WebSocket Test</h1>
    <div id="status">Disconnected</div>
    <div id="messages"></div>
    
    <button onclick="subscribe('RELIANCE')">Subscribe to RELIANCE</button>
    <button onclick="unsubscribe('RELIANCE')">Unsubscribe from RELIANCE</button>
    
    <script>
        const ws = new WebSocket('ws://localhost:8003/ws');
        const messagesDiv = document.getElementById('messages');
        const statusDiv = document.getElementById('status');
        
        ws.onopen = () => {
            statusDiv.innerText = 'Connected';
            statusDiv.style.color = 'green';
        };
        
        ws.onclose = () => {
            statusDiv.innerText = 'Disconnected';
            statusDiv.style.color = 'red';
        };
        
        ws.onmessage = (event) => {
            const msg = JSON.parse(event.data);
            const msgEl = document.createElement('div');
            msgEl.innerText = JSON.stringify(msg, null, 2);
            messagesDiv.insertBefore(msgEl, messagesDiv.firstChild);
        };
        
        function subscribe(symbol) {
            ws.send(JSON.stringify({action: 'subscribe', symbol: symbol}));
        }
        
        function unsubscribe(symbol) {
            ws.send(JSON.stringify({action: 'unsubscribe', symbol: symbol}));
        }
    </script>
</body>
</html>
```

Open in browser: `test-websocket.html`

---

## Step 5: View Logs and Monitoring

```powershell
# View specific service logs
docker-compose logs -f market-data-service
docker-compose logs -f scanner-service
docker-compose logs -f websocket-service

# Access Grafana (monitoring dashboards)
# Open browser: http://localhost:3001
# Default credentials: admin/admin

# Access RabbitMQ Management
# Open browser: http://localhost:15672
# Default credentials: guest/guest
```

---

## Troubleshooting

### Services won't start
```powershell
# Check Docker is running
docker ps

# Reset everything
docker-compose down -v
docker-compose up -d
```

### API returns 404 or errors
```powershell
# Check service logs
docker-compose logs market-data-service

# Verify environment variables
docker-compose exec market-data-service env | grep API
```

### No data from APIs
- Verify API keys in `.env` are valid
- Yahoo Finance fallback should work without keys
- Check provider health: `curl http://localhost:8001/api/v1/providers/health`

### Database connection errors
```powershell
# Reset database
docker-compose down -v
docker-compose up -d postgres
# Wait 10 seconds
docker-compose up -d
```

---

## Stop Services

```powershell
# Stop all services
docker-compose down

# Stop and remove all data
docker-compose down -v
```

---

## Next Steps

1. **Explore API Documentation**: 
   - Market Data: http://localhost:8001/docs
   - Scanner: http://localhost:8002/docs
   - WebSocket: http://localhost:8003/docs

2. **Run Custom Scans**: Create your own criteria using the scanner DSL

3. **Build Frontend**: Start Next.js web application (coming next)

4. **Add More Features**: Backtesting, paper trading, live trading
