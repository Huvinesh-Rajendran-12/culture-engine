#!/bin/bash

# FlowForge Backend Startup Script

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting FlowForge Backend...${NC}"

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found${NC}"
    echo -e "Creating .env from .env.example..."
    cp .env.example .env
    echo -e "${RED}Please update .env with your ANTHROPIC_API_KEY before running again${NC}"
    exit 1
fi

# Check if ANTHROPIC_API_KEY is set
source .env
if [ -z "$ANTHROPIC_API_KEY" ] || [ "$ANTHROPIC_API_KEY" = "your_api_key_here" ]; then
    echo -e "${RED}Error: ANTHROPIC_API_KEY not configured in .env${NC}"
    echo -e "Please set your Anthropic API key in the .env file"
    exit 1
fi

# Sync dependencies
echo -e "${GREEN}Syncing dependencies...${NC}"
uv sync

# Start the server
echo -e "${GREEN}Starting FastAPI server...${NC}"
echo -e "API: http://localhost:8000"
echo -e "Docs: http://localhost:8000/docs"
echo ""

uv run uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
