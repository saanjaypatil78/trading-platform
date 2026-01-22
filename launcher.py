"""
Trading Platform - Universal Launcher
Works on any Python environment: Local, Colab, Codespaces, Replit, etc.
"""
import os
import sys
import time
import threading
import webbrowser
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

def start_service(name: str, app_module: str, port: int):
    """Start a FastAPI service."""
    try:
        import uvicorn
        print(f"[{name}] Starting on port {port}...")
        uvicorn.run(app_module, host="0.0.0.0", port=port, log_level="warning")
    except Exception as e:
        print(f"[{name}] Failed: {e}")

def start_frontend(port: int = 8000):
    """Start static file server for frontend."""
    import http.server
    import socketserver
    
    os.chdir(ROOT / "frontend" / "static")
    
    Handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), Handler) as httpd:
        print(f"[Frontend] Serving on http://localhost:{port}")
        httpd.serve_forever()

def check_health(port: int) -> bool:
    """Check if service is healthy."""
    try:
        import urllib.request
        urllib.request.urlopen(f"http://localhost:{port}/health", timeout=2)
        return True
    except:
        return False

def main():
    print("=" * 60)
    print("   TRADING PLATFORM LAUNCHER")
    print("=" * 60)
    print()
    
    # Install dependencies if needed
    try:
        import fastapi
        import uvicorn
        import pydantic
    except ImportError:
        print("[Setup] Installing dependencies...")
        os.system(f"{sys.executable} -m pip install fastapi uvicorn pydantic httpx -q")
        print("[Setup] Dependencies installed!")
    
    # Start services in threads
    services = [
        ("Brain", "backend.services.brain.main:app", 8007),
        ("Scanner", "backend.services.scanner.main:app", 8008),
        ("Orders", "backend.services.broker.main:app", 8009),
        ("DeFi", "backend.services.defi.main:app", 8010),
        ("StrategyGen", "backend.services.strategy_gen.main:app", 8020),
        ("Webhooks", "backend.services.alerts.webhook_service:app", 8030),
    ]
    
    threads = []
    for name, module, port in services:
        t = threading.Thread(target=start_service, args=(name, module, port), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(1)
    
    # Wait for services to be ready
    print("\n[Startup] Waiting for services...")
    time.sleep(8)
    
    # Check health
    for name, _, port in services:
        status = "[OK]" if check_health(port) else "[FAIL]"
        print(f"  {status} {name} - http://localhost:{port}")
    
    print()
    print("=" * 60)
    print("   SERVICES READY!")
    print("=" * 60)
    print()
    print("Frontend:  http://localhost:8000")
    print("Brain API: http://localhost:8007/docs")
    print("Scanner:   http://localhost:8008/docs")
    print("Orders:    http://localhost:8009/docs")
    print("DeFi:      http://localhost:8010/docs")
    print()
    print("Press Ctrl+C to stop")
    print()
    
    # Try to open browser
    try:
        webbrowser.open("http://localhost:8000")
    except:
        pass
    
    # Start frontend (blocking)
    start_frontend(8000)

if __name__ == "__main__":
    main()
