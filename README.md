# RegimeForge Alpha

**AI-Powered WEEX Cryptocurrency Trading Dashboard**

An intelligent trading platform for the WEEX exchange featuring real-time market regime detection, automated signal generation, and seamless trade execution with AI log submission for hackathon verification.

## 🚀 Key Features

### Trading & Market Data

- **Real-time Market Data**: Live price feeds, order books, and candlestick data
- **Multi-Asset Support**: BTC, ETH, SOL, XRP, BNB, ADA, DOGE, LTC perpetual contracts
- **Position Tracking**: Real-time position monitoring with PnL calculations
- **Order Management**: Market and limit orders with proper size validation

### AI-Powered Analysis

- **Market Regime Detection**: Identifies trending, ranging, and volatile market conditions
- **Signal Generation**: Automated LONG/SHORT signals with confidence scores
- **Technical Indicators**: RSI, volatility analysis, trend detection
- **Global Market Context**: CoinGecko integration for enhanced signal accuracy
- **AI Log Submission**: Automatic logging for WEEX hackathon verification

### Trade Automation

- **Auto-Trading**: Configurable automated trade execution based on AI signals
- **Take-Profit Management**: Fixed and trailing take-profit modes
- **Risk Controls**: Daily loss limits, trade cooldowns, and position limits

---

## 🦎 CoinGecko API Integration

RegimeForge Alpha integrates CoinGecko API to enhance AI signal generation with global market context.

### Endpoints Used

| Endpoint               | Purpose                                            | File Location                             |
| ---------------------- | -------------------------------------------------- | ----------------------------------------- |
| `GET /global`          | BTC dominance, total market cap, 24h market change | `trading_dashboard/services/coingecko.py` |
| `GET /coins/markets`   | 7-day price trends, ATH distance, market cap rank  | `trading_dashboard/services/coingecko.py` |
| `GET /search/trending` | Trending coins for momentum detection              | `trading_dashboard/services/coingecko.py` |

### How CoinGecko Data Enhances the Strategy

**1. Global Market Sentiment** (`/global`)

- Fetches total market cap change (24h) to determine if the overall crypto market is bullish or bearish
- AI adjusts signal confidence based on market-wide momentum
- Location: `coingecko.py:get_global_data()` → used in `ai_engine.py:_fetch_global_context()`

**2. BTC Dominance Analysis** (`/global`)

- High BTC dominance (>55%) signals potential altcoin underperformance
- Low BTC dominance (<45%) suggests altcoin season - boosts altcoin long signals
- Location: `coingecko.py:GlobalMarketData.btc_dominance_trend` → `ai_engine.py:analyze()`

**3. 7-Day Price Trends** (`/coins/markets`)

- Identifies extended rallies (+10% 7d) that may indicate exhaustion
- Detects prolonged declines (-10% 7d) for potential reversal plays
- Location: `coingecko.py:get_coin_data()` → `ai_engine.py:analyze()`

**4. Trending Coin Detection** (`/search/trending`)

- Coins trending on CoinGecko receive a momentum boost in signal scoring
- Helps identify assets with increasing market attention
- Location: `coingecko.py:get_trending()` → `ai_engine.py:analyze()`

### Implementation Files

```text
trading_dashboard/
├── services/
│   ├── coingecko.py      # CoinGecko API client with caching
│   └── ai_engine.py      # AI engine using CoinGecko data (lines 1-50, 103-220)
├── routes/
│   └── api.py            # /api/global endpoint (lines 220-240)
├── static/
│   └── dashboard.js      # loadGlobalMarket() function (lines 340-395)
└── templates/
    └── dashboard.html    # Global Market widget display
```

### CoinGecko Data Flow

```text
CoinGeckoClient.get_market_summary()
    ├── get_global_data()      → BTC dominance, market sentiment
    ├── get_coin_data()        → 7d trends, ATH distance
    └── get_trending()         → Trending coins list
            ↓
RegimeForgeAI._fetch_global_context()
            ↓
RegimeForgeAI.analyze()        → Enhanced signal with global context
            ↓
Dashboard displays:
    - Global Market widget (sentiment, BTC dom, trending)
    - AI reasoning includes CoinGecko insights
```

---

## 🏗️ Architecture

```text
trading_dashboard/
├── __init__.py          # Package init
├── app.py               # Flask app factory
├── config.py            # Trading constants & API config
├── api_client.py        # Async WEEX API wrapper
├── models.py            # Data models
├── utils.py             # Helper functions
├── routes/
│   ├── api.py           # Core trading endpoints + /api/global
│   ├── ai.py            # AI analysis endpoints
│   └── automation.py    # Automation control
├── services/
│   ├── coingecko.py     # CoinGecko API client (NEW)
│   ├── ai_engine.py     # RegimeForge AI engine
│   ├── trading.py       # Order execution
│   ├── take_profit.py   # TP management
│   └── automation.py    # Auto-trading logic
├── templates/
│   └── dashboard.html   # Web dashboard
└── static/
    ├── dashboard.css
    └── dashboard.js
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- WEEX API credentials (with IP whitelisting)

### Installation

```bash
# Clone the repository
git clone https://github.com/emmanuelakbi/regimeforge-alpha.git
cd regimeforge-alpha

# Install dependencies
pip install -r requirements.txt

# Configure credentials
cp .env.example .env
# Edit .env with your WEEX API credentials
```

### Configuration

Create a `.env` file with your WEEX credentials:

```env
WEEX_API_KEY=your_api_key
WEEX_SECRET_KEY=your_secret_key
WEEX_PASSPHRASE=your_passphrase
```

### Running Locally

```bash
python run.py
```

Access the dashboard at `http://localhost:5000`

### Deployment

```bash
./deploy.sh
```

## 📊 API Endpoints

### Market Data

- `GET /api/price` - Current price ticker
- `GET /api/depth` - Order book depth
- `GET /api/klines` - Candlestick data
- `GET /api/global` - CoinGecko global market data

### Account

- `GET /api/balance` - Account balance
- `GET /api/position` - Current positions

### Trading

- `POST /api/trade` - Place manual trade
- `POST /api/close` - Close position

### AI

- `GET /api/ai/analyze` - Get AI signal (includes CoinGecko context)
- `POST /api/ai/trade` - Execute AI-driven trade

### Automation Controls

- `GET /api/automation/settings` - Get automation settings
- `POST /api/automation/settings` - Update settings
- `POST /api/automation/toggle` - Enable/disable automation

## 🔧 Tech Stack

- **Backend**: Python 3.x, Flask
- **HTTP Client**: httpx (async)
- **External APIs**: WEEX Contract API, CoinGecko API
- **Frontend**: Vanilla JavaScript, CSS
- **Templates**: Jinja2
- **Production**: Gunicorn

## 🧪 Testing

```bash
python test_comprehensive.py
```

## ⚠️ Important Notes

- WEEX API requires IP whitelisting - ensure your server IP is whitelisted
- CoinGecko free tier: 30 calls/minute (caching implemented)
- Always test with small amounts first
- The AI signals are for informational purposes - trade at your own risk

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

RegimeForge Alpha is provided for educational and research purposes. Cryptocurrency trading involves substantial risk of loss. Users are responsible for their own trading decisions and should never trade with funds they cannot afford to lose.

---

**RegimeForge Alpha**: AI-powered trading enhanced with CoinGecko global market intelligence.
