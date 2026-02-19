# Crypto Trade Analysis API

A professional, production-ready FastAPI service for fetching cryptocurrency OHLCV (Open, High, Low, Close, Volume) data and technical indicators using ccxt.

## Features

- 🚀 **FastAPI** - Modern, fast web framework for building APIs
- 📊 **Technical Indicators** - EMA (20, 50, 200), RSI (14), ATR (14)
- 🔌 **Multi-Exchange Support** - Powered by ccxt library
- 🐳 **Docker Ready** - Easy deployment with Docker and docker-compose
- ✅ **Type Safe** - Full type hints with mypy strict mode
- 🧪 **Tested** - Comprehensive test suite with pytest
- 📝 **Well Documented** - Clear API documentation with FastAPI's built-in docs

## Quick Start

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/Nfectious/crypto-trade-analysis.git
   cd crypto-trade-analysis
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Create environment file** (optional)
   ```bash
   cp .env.example .env
   # Edit .env to customize settings
   ```

5. **Run the application**
   ```bash
   uvicorn app.main:app --reload
   ```

6. **Access the API**
   - API: http://localhost:8000
   - Interactive docs: http://localhost:8000/docs
   - Alternative docs: http://localhost:8000/redoc

### Using Docker

1. **Build and run with docker-compose**
   ```bash
   docker-compose up --build
   ```

2. **Access the API**
   - API: http://localhost:8000
   - Interactive docs: http://localhost:8000/docs

## API Endpoints

### Health Check
```bash
GET /
```
Returns service status.

**Response:**
```json
{
  "status": "ok",
  "message": "Simple Crypto Data API is running"
}
```

### Live Market Data
```bash
GET /api/v1/live_data
```

**Query Parameters:**
- `symbol` (string, default: "BTC/USDT") - Trading pair symbol
- `timeframe` (string, default: "1h") - Candle timeframe (e.g., "1m", "5m", "1h", "1d")
- `limit` (integer, default: 250, range: 20-2000) - Number of candles to fetch
- `exchange` (string, default: "binance") - Exchange name

**Example Request:**
```bash
curl "http://localhost:8000/api/v1/live_data?symbol=BTC/USDT&timeframe=1h&limit=100"
```

**Response:**
```json
{
  "symbol": "BTC/USDT",
  "timeframe": "1h",
  "exchange": "binance",
  "last_price": 43250.5,
  "last_timestamp": "2024-01-15T12:00:00Z",
  "candles_count": 100,
  "recent_candles": [
    {
      "timestamp": "2024-01-15T12:00:00Z",
      "open": 43200.0,
      "high": 43300.0,
      "low": 43150.0,
      "close": 43250.5,
      "volume": 125.5,
      "ema_20": 43180.2,
      "ema_50": 43050.8,
      "ema_200": null,
      "rsi_14": 55.3,
      "atr_14": 150.2
    }
  ],
  "latest_indicators": {
    "ema_20": 43180.2,
    "ema_50": 43050.8,
    "ema_200": null,
    "rsi_14": 55.3,
    "atr_14": 150.2
  },
  "meta": {}
}
```

**Note about null values:** Technical indicators may return `null` for early candles where there isn't enough historical data to calculate the indicator. For example:
- EMA-20 requires at least 20 candles
- EMA-50 requires at least 50 candles
- EMA-200 requires at least 200 candles
- RSI-14 requires at least 14 candles
- ATR-14 requires at least 14 candles

### WebSocket Live Data Stream
```
WS /api/v1/live_data/ws
```

Streams real-time market data with technical indicators at regular intervals.

**Query Parameters:**
- `symbol` (string, default: "BTC/USDT") - Trading pair symbol
- `timeframe` (string, default: "1h") - Candle timeframe (e.g., "1m", "5m", "1h", "1d")
- `limit` (integer, default: 250, range: 20-2000) - Number of candles to fetch
- `exchange` (string, default: "binance") - Exchange name
- `interval` (integer, default: 5, range: 1-60) - Update interval in seconds

**Example Connection:**
```javascript
const ws = new WebSocket("ws://localhost:8000/api/v1/live_data/ws?symbol=BTC/USDT&interval=5");

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("Received:", data);
};
```

The WebSocket will send a JSON payload every `interval` seconds with the same structure as the REST API response. If there's an error fetching data, the WebSocket will send an error object instead:

```json
{
  "error": "network_error",
  "message": "Network error connecting to exchange: ...",
  "status_code": 503
}
```

## Technical Indicators

The API calculates the following technical indicators using the `ta` library:

- **EMA (Exponential Moving Average)**: 20, 50, and 200 periods
- **RSI (Relative Strength Index)**: 14 period (momentum oscillator)
- **ATR (Average True Range)**: 14 period (volatility indicator)

## Development

### Running Tests
```bash
pytest
```

### Linting
```bash
ruff check .
```

### Type Checking
```bash
mypy src/
```

### Code Formatting
```bash
ruff check --fix .
```

## Configuration

Configuration is managed through environment variables. Copy `.env.example` to `.env` and customize as needed:

```env
# Application Configuration
APP_NAME="Simple Crypto Data API"
API_PREFIX="/api/v1"

# Exchange Configuration
DEFAULT_EXCHANGE="binance"
DEFAULT_MARKET_TYPE="spot"

# Rate Limiting
ENABLE_RATE_LIMIT=true
```

## Project Structure

```
crypto-trade-analysis/
├── src/
│   └── app/
│       ├── __init__.py
│       ├── main.py              # FastAPI application
│       ├── api/
│       │   ├── __init__.py
│       │   └── v1/
│       │       ├── __init__.py
│       │       ├── routes_live_data.py  # REST API endpoints
│       │       └── ws_live_data.py      # WebSocket endpoints
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py        # Application settings
│       │   └── logging.py       # Logging configuration
│       ├── integrations/
│       │   ├── __init__.py
│       │   └── exchanges.py     # ccxt exchange wrapper
│       ├── schemas/
│       │   ├── __init__.py
│       │   └── live_data.py     # Pydantic models
│       └── services/
│           ├── __init__.py
│           ├── indicators.py    # Technical indicators
│           └── market_data.py   # Market data processing
├── tests/
│   ├── __init__.py
│   ├── test_health.py
│   ├── test_live_data.py
│   └── test_live_data_mocked.py  # Mocked tests for CI
├── .github/
│   └── workflows/
│       └── ci.yml              # GitHub Actions CI
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── .gitignore
├── .env.example
└── README.md
```

## CI/CD

The project uses GitHub Actions for continuous integration. On every push and pull request, the workflow:

1. Installs dependencies
2. Runs ruff linting
3. Runs mypy type checking
4. Runs pytest tests

See `.github/workflows/ci.yml` for details.

## Error Handling

The API handles various error conditions gracefully:

- **Network Errors** (503): Issues connecting to the exchange
- **Exchange Errors** (400): Invalid parameters or exchange-specific errors
- **Validation Errors** (422): Invalid query parameters
- **Internal Errors** (500): Unexpected server errors

## License

This project is open source and available for educational and commercial use.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.