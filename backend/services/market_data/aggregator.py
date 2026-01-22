from typing import Optional, List
from datetime import datetime
import logging
from .providers import RapidAPIProvider, FinnhubProvider, YahooFinanceProvider
from .providers.polygon_provider import PolygonProvider
from .providers.upstox_provider import UpstoxProvider
from .providers.alpaca_provider import AlpacaProvider
from .providers.alphavantage_provider import AlphaVantageProvider
from .providers.zerodha_provider import ZerodhaProvider
from shared.models import Quote, OHLCV, HistoricalData, CompanyInfo, SearchResult, ProviderHealth
from shared.cache import cache
from shared.config import settings

logger = logging.getLogger(__name__)


class MarketDataAggregator:
    """
    Aggregates market data from multiple providers with automatic failover.
    Implements intelligent caching and rate limiting.
    """
    
    def __init__(self):
        self.providers = []
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize all available providers in priority order"""
        # Priority: Yahoo -> AlphaVantage -> Upstox -> Alpaca -> Zerodha
        
        # 1. Yahoo Finance (Best Coverage/Free)
        if settings.YAHOO_FINANCE_ENABLED:
            self.providers.append(YahooFinanceProvider())
            logger.info("Initialized Yahoo Finance provider (Priority 1)")

        # 2. AlphaVantage
        if settings.ALPHAVANTAGE_API_KEY:
            self.providers.append(AlphaVantageProvider(settings.ALPHAVANTAGE_API_KEY))
            logger.info("Initialized AlphaVantage provider (Priority 2)")

        # 3. Upstox (Indian Market)
        if settings.UPSTOX_API_KEY:
            self.providers.append(UpstoxProvider(settings.UPSTOX_API_KEY))
            logger.info("Initialized Upstox provider (Priority 3)")

        # 4. Alpaca (US/Crypto/Reliable)
        if settings.ALPACA_API_KEY:
            self.providers.append(AlpacaProvider(settings.ALPACA_API_KEY, settings.ALPACA_API_SECRET))
            logger.info("Initialized Alpaca provider (Priority 4)")
            
        # 5. Zerodha (Indian Market Fallback)
        if settings.ZERODHA_API_KEY:
            self.providers.append(ZerodhaProvider(settings.ZERODHA_API_KEY))
            logger.info("Initialized Zerodha provider (Priority 5)")
        
        if not self.providers:
            logger.warning("No market data providers configured!")
    
    async def get_quote(self, symbol: str, use_cache: bool = True) -> Optional[Quote]:
        """
        Get real-time quote with caching and failover
        
        Args:
            symbol: Stock symbol (e.g., "RELIANCE")
            use_cache: Whether to use cached data
        
        Returns:
            Quote object or None if all providers fail
        """
        cache_key = f"quote:{symbol}"
        
        # Check cache first
        if use_cache:
            cached = await cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for quote: {symbol}")
                return cached
        
        # Try each provider in order
        for provider in self.providers:
            if not provider.is_available:
                logger.debug(f"Skipping unavailable provider: {provider.name}")
                continue
            
            try:
                logger.info(f"Fetching quote for {symbol} from {provider.name}")
                quote = await provider.get_quote(symbol)
                
                if quote:
                    # Cache the result
                    await cache.set(cache_key, quote, ttl=settings.CACHE_QUOTES_TTL)
                    logger.info(f"Successfully fetched quote for {symbol} from {provider.name}")
                    return quote
                else:
                    logger.warning(f"No data returned for {symbol} from {provider.name}")
                    
            except Exception as e:
                logger.error(f"Error fetching quote from {provider.name}: {e}")
                provider.mark_unavailable(str(e))
                continue
        
        logger.error(f"Failed to fetch quote for {symbol} from all providers")
        return None
    
    async def get_ohlcv(
        self, 
        symbol: str, 
        interval: str = "1d",
        limit: int = 100,
        use_cache: bool = True
    ) -> Optional[List[OHLCV]]:
        """Get OHLCV data with caching and failover"""
        cache_key = f"ohlcv:{symbol}:{interval}:{limit}"
        
        # Check cache
        if use_cache:
            cached = await cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for OHLCV: {symbol}")
                return cached
        
        # Try each provider
        for provider in self.providers:
            if not provider.is_available:
                continue
            
            try:
                logger.info(f"Fetching OHLCV for {symbol} from {provider.name}")
                ohlcv = await provider.get_ohlcv(symbol, interval, limit)
                
                if ohlcv and len(ohlcv) > 0:
                    await cache.set(cache_key, ohlcv, ttl=settings.CACHE_OHLC_TTL)
                    logger.info(f"Successfully fetched {len(ohlcv)} candles for {symbol}")
                    return ohlcv
                    
            except Exception as e:
                logger.error(f"Error fetching OHLCV from {provider.name}: {e}")
                provider.mark_unavailable(str(e))
                continue
        
        logger.error(f"Failed to fetch OHLCV for {symbol}")
        return None
    
    async def get_historical(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        interval: str = "1d",
        use_cache: bool = True
    ) -> Optional[HistoricalData]:
        """Get historical data for date range"""
        cache_key = f"historical:{symbol}:{start_date.date()}:{end_date.date()}:{interval}"
        
        # Check cache (longer TTL for historical data)
        if use_cache:
            cached = await cache.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for historical: {symbol}")
                return cached
        
        # Try each provider
        for provider in self.providers:
            if not provider.is_available:
                continue
            
            try:
                logger.info(f"Fetching historical data for {symbol} from {provider.name}")
                historical = await provider.get_historical(symbol, start_date, end_date, interval)
                
                if historical and len(historical.data) > 0:
                    await cache.set(cache_key, historical, ttl=settings.CACHE_HISTORICAL_TTL)
                    logger.info(f"Successfully fetched historical data for {symbol}")
                    return historical
                    
            except Exception as e:
                logger.error(f"Error fetching historical from {provider.name}: {e}")
                provider.mark_unavailable(str(e))
                continue
        
        logger.error(f"Failed to fetch historical for {symbol}")
        return None
    
    async def search_symbols(self, query: str) -> Optional[List[SearchResult]]:
        """Search for stock symbols"""
        # Symbol search doesn't need caching as much
        for provider in self.providers:
            if not provider.is_available:
                continue
            
            try:
                results = await provider.search_symbols(query)
                if results:
                    return results
            except Exception as e:
                logger.error(f"Error searching from {provider.name}: {e}")
                continue
        
        return None
    
    async def get_company_info(
        self, 
        symbol: str,
        use_cache: bool = True
    ) -> Optional[CompanyInfo]:
        """Get company fundamental information"""
        cache_key = f"company:{symbol}"
        
        if use_cache:
            cached = await cache.get(cache_key)
            if cached:
                return cached
        
        for provider in self.providers:
            if not provider.is_available:
                continue
            
            try:
                info = await provider.get_company_info(symbol)
                if info:
                    await cache.set(cache_key, info, ttl=settings.CACHE_FUNDAMENTALS_TTL)
                    return info
            except Exception as e:
                logger.error(f"Error fetching company info from {provider.name}: {e}")
                continue
        
        return None
    
    async def get_provider_health(self) -> List[ProviderHealth]:
        """Get health status of all providers"""
        health_statuses = []
        
        for provider in self.providers:
            try:
                start_time = datetime.now()
                is_healthy = await provider.health_check()
                response_time = (datetime.now() - start_time).total_seconds() * 1000
                
                health = ProviderHealth(
                    provider=provider.name,
                    is_available=is_healthy,
                    response_time_ms=response_time if is_healthy else None,
                    rate_limit_remaining=provider.rate_limit_remaining,
                    last_error=provider.last_error,
                    last_check=datetime.now()
                )
                
                if is_healthy:
                    provider.mark_available()
                
            except Exception as e:
                health = ProviderHealth(
                    provider=provider.name,
                    is_available=False,
                    response_time_ms=None,
                    rate_limit_remaining=None,
                    last_error=str(e),
                    last_check=datetime.now()
                )
            
            health_statuses.append(health)
        
        return health_statuses
    
    async def get_bulk_quotes(self, symbols: List[str]) -> dict[str, Optional[Quote]]:
        """Get quotes for multiple symbols efficiently"""
        results = {}
        
        for symbol in symbols:
            quote = await self.get_quote(symbol)
            results[symbol] = quote
        
        return results


# Global aggregator instance
aggregator = MarketDataAggregator()
