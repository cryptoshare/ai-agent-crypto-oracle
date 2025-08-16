# AI Agent Crypto Oracle

A FastAPI-based sentiment oracle that uses OpenAI's Responses API with web search to analyze crypto market sentiment and provide trading guidance.

## Features

- **Real-time sentiment analysis** using OpenAI's web search capabilities
- **Deterministic scoring** with weighted sentiment across multiple categories
- **Trading regime detection** (RISK_ON, RISK_OFF, NEUTRAL)
- **Automated guidance** for trading parameters
- **Docker-ready** for easy deployment

## Quick Start

### 1. Environment Setup

Copy the environment template and configure your settings:

```bash
cp env.example .env
# Edit .env with your OpenAI API key and preferences
```

### 2. Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### 3. Test Endpoints

```bash
# Health check
curl http://localhost:8000/health

# Run oracle analysis
curl "http://localhost:8000/oracle/run?window=2h"
```

## Docker Deployment

### Build and Run Locally

```bash
docker build -t crypto-oracle .
docker run -p 8000:8000 --env-file .env crypto-oracle
```

### Railway Deployment

1. **Push to GitHub** - Create a repository and push this folder
2. **Create Railway Project** - "Deploy from Repo"
3. **Configure Environment** - Add variables from `env.example`
4. **Set Root Directory** - If mono-repo, set to `oracle`
5. **Deploy** - Railway will build using the Dockerfile

### Verify Deployment

```bash
# Health check
curl https://<your-app>.railway.app/health

# Test oracle
curl "https://<your-app>.railway.app/oracle/run?window=2h"
```

## Make.com Integration

Create a scenario "Sentiment Oracle (2h)":

**Module 1 - Scheduler:**
- Every 2 hours

**Module 2 - HTTP Request:**
- Method: GET
- URL: `https://<your-app>.railway.app/oracle/run?window=2h`
- Expect: JSON

## API Endpoints

### GET /health
Health check endpoint.

**Response:**
```json
{"ok": true}
```

### GET /oracle/run
Run sentiment analysis with optional time window.

**Parameters:**
- `window` (optional): Time window (e.g., "2h", "1h")

**Response:**
```json
{
  "at": "2024-01-15T10:30:00Z",
  "window": "2h",
  "scores": {
    "news": 0.3,
    "macro": -0.1,
    "geopolitics": 0.0,
    "btc_eth_context": 0.2
  },
  "composite": 0.15,
  "regime": "NEUTRAL",
  "guidance": {
    "allow_new_trades": true,
    "direction_bias": "both",
    "risk_budget_pct": 0.30,
    "daily_dd_cap_pct": 2.0,
    "max_leverage": 3.0,
    "do_not_trade_until": null
  },
  "items": [...],
  "notes": "Analysis summary"
}
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key | Required |
| `OPENAI_MODEL` | OpenAI model to use | `gpt-4.5-mini` |
| `ALLOWED_DOMAINS` | Comma-separated trusted news domains | `reuters.com,coindesk.com,theblock.co` |
| `QUERY_PACK` | Semicolon-separated search queries | `BTC ETH driver;exchange hack exploit` |
| `DEFAULT_WINDOW` | Default time window for analysis | `2h` |

### Scoring Weights

The composite score uses these weights:
- News: 40%
- Macro: 20%
- Geopolitics: 10%
- BTC/ETH Context: 30%

### Regime Thresholds

- **RISK_ON**: Composite > 0.25
- **RISK_OFF**: Composite < -0.25
- **NEUTRAL**: Between thresholds

## Project Structure

```
oracle/
├── app.py              # FastAPI application
├── scoring.py          # Sentiment scoring algorithms
├── providers.py        # OpenAI API integration
├── settings.py         # Configuration management
├── requirements.txt    # Python dependencies
├── Dockerfile         # Container configuration
├── README.md          # This file
└── env.example        # Environment template
```

## Development

### Adding New Sentiment Categories

1. Update `normalize_items()` in `scoring.py`
2. Add keywords for categorization
3. Update `composite_score()` weights
4. Test with sample data

### Extending Trading Guidance

Modify `default_guidance()` in `scoring.py` to add new parameters or adjust existing ones based on your trading strategy.

## Troubleshooting

### Common Issues

1. **OpenAI API Errors**: Check your API key and model availability
2. **JSON Parse Errors**: The system will return a failsafe response
3. **Timeout Issues**: Increase timeout in `providers.py` if needed

### Logs

Check application logs for detailed error information:

```bash
# Local
uvicorn app:app --log-level debug

# Docker
docker logs <container-id>
```

## License

MIT License - see LICENSE file for details.
