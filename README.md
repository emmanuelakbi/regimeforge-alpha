# RegimeForge Alpha

**AI-Powered WEEX Cryptocurrency Trading Dashboard**

An intelligent trading platform for the WEEX exchange featuring real-time market regime detection, automated signal generation, Claude LLM-powered chat advisor, and seamless trade execution with AI log submission for hackathon verification.

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

### 🤖 Claude LLM Integration

- **AI Chat Advisor**: Context-aware trading assistant powered by Claude via AWS Bedrock
- **Market Briefs**: Natural language market summaries with AI insights
- **Signal Explanations**: Detailed reasoning behind AI trading signals
- **Risk Assessment**: AI-powered trade risk analysis with position sizing advice
- **Conversation Memory**: Chat maintains context across messages for consistent advice

### Trade Automation

- **Auto-Trading**: Configurable automated trade execution based on AI signals
- **Take-Profit Management**: Fixed and trailing take-profit modes
- **Risk Controls**: Daily loss limits, trade cooldowns, and position limits

---

## 🦎 CoinGecko API Integration

RegimeForge Alpha integrates CoinGecko API to enhance AI signal generation with global market context.

### Endpoints Used

| Endpoint               | Purpose                                            | Cache TTL |
| ---------------------- | -------------------------------------------------- | --------- |
| `GET /global`          | BTC dominance, total market cap, 24h market change | 5 min     |
| `GET /coins/markets`   | 7-day price trends, ATH distance, market cap rank  | 3 min     |
| `GET /search/trending` | Trending coins for momentum detection              | 10 min    |

### What Each Endpoint Contributes to the Strategy

#### 1. `GET /global` - Global Market Sentiment

**Data Used:**

- `market_cap_percentage.btc` - BTC dominance percentage
- `market_cap_change_percentage_24h_usd` - 24h market cap change

**What It Enables:**

- Determines overall market sentiment (BULLISH, NEUTRAL, BEARISH)
- AI adjusts signal confidence based on market-wide momentum
- High BTC dominance (>55%) signals potential altcoin underperformance
- Low BTC dominance (<45%) suggests altcoin season - boosts altcoin long signals

**File Location:** `trading_dashboard/services/coingecko.py` → `get_global_data()` (lines 149-190)

**Used In:** `trading_dashboard/services/ai_engine.py` → `_fetch_global_context()` (lines 240-280)

---

#### 2. `GET /coins/markets` - Coin-Specific Data

**Data Used:**

- `price_change_percentage_24h` - 24h price change
- `price_change_percentage_7d_in_currency` - 7-day price trend
- `ath_change_percentage` - Distance from all-time high
- `market_cap_rank` - Market cap ranking

**What It Enables:**

- Identifies extended rallies (+10% 7d) that may indicate exhaustion
- Detects prolonged declines (-10% 7d) for potential reversal plays
- ATH distance helps gauge upside potential
- Cross-references WEEX prices with CoinGecko for validation

**File Location:** `trading_dashboard/services/coingecko.py` → `get_coin_data()` (lines 192-255)

**Used In:** `trading_dashboard/services/ai_engine.py` → `analyze()` (lines 130-220)

---

#### 3. `GET /search/trending` - Trending Coins

**Data Used:**

- `coins[].item.symbol` - Trending coin symbols
- `coins[].item.market_cap_rank` - Trending coin rankings
- `coins[].item.score` - Trending score

**What It Enables:**

- Coins trending on CoinGecko receive a momentum boost in signal scoring (+5 points)
- Helps identify assets with increasing market attention
- Displayed in dashboard "Global Market" widget for user awareness

**File Location:** `trading_dashboard/services/coingecko.py` → `get_trending()` (lines 257-295)

**Used In:** `trading_dashboard/services/ai_engine.py` → `analyze()` (lines 200-210)

---

### Implementation Files

```
trading_dashboard/
├── services/
│   ├── coingecko.py      # CoinGecko API client with caching (lines 1-320)
│   │   ├── get_global_data()      # Fetches /global endpoint
│   │   ├── get_coin_data()        # Fetches /coins/markets endpoint
│   │   ├── get_trending()         # Fetches /search/trending endpoint
│   │   └── get_market_summary()   # Combines all data for AI
│   │
│   └── ai_engine.py      # AI engine using CoinGecko data (lines 1-350)
│       ├── _fetch_global_context()  # Gets CoinGecko data for analysis
│       └── analyze()                # Uses global context in signal generation
│
├── routes/
│   └── api.py            # /api/global endpoint (lines 265-285)
│
├── static/
│   └── dashboard.js      # loadGlobalMarket() function (lines 340-420)
│
└── templates/
    └── dashboard.html    # Global Market widget display (lines 180-230)
```

### CoinGecko Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    CoinGecko API Endpoints                       │
├─────────────────┬─────────────────────┬─────────────────────────┤
│   GET /global   │  GET /coins/markets │  GET /search/trending   │
│                 │                     │                         │
│ • BTC dominance │ • 7d price change   │ • Trending coins list   │
│ • Market cap Δ  │ • ATH distance      │ • Momentum indicators   │
│ • Sentiment     │ • Market cap rank   │                         │
└────────┬────────┴──────────┬──────────┴────────────┬────────────┘
         │                   │                       │
         ▼                   ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│              coingecko.py: get_market_summary()                  │
