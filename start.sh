#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting ASPL Environment...${NC}"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    playwright install chromium
else
    source venv/bin/activate
fi

# Check if Redis is running (optional but good)
if ! pgrep -x "redis-server" > /dev/null; then
    echo "Redis is not running. Starting Redis (if installed)..."
    # Try to start redis if available, otherwise warn
    if command -v redis-server &> /dev/null; then
        redis-server --daemonize yes
    else
        echo "Redis not found. Falling back to in-memory cache."
    fi
fi

echo -e "${GREEN}Launching API Server...${NC}"
echo "Access Swagger UI at: http://127.0.0.1:8000/docs"

# Run the server
uvicorn src.main:app --reload --port 8000
