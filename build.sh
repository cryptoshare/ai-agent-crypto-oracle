#!/bin/bash
# Build script for Railway deployment

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Installing uvicorn specifically..."
pip install uvicorn[standard]

echo "Starting application..."
echo "PORT environment variable: $PORT"
cd oracle
uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}
