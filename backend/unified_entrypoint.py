
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.shared.config import settings

# Import sub-apps
# NOTE: Using lazy imports or just importing 'app' from each main.py
from backend.services.brain.main import app as brain_app
from backend.services.scanner.main import app as scanner_app
from backend.services.broker.main import app as broker_app
from backend.services.market_data.main import app as market_data_app
from backend.services.websocket.main import app as websocket_app
from backend.services.orderflow.main import app as orderflow_app
from backend.services.aggregator.main import app as aggregator_app
from backend.services.strategy_gen.main import app as strategy_gen_app
from backend.services.defi.main import app as defi_app
# from backend.services.defi.main import app as defi_app # Optional if high memory

# Create Unified App
app = FastAPI(
    title=f"{settings.APP_NAME} (Unified)",
    version=settings.APP_VERSION,
    description="Monolithic entrypoint for AWS Free Tier deployment"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, set to Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Sub-Applications
# The paths MUST match what the frontend expects.
# If frontend expects http://scanner-service/api/v1/scanner...
# we need to be careful.
# If frontend calls /api/v1/brain, we mount brain_app at /api/v1/brain?
# Let's check the sub-apps. They likely have their own /api/v1 prefixes.
# If brain_app has @app.get("/analyze"), mounting it at "/brain" makes it "/brain/analyze".

# Adjust mounting strategy:
# Adjust mounting strategy:
app.mount("/api/v1/brain", brain_app)
app.mount("/api/v1/scanner", scanner_app)
app.mount("/api/v1/orders", broker_app)
app.mount("/api/v1/market", market_data_app)
app.mount("/ws", websocket_app)
app.mount("/api/v1/orderflow", orderflow_app)
app.mount("/api/v1/signals", aggregator_app)
app.mount("/api/v1/strategy-gen", strategy_gen_app)
app.mount("/api/v1/defi", defi_app)

from backend.services.auth.router import router as auth_router
app.include_router(auth_router, prefix="/auth")

@app.get("/")
async def health():
    return {
        "status": "healthy",
        "mode": "unified_monolith",
        "services": ["brain", "scanner", "orders", "market-data"]
    }
