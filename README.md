# Trading Platform

A complete algorithmic trading platform combining **Chartink** (stock screeners) and **OpenAlgo** (order execution) features.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/your-repo/trading-platform)
[![Open in Gitpod](https://gitpod.io/button/open-in-gitpod.svg)](https://gitpod.io/#https://github.com/your-repo/trading-platform)

## 🚀 Quick Start

### Option 1: One-Click Cloud Launch
- **GitHub Codespaces**: Click the badge above or press `.` on GitHub
- **Gitpod**: Click the Gitpod badge above
- **Google Colab**: Upload `colab_setup.py` and run all cells

### Option 2: Local Launch
```bash
python launcher.py
```

### Option 3: Manual Start
```bash
# Start services individually
python backend/services/brain/main.py   # Port 8007
python backend/services/scanner/main.py # Port 8008
python backend/services/broker/main.py  # Port 8009

# Start frontend
cd frontend/static && python -m http.server 8000
```

## 📊 Features

### Scanner Engine (Chartink-style)
- **16+ Technical Indicators**: RSI, MACD, SMA, EMA, Bollinger, ATR, VWAP
- **Custom Conditions**: `rsi(14) > 70`, `sma(50) > sma(200)`
- **Pre-built Templates**: RSI Overbought, Golden Cross, Death Cross
- **Real-time Scanning**: Scan entire stock universes

### Order Execution (OpenAlgo-style)
- **Paper Trading**: Simulated broker with slippage & commissions
- **Order Types**: Market, Limit, Stop Loss, SL-Market
- **Position Tracking**: Real-time P&L calculation
- **Webhook Support**: TradingView, Amibroker integration

### AI Brain (Chain-of-Thought)
- **Sequential Thinking**: Explainable multi-step reasoning
- **5 Trading Strategies**: Entry, Risk, Regime, Portfolio, Earnings
- **Knowledge Graph Memory**: Persistent context and learning
- **GLM 4.7 Registry**: Self-updating model metadata exposed via `/model`

### Workflow Tools
- **Action Center**: Auto/Semi-Auto execution modes
- **Smart Router**: Latency-based order routing
- **Monitoring**: Latency P50/P95/P99, Traffic analytics, P&L tracking
- **Telegram Bot**: Real-time notifications

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│              Frontend (Static HTML)                 │
│   No npm required - Uses Tailwind CDN + Vanilla JS  │
└─────────────────────────────────────────────────────┘
                          │
         ┌────────────────┼────────────────┐
         ▼                ▼                ▼
   ┌──────────┐    ┌──────────┐    ┌──────────┐
   │  Brain   │    │ Scanner  │    │  Orders  │
   │  :8007   │    │  :8008   │    │  :8009   │
   └──────────┘    └──────────┘    └──────────┘
         │                │                │
         └────────────────┴────────────────┘
                          │
         ┌────────────────┴────────────────┐
         ▼                                 ▼
   ┌──────────┐                     ┌──────────┐
   │  Shared  │                     │  Broker  │
   │  Brain   │                     │  Adapter │
   │  Memory  │                     │  Paper   │
   └──────────┘                     └──────────┘
```

## 🔗 Repository Lineage

This workspace combines features inspired by three upstream sources:

- **Chartink**: Scanner DSL and indicator templates power the stock screening workflows.
- **OpenAlgo**: Order placement, webhook support, and broker adapters shape execution.
- **FACTRADE-solana**: DeFi staking UI and tokenomics utilities are ported into the passive-income module.

The latest repo focuses on merging these components into one cohesive platform, while keeping the AI layer local and cost-aware.

## 📁 Project Structure

```
trading-platform/
├── backend/
│   ├── services/
│   │   ├── brain/      # AI reasoning API
│   │   ├── scanner/    # Stock screener API
│   │   └── broker/     # Order execution API
│   └── shared/
│       ├── brain/      # SequentialThinker, KnowledgeGraph
│       └── workflow/   # ActionCenter, Monitoring
├── frontend/
│   └── static/         # No-build HTML frontend
├── launcher.py         # Universal launcher
├── colab_setup.py      # Google Colab script
├── codespaces_setup.sh # Bash setup script
├── .devcontainer/      # GitHub Codespaces config
└── .gitpod.yml         # Gitpod config
```

## 🔌 API Endpoints

### Brain Service (Port 8007)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/brain/entry-analysis` | POST | Buy/Sell decision |
| `/api/v1/brain/risk-assessment` | POST | Position sizing |
| `/api/v1/brain/regime-detection` | POST | Market regime |
| `/api/v1/brain/earnings-play` | POST | Options strategy |
| `/api/v1/brain/memory` | GET | Knowledge graph |

### Scanner Service (Port 8008)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/scanner/scan` | POST | Run custom scan |
| `/api/v1/scanner/templates` | GET | List templates |
| `/api/v1/scanner/template/{name}` | POST | Run template |
| `/api/v1/scanner/indicators/{symbol}` | GET | Get indicators |

### Order Service (Port 8009)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/orders/place` | POST | Place order |
| `/api/v1/orders` | GET | List orders |
| `/api/v1/positions` | GET | Current positions |
| `/api/v1/funds` | GET | Available capital |
| `/api/v1/webhook` | POST | TradingView signal |

## 🧪 Testing

```bash
# Run all tests
python test_openalgo.py
python test_workflow.py
python verify_modules.py

# Debug agent
python debug_agent.py --fix
```

### 🎥 Demo Videos
The following videos demonstrating key features have been generated and saved locally:

- **System Diagnostics**: `C:\Users\Asus\.gemini\antigravity\brain\139ddc94-6818-4295-9a4d-29cfe3634d5f\system_diagnosis_1769019772246.webp`
- **Simple Strategy Generation ("SMA Crossover")**: `C:\Users\Asus\.gemini\antigravity\brain\139ddc94-6818-4295-9a4d-29cfe3634d5f\verify_strategy_gen_1769021461257.webp`
- **Complex Strategy Generation ("RSI + WMA + Divergence")**: `C:\Users\Asus\.gemini\antigravity\brain\139ddc94-6818-4295-9a4d-29cfe3634d5f\verify_complex_strategy_gen_1769022225120.webp`

> *Note: These files are regular WebP images/animations that can be viewed in Chrome or any modern image viewer.*

## 📝 License

MIT License - Feel free to use and modify.

## 🙏 Credits

Inspired by:
- [OpenAlgo](https://github.com/marketcalls/openalgo) - Open-source algo trading
- [Chartink](https://chartink.com) - Stock screeners
- [MCP Sequential Thinking](https://github.com/modelcontextprotocol) - AI reasoning
