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

### 🤖 Claude LLM Integration (NEW)

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

## 🧠 Claude LLM Features

RegimeForge Alpha integrates Claude (via AWS Bedrock) for intelligent trading assistance.

### Chat Advisor

The AI Chat Advisor provides context-aware trading guidance:

- **Full Market Context**: Knows current price, signal, position, balance, and global sentiment
- **Conversation Memory**: Remembers previous messages for consistent advice
- **Quick Actions**: Pre-built prompts for common questions (position analysis, risk check, trade ideas)

### Endpoints

| Endpoint                 | Purpose                             |
| ------------------------ | ----------------------------------- |
| `GET /api/brief`         | AI-generated market summary         |
| `POST /api/explain`      | Signal explanation from Claude      |
| `POST /api/risk`         | Risk assessment for proposed trades |
| `POST /api/chat`         | Full chat with conversation history |
| `POST /api/chat/quick`   | Quick action prompts                |
| `GET /api/claude/status` | Check if Claude is enabled          |

### Implementation

```text
trading_dashboard/
├── services/
│   └── claude.py         # Claude service (AWS Bedrock integration)
├── routes/
│   └── api.py            # Chat and brief endpoints
├── static/
│   └── dashboard.js      # Chat UI functions
└── templates/
    └── dashboard.html    # Chat interface
```

---

## 🦎 CoinGecko API Integration

RegimeForge Alpha integrates CoinGecko API to enhance AI signal generation with global market context.

### Endpoints Used

| Endpoint               | Purpose                         | Cache TTL |
| ---------------------- | ------------------------------- | --------- |
| `GET /global`          | BTC dominance, market sentiment | 5 min     |
| `GET /coins/markets`   | 7-day trends, ATH distance      | 3 min     |
| `GET /search/trending` | Trending coins detection        | 10 min    |

### How CoinGecko Data Enhances the Strategy

**1. Global Market Sentiment** - AI adjusts signal confidence based on market-wide momentum

**2. BTC Dominance Analysis** - High dominance signals altcoin underperformance

**3. 7-Day Price Trends** - Identifies extended rallies or declines for reversal plays

**4. Trending Coin Detection** - Coins trending on CoinGecko receive momentum boost

### Rate Limit Handling

- Aggressive caching to stay within 30 calls/minute free tier
- Stale cache fallback when rate limited
- 3-second minimum interval between requests

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
│   ├── api.py           # Core trading + Claude endpoints
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
    ├── dashboard.css    # Styles including chat
    └── dashboard.js     # Frontend + chat functions
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- WEEX API credentials (with IP whitelisting)
- AWS credentials (for Claude LLM features - optional)

### Installation

```bash
# Clone the repository
git clone https://github.com/emmanuelakbi/regimeforge-alpha.git
cd regimeforge-alpha

# Install dependencies
pip install -r requirements.txt

# Configure credentials
cp .env.example .env
# Edit .env with your credentials
```

### Configuration

Create a `.env` file:

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
- `GET /api/balance` - Account balance
- `GET /api/position` - Current positions
- `GET /api/global` - CoinGecko global market data

### Trading

- `POST /api/open` - Open position
- `POST /api/close` - Close position

### AI Analysis

- `GET /api/ai/analyze` - Get AI signal
- `POST /api/ai/trade` - Execute AI-driven trade

### Claude LLM

- `GET /api/brief` - Market brief
- `POST /api/explain` - Signal explanation
- `POST /api/risk` - Risk assessment
- `POST /api/chat` - Chat with AI advisor

### Automation

- `GET /api/automation/settings` - Get settings
- `POST /api/automation/settings` - Update settings

## 🔧 Tech Stack

- **Backend**: Python 3.x, Flask, Gunicorn
- **HTTP Client**: httpx (async)
- **LLM**: Claude 3 Haiku via AWS Bedrock
- **External APIs**: WEEX Contract API, CoinGecko API
- **Frontend**: Vanilla JavaScript, CSS, Jinja2

## 🧪 Testing

```bash
python test_comprehensive.py
```

## ⚠️ Important Notes

- WEEX API requires IP whitelisting
- CoinGecko free tier: 30 calls/minute (caching implemented)
- Claude features require AWS Bedrock access
- Always test with small amounts first

## 📄 License

MIT License - see [LICENSE](LICENSE) file.

## ⚠️ Disclaimer

RegimeForge Alpha is for educational purposes. Cryptocurrency trading involves substantial risk. Trade at your own risk.

---

**RegimeForge Alpha**: AI-powered trading with Claude LLM advisor and CoinGecko market intelligence.
