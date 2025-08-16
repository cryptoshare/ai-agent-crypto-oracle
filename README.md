# AI Agent Crypto

A comprehensive AI-powered cryptocurrency analysis and trading system with sentiment oracle capabilities.

## Project Structure

```
AI AGENT CRYPTO/
├── venv/                 # Virtual environment
├── oracle/              # Sentiment Oracle FastAPI application
│   ├── app.py           # Main FastAPI application
│   ├── scoring.py       # Sentiment scoring algorithms
│   ├── providers.py     # OpenAI API integration
│   ├── settings.py      # Configuration management
│   ├── requirements.txt # Oracle dependencies
│   ├── Dockerfile      # Container configuration
│   ├── README.md       # Oracle documentation
│   └── env.example     # Environment template
├── requirements.txt     # Main project dependencies
├── README.md           # This file
└── src/                # Additional source code
```

## Quick Start

### 1. Setup Virtual Environment

```bash
# Activate virtual environment
source venv/bin/activate

# Install main dependencies
pip install -r requirements.txt
```

### 2. Oracle Setup

```bash
# Navigate to oracle directory
cd oracle

# Copy environment template
cp env.example .env

# Edit .env with your OpenAI API key
# OPENAI_API_KEY=sk-your-key-here

# Install oracle dependencies
pip install -r requirements.txt

# Run locally
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### 3. Test Oracle

```bash
# Health check
curl http://localhost:8000/health

# Run sentiment analysis
curl "http://localhost:8000/oracle/run?window=2h"
```

## Deployment

### Railway Deployment

1. Push the `oracle/` folder to GitHub
2. Create Railway project → "Deploy from Repo"
3. Set Root Directory to `oracle`
4. Add environment variables from `env.example`
5. Deploy and test endpoints

### Make.com Integration

Set up automated sentiment analysis every 2 hours:
- Scheduler: Every 2 hours
- HTTP Request: GET `https://<your-app>.railway.app/oracle/run?window=2h`

## Features

- **Real-time sentiment analysis** using OpenAI's web search
- **Deterministic scoring** across news, macro, geopolitics, and crypto context
- **Trading regime detection** (RISK_ON, RISK_OFF, NEUTRAL)
- **Automated trading guidance** with risk parameters
- **Docker-ready** for easy deployment
- **Make.com integration** for automated scheduling

## Documentation

- [Oracle Documentation](./oracle/README.md) - Complete setup and API reference
- [Environment Configuration](./oracle/env.example) - Configuration template
