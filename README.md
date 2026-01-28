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
- **AI Log Submission**: Automatic logging for WEEX hackathon verification

### Automation

- **Auto-Trading**: Configurable automated trade execution based on AI signals
- **Take-Profit Management**: Fixed and trailing take-profit modes
- **Risk Controls**: Daily loss limits, trade cooldowns, and position limits

## 🏗️ Architecture

```
trading_dashboard/
├── __init__.py          # Package init
├── app.py               # Flask app factory
├── config.py            # Trading constants & API config
├── api_client.py        # Async WEEX API wrapper
├── models.py            # Data models
├── utils.py             # Helper functions
├── routes/
│   ├── api.py           # Core trading endpoints
│   ├── ai.py            # AI analysis endpoints
│   └── automation.py    # Automation control
├── services/
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
git clone https://github.com/emmanuelakbi/RegimeForge-Alpha.git
cd RegimeForge-Alpha

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
# Deploy to production server
./deploy.sh
```

## 📊 API Endpoints

### Market Data

- `GET /api/price` - Current price ticker
- `GET /api/depth` - Order book depth
- `GET /api/klines` - Candlestick data

### Account

- `GET /api/balance` - Account balance
- `GET /api/position` - Current positions

### Trading

- `POST /api/trade` - Place manual trade
- `POST /api/close` - Close position

### AI

- `GET /api/ai/analyze` - Get AI signal
- `POST /api/ai/trade` - Execute AI-driven trade

### Automation

- `GET /api/automation/settings` - Get automation settings
- `POST /api/automation/settings` - Update settings
- `POST /api/automation/toggle` - Enable/disable automation

## 🔧 Tech Stack

- **Backend**: Python 3.x, Flask
- **HTTP Client**: httpx (async)
- **Frontend**: Vanilla JavaScript, CSS
- **Templates**: Jinja2
- **Production**: Gunicorn

## 🧪 Testing

```bash
python test_comprehensive.py
```

## ⚠️ Important Notes

- WEEX API requires IP whitelisting - ensure your server IP is whitelisted
- Always test with small amounts first
- The AI signals are for informational purposes - trade at your own risk

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

RegimeForge Alpha is provided for educational and research purposes. Cryptocurrency trading involves substantial risk of loss. Users are responsible for their own trading decisions and should never trade with funds they cannot afford to lose.

---

**RegimeForge Alpha**: AI-powered trading for the WEEX exchange.
