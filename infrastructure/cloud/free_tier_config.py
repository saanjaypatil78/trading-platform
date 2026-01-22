"""
Free-Tier Cloud Optimization Config
Settings and templates for Vercel, AWS, and GCP free tiers.
"""

CLOUD_CONFIG = {
    "vercel": {
        "tier": "Hobby",
        "optimization": [
            "Edge Runtime for low-latency API calls",
            "Static Regeneration for scanner templates",
            "Environment Variable scoping for multi-broker keys"
        ],
        "limits": {
            "max_duration": 10, # 10s for free tier serverless
            "memory": 1024
        }
    },
    "aws": {
        "tier": "Free Tier (12 Months)",
        "instance": "t2.micro",
        "services": [
            "EC2 for Backend Services (Brain, Orders)",
            "Lambda for Webhook Ingestion",
            "DynamoDB (25GB) for State persistence"
        ],
        "optimization": [
            "ARM64 (t4g.small) if available in free tier",
            "VPC endpoints to reduce data transfer costs"
        ]
    },
    "gcp": {
        "tier": "Free Forever",
        "instance": "e2-micro",
        "region": "us-west1", # Required for free tier
        "services": [
            "Cloud Run for scalable scanner engine",
            "Pub/Sub for MessageBus decoupling"
        ]
    },
    "colab": {
        "usage": "Headless Strategy Research",
        "optimization": [
            "Use Numba for 10x backtest speedup",
            "Interactive visualization via Plotly/Streamlit"
        ]
    }
}

def get_optimized_settings(provider: str) -> dict:
    """Returns provider-specific optimization flags."""
    return CLOUD_CONFIG.get(provider, {})

def generate_deploy_hints():
    """Prints hints for the user to stay within free limits."""
    print("--- Free-Tier Deployment Hints ---")
    print("1. Vercel: Use 'next build' and ensure large assets are in public/")
    print("2. AWS: Keep EC2 running US-EAST-1/2 for maximum compatibility")
    print("3. GCP: Use e2-micro only in us-west1, us-central1, or us-east1")
    print("4. Gmail: Use 'App Passwords' to bypass 2FA for alerting")
