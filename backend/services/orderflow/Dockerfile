FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY services/orderflow/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy common code
COPY shared ./backend/shared
COPY services/orderflow ./backend/services/orderflow

# Expose port
EXPOSE 8008

# Run the service
CMD ["python", "-m", "backend.services.orderflow.main"]
