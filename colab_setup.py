# Trading Platform - Google Colab One-Click Setup
# Run this cell to start the entire platform

# ============================================================================
# CELL 1: Clone and Setup
# ============================================================================
# Run this cell first
!pip install fastapi uvicorn pydantic httpx -q

import os
import sys
import subprocess
from threading import Thread
import time

# Clone repo (uncomment if needed)
# !git clone https://github.com/your-repo/trading-platform.git
# %cd trading-platform

# ============================================================================
# CELL 2: Start All Services
# ============================================================================
def run_service(name, module, port):
    """Run a FastAPI service in background"""
    import uvicorn
    print(f"[{name}] Starting on port {port}...")
    uvicorn.run(module, host="0.0.0.0", port=port, log_level="warning")

# Import and start services
sys.path.insert(0, os.getcwd())

# Start services in threads
from backend.services.brain.main import app as brain_app
from backend.services.scanner.main import app as scanner_app
from backend.services.broker.main import app as orders_app

Thread(target=run_service, args=("Brain", brain_app, 8007), daemon=True).start()
time.sleep(2)
Thread(target=run_service, args=("Scanner", scanner_app, 8008), daemon=True).start()
time.sleep(2)
Thread(target=run_service, args=("Orders", orders_app, 8009), daemon=True).start()
time.sleep(2)

print("\n" + "="*60)
print("ALL SERVICES STARTED!")
print("="*60)
print("Brain API:   http://localhost:8007")
print("Scanner API: http://localhost:8008")
print("Orders API:  http://localhost:8009")

# ============================================================================
# CELL 3: Expose via ngrok (for external access)
# ============================================================================
# Uncomment to expose services externally
"""
!pip install pyngrok -q
from pyngrok import ngrok

# Expose scanner service
public_url = ngrok.connect(8008)
print(f"Public Scanner URL: {public_url}")
"""

# ============================================================================
# CELL 4: Serve Static Frontend
# ============================================================================
import http.server
import socketserver
import webbrowser

PORT = 8000
os.chdir("frontend/static")

Handler = http.server.SimpleHTTPRequestHandler
with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"\nFrontend: http://localhost:{PORT}")
    print("\nOpen the URL above to access the Trading Platform UI")
    httpd.serve_forever()
