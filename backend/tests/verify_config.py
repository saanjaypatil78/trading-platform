
import sys
import os

# Assume running from project root
sys.path.append(os.getcwd())

# Set dummy env vars to satisfy pydantic validation
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("JWT_SECRET_KEY", "dummy_secret")

from backend.shared.config import settings

def test_config():
    print("Testing Configuration Loading...")
    print(f"UPSTOX_API_KEY: {'*' * 8 if settings.UPSTOX_API_KEY else 'NOT_SET'}")
    print(f"UPSTOX_API_SECRET: {'*' * 8 if settings.UPSTOX_API_SECRET else 'NOT_SET'}")
    print(f"RATELIMIT_ENABLED: {settings.RATELIMIT_ENABLED}")
    
    if settings.UPSTOX_API_KEY and settings.UPSTOX_API_KEY != "NOT_SET":
         print("SUCCESS: Upstox keys are loaded.")
    else:
         print("FAILURE: Upstox keys are missing.")

if __name__ == "__main__":
    test_config()
