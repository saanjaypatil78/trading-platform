
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.shared.config import settings

# Keep legacy shared.* imports deterministic for all mounted services.
BACKEND_ROOT = Path(__file__).resolve().parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Import sub-apps
from backend.services.brain.main import app as brain_app
from backend.services.scanner.main import app as scanner_app
from backend.services.broker.main import app as broker_app
from backend.services.market_data.main import app as market_data_app

app = FastAPI(
    title=f"{settings.APP_NAME} (Unified)",
    version=settings.APP_VERSION,
    description="Monolithic entrypoint for AWS Free Tier deployment"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, set to Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/api/v1/brain", brain_app)
app.mount("/api/v1/scanner", scanner_app)
app.mount("/api/v1/orders", broker_app)
app.mount("/api/v1/market-data", market_data_app)

from backend.services.auth.router import router as auth_router
from services.collaboration.router import router as collaboration_router

app.include_router(auth_router, prefix="/auth")
app.include_router(collaboration_router)


@app.get("/")
async def health():
    return {
        "status": "healthy",
        "mode": "unified_monolith",
        "services": ["brain", "scanner", "orders", "market-data", "collaboration"]
    }
