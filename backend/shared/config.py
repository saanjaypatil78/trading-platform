from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application configuration settings"""
    
    # Application
    APP_NAME: str = "Trading Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_PREFIX: str = "/api/v1"
    
    # Database
    DATABASE_URL: str = "sqlite:///./trading_platform.db"
    DB_ECHO: bool = False
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 300  # 5 minutes default
    
    # RabbitMQ
    RABBITMQ_URL: Optional[str] = None
    
    # JWT
    JWT_SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Market Data APIs
    RAPIDAPI_KEY: Optional[str] = None
    RAPIDAPI_HOST: str = "indian-stock-exchange.p.rapidapi.com"
    
    FINNHUB_API_KEY: Optional[str] = None
    
    UPSTOX_API_KEY: str = "88112d04-5505-48a9-81ab-124aa04311b3"
    UPSTOX_API_SECRET: str = "o963nixptz"
    POLYGON_API_KEY: Optional[str] = None
    
    RATELIMIT_ENABLED: bool = True
    
    ALPHA_VANTAGE_API_KEY: Optional[str] = None
    
    # Keys for Provider Fallback
    ALPHAVANTAGE_API_KEY: Optional[str] = None # For compatibility if script uses this name
    ALPACA_API_KEY: Optional[str] = None
    ALPACA_API_SECRET: Optional[str] = None
    ZERODHA_API_KEY: Optional[str] = None
    ZERODHA_ACCESS_TOKEN: Optional[str] = None
    
    YAHOO_FINANCE_ENABLED: bool = True
    
    # Caching durations (seconds)
    CACHE_QUOTES_TTL: int = 60  # 1 minute
    CACHE_OHLC_TTL: int = 60  # 1 minute
    CACHE_HISTORICAL_TTL: int = 86400  # 24 hours
    CACHE_FUNDAMENTALS_TTL: int = 604800  # 7 days
    
    # Rate limiting
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    RATE_LIMIT_REQUESTS_PER_HOUR: int = 1000
    
    # Scanner
    SCANNER_MAX_STOCKS: int = 10000
    SCANNER_PARALLEL_WORKERS: int = 4
    SCANNER_TIMEOUT_SECONDS: int = 300
    
    # Backtesting
    BACKTEST_MAX_YEARS: int = 10
    BACKTEST_DEFAULT_CAPITAL: float = 100000
    BACKTEST_COMMISSION_PERCENT: float = 0.05
    
    # Paper Trading
    PAPER_TRADING_INITIAL_CAPITAL: float = 100000
    PAPER_TRADING_SLIPPAGE_PERCENT: float = 0.1
    
    # CORS
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:8000",
        "https://*.vercel.app"
    ]
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    # Sentry
    SENTRY_DSN: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