│                                                                  │
│  Combines all endpoints into unified market context object       │
│  with caching (5min global, 3min coins, 10min trending)         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│            ai_engine.py: _fetch_global_context()                 │
│                                                                  │
│  Extracts relevant data for signal generation:                   │
│  • btc_dominance, btc_dominance_trend                           │
│  • market_sentiment (BULLISH/NEUTRAL/BEARISH)                   │
│  • price_change_7d, ath_distance_pct                            │
│  • coin_is_trending (boolean)                                   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  ai_engine.py: analyze()                         │
│                                                                  │
│  Signal scoring adjustments based on CoinGecko data:            │
│                                                                  │
│  • Bullish sentiment: +10 to long score                         │
│  • Bearish sentiment: +10 to short score                        │
│  • Coin trending: +5 momentum boost                             │
│  • Extended 7d rally (>10%): -5 (exhaustion warning)            │
│  • Extended 7d decline (<-10%): +5 (reversal potential)         │
│  • High BTC dominance: reduces altcoin long confidence          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Dashboard Display                           │
│                                                                  │
│  Global Market Widget shows:                                     │
│  • Market Sentiment (color-coded)                               │
│  • BTC Dominance %                                              │
│  • Market Cap 24h Change                                        │
│  • 7d Price Change for selected coin                            │
│  • Trending coins list                                          │
│  • "🔥 [COIN] is trending!" badge when applicable               │
└─────────────────────────────────────────────────────────────────┘
```

### How CoinGecko API Helped the Strategy

**Summary:** CoinGecko API provides essential global market context that WEEX API alone cannot offer. By combining WEEX's real-time price data with CoinGecko's market-wide sentiment, BTC dominance trends, and trending coin detection, RegimeForge Alpha generates more informed trading signals.

**Key Improvements:**

1. **Market Sentiment Awareness**: Signals now consider whether the overall crypto market is bullish or bearish, not just the individual coin
2. **BTC Dominance Factor**: Altcoin signals are adjusted based on BTC dominance trends
3. **Momentum Detection**: Trending coins receive a confidence boost, capturing market attention
4. **Exhaustion Warnings**: Extended 7-day rallies trigger caution in long signals
5. **Reversal Detection**: Prolonged declines are flagged as potential reversal opportunities

**WebSocket API:** No, we did not use CoinGecko WebSocket API. We used REST endpoints with aggressive caching to stay within rate limits.

---

## 🧠 Claude LLM Features

RegimeForge Alpha integrates Claude (via AWS Bedrock) for intelligent trading assistance.

### Chat Advisor

- **Full Market Context**: Knows current price, signal, position, balance, and global sentiment
- **Conversation Memory**: Remembers previous messages for consistent advice
- **Quick Actions**: Pre-built prompts for common questions

### Endpoints

| Endpoint            | Purpose                             |
| ------------------- | ----------------------------------- |
| `GET /api/brief`    | AI-generated market summary         |
| `POST /api/explain` | Signal explanation from Claude      |
| `POST /api/risk`    | Risk assessment for proposed trades |
| `POST /api/chat`    | Full chat with conversation history |

---

## 🏗️ Architecture

```
trading_dashboard/
├── app.py               # Flask app factory
├── config.py            # Trading constants & API config
├── api_client.py        # Async WEEX API wrapper
├── routes/
│   ├── api.py           # Core trading + Claude + CoinGecko endpoints
│   ├── ai.py            # AI analysis endpoints
│   └── automation.py    # Automation control
├── services/
│   ├── claude.py        # Claude LLM service (AWS Bedrock)
│   ├── coingecko.py     # CoinGecko API client
│   ├── ai_engine.py     # RegimeForge AI engine
│   ├── trading.py       # Order execution
│   ├── take_profit.py   # TP management
│   └── automation.py    # Auto-trading logic
├── templates/
│   └── dashboard.html   # Web dashboard + Chat UI
└── static/
    ├── dashboard.css
    └── dashboard.js
```

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/emmanuelakbi/regimeforge-alpha.git
cd regimeforge-alpha
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
python run.py
```

### Configuration

```env
# WEEX API (required)
WEEX_API_KEY=your_api_key
WEEX_SECRET_KEY=your_secret_key
WEEX_PASSPHRASE=your_passphrase

# AWS Bedrock for Claude (optional)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

## 🔧 Tech Stack

- **Backend**: Python 3.x, Flask, Gunicorn
- **HTTP Client**: httpx (async)
- **LLM**: Claude 3 Haiku via AWS Bedrock
- **External APIs**: WEEX Contract API, CoinGecko API
- **Frontend**: Vanilla JavaScript, CSS, Jinja2

## 📄 License

MIT License - see [LICENSE](LICENSE) file.

## ⚠️ Disclaimer

RegimeForge Alpha is for educational purposes. Cryptocurrency trading involves substantial risk. Trade at your own risk.

---

**RegimeForge Alpha**: AI-powered trading with Claude LLM advisor and CoinGecko market intelligence.
