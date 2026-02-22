#!/bin/bash

# Culture Engine Backend startup script

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}Starting Culture Engine Backend...${NC}"

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found${NC}"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo -e "${RED}Please configure .env with your API credentials before running again${NC}"
    exit 1
fi

# Export all env vars so the backend and model adapter can access them
set -a
source .env
set +a

# Validate that at least one auth method is configured
if [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$ANTHROPIC_AUTH_TOKEN" ]; then
    echo -e "${RED}Error: No API credentials configured in .env${NC}"
    echo "Set either ANTHROPIC_API_KEY (direct) or ANTHROPIC_AUTH_TOKEN (OpenRouter)"
    exit 1
fi

if [ "$ANTHROPIC_API_KEY" = "your_anthropic_api_key_here" ]; then
    echo -e "${RED}Error: ANTHROPIC_API_KEY has not been updated from the placeholder${NC}"
    exit 1
fi

# Sync dependencies
echo -e "${GREEN}Syncing dependencies...${NC}"
uv sync

# Start the server
echo -e "${GREEN}Starting FastAPI server...${NC}"
echo "API: http://localhost:8100"
echo "Docs: http://localhost:8100/docs"
echo ""

uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8100
