FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir fastapi uvicorn httpx pydantic

# Copy code
COPY services/aggregator ./backend/services/aggregator

# Expose port
EXPOSE 8011

# Run the service
CMD ["python", "-m", "backend.services.aggregator.main"]
