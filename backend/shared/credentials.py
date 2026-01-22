"""
Unified Credentials Manager
Handles secure retrieval of API keys and secrets from environment variables.
"""
import os
from dotenv import load_dotenv
from typing import Optional

# Load .env file if it exists
load_dotenv()

class Credentials:
    # Alpaca
    ALPACA_API_KEY = os.getenv("ALPACA_API_KEY")
    ALPACA_API_SECRET = os.getenv("ALPACA_API_SECRET")
    ALPACA_PAPER = os.getenv("ALPACA_PAPER", "true").lower() == "true"

    # Polygon.io
    POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")

    # Indian Brokers (Upstox & Zerodha)
    UPSTOX_API_KEY = os.getenv("UPSTOX_API_KEY")
    UPSTOX_API_SECRET = os.getenv("UPSTOX_API_SECRET")
    UPSTOX_REDIRECT_URI = os.getenv("UPSTOX_REDIRECT_URI", "http://localhost:8000/callback")
    
    ZERODHA_API_KEY = os.getenv("ZERODHA_API_KEY")
    ZERODHA_API_SECRET = os.getenv("ZERODHA_API_SECRET")

    @classmethod
    def get_alpaca_creds(cls) -> dict:
        return {
            "key_id": cls.ALPACA_API_KEY,
            "secret_key": cls.ALPACA_API_SECRET,
            "paper": cls.ALPACA_PAPER
        }

    @classmethod
    def get_polygon_key(cls) -> Optional[str]:
        return cls.POLYGON_API_KEY

    @classmethod
    def get_upstox_creds(cls) -> dict:
        return {
            "api_key": cls.UPSTOX_API_KEY,
            "api_secret": cls.UPSTOX_API_SECRET,
            "redirect_uri": cls.UPSTOX_REDIRECT_URI
        }

    @classmethod
    def is_upstox_configured(cls) -> bool:
        return bool(cls.UPSTOX_API_KEY and cls.UPSTOX_API_SECRET)

    @classmethod
    def is_alpaca_configured(cls) -> bool:
        return bool(cls.ALPACA_API_KEY and cls.ALPACA_API_SECRET)

    @classmethod
    def is_polygon_configured(cls) -> bool:
        return bool(cls.POLYGON_API_KEY)
