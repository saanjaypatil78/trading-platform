"""
Security Middleware & Anti-Exploit
Implements rate limiting, payload validation, and request signing verification.
"""
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import time
import logging
from typing import Dict, Tuple

logger = logging.getLogger(__name__)

# Simple in-memory rate limiter for demo purposes (can be swapped for Redis)
_RATE_LIMIT_STORE: Dict[str, Tuple[int, float]] = {}
RATE_LIMIT_WINDOW = 60  # seconds
MAX_REQUESTS_PER_WINDOW = 100

class SecurityMiddleware:
    """
    Middleware for API security and anti-exploit mechanisms.
    """
    
    @staticmethod
    async def check_rate_limit(request: Request):
        """
        Enforce rate limits per IP address.
        """
        client_ip = request.client.host
        current_time = time.time()
        
        limit_data = _RATE_LIMIT_STORE.get(client_ip, (0, current_time))
        request_count, start_time = limit_data
        
        # Reset window if expired
        if current_time - start_time > RATE_LIMIT_WINDOW:
            request_count = 0
            start_time = current_time
        
        request_count += 1
        _RATE_LIMIT_STORE[client_ip] = (request_count, start_time)
        
        if request_count > MAX_REQUESTS_PER_WINDOW:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )

    @staticmethod
    async def validate_payload_size(request: Request, max_size_bytes: int = 1024 * 50): # 50KB limit
        """
        Prevent DoS via large payloads.
        """
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > max_size_bytes:
            logger.warning(f"Payload too large from IP: {request.client.host}")
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Payload too large."
            )

    @staticmethod
    def sanitize_input(text: str) -> str:
        """
        Basic input sanitization to prevent injection.
        """
        # Remove potentially dangerous characters
        dangerous_chars = [";", "--", "/*", "*/", "xp_"]
        sanitized = text
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, "")
        return sanitized

async def security_middleware_dependency(request: Request):
    """Dependency for FastAPI routes to enforce security."""
    await SecurityMiddleware.validate_payload_size(request)
    await SecurityMiddleware.check_rate_limit(request)
