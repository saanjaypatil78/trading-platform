FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY ../../requirements.txt .

# Install Python dependencies including backtesting libraries
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir vectorbt backtrader

# Copy application code
COPY . .
COPY ../../shared /app/shared

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
