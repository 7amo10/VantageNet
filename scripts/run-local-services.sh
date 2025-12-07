#!/bin/bash

# ============================================
# VantageNet Local Services Runner
# ============================================
# This script runs the Python/PyTorch services locally
# using your my_env virtual environment instead of Docker.
# This saves storage and bandwidth by using your local PyTorch.
#
# Prerequisites:
# - Docker containers running (docker-compose up -d)
# - my_env virtual environment with PyTorch installed
# - Redis accessible at localhost:6380
# - PostgreSQL accessible at localhost:5434
# ============================================

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_PATH="${PYTHON_VENV_PATH:-$HOME/my_env}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     VantageNet Local Services Runner       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

# Check if virtual environment exists
if [ ! -d "$VENV_PATH" ]; then
    echo -e "${RED}Error: Virtual environment not found at $VENV_PATH${NC}"
    echo -e "${YELLOW}Please set PYTHON_VENV_PATH environment variable or create my_env${NC}"
    exit 1
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment: $VENV_PATH${NC}"
source "$VENV_PATH/bin/activate"

# Load environment variables
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${GREEN}Loading environment variables from .env${NC}"
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)
fi

# Set default environment variables for local services
export REDIS_HOST="${REDIS_HOST:-localhost}"
export REDIS_PORT="${REDIS_PORT:-6380}"
export POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
export POSTGRES_PORT="${POSTGRES_PORT:-5434}"
export POSTGRES_USER="${POSTGRES_USER:-vantage}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-vantage_secret}"
export POSTGRES_DB="${POSTGRES_DB:-vantage_db}"

# Function to check if a service is running
check_service() {
    local port=$1
    local name=$2
    if lsof -i :$port > /dev/null 2>&1; then
        echo -e "${YELLOW}Warning: Port $port ($name) is already in use${NC}"
        return 1
    fi
    return 0
}

# Function to start a service
start_service() {
    local service_name=$1
    local service_dir=$2
    local port=$3
    
    echo -e "${GREEN}Starting $service_name on port $port...${NC}"
    cd "$PROJECT_ROOT/services/$service_dir"
    
    # Install requirements if needed
    if [ -f "requirements.txt" ]; then
        pip install -q -r requirements.txt 2>/dev/null || true
    fi
    
    # Start the service in background using python -m
    python -m app.main > "/tmp/vantage_${service_name}.log" 2>&1 &
    echo $! > "/tmp/vantage_${service_name}.pid"
    echo -e "${GREEN}✓ $service_name started (PID: $!)${NC}"
}

# Main function
main() {
    case "${1:-start}" in
        start)
            echo -e "${BLUE}Checking Docker containers...${NC}"
            
            # Check if Redis is accessible (test with nc or docker exec)
            if docker exec vantage-redis redis-cli ping > /dev/null 2>&1; then
                echo -e "${GREEN}✓ Redis is accessible at localhost:6380${NC}"
            else
                echo -e "${RED}Error: Redis container is not running${NC}"
                echo -e "${YELLOW}Please run 'docker compose up -d' first${NC}"
                exit 1
            fi
            
            # Check if PostgreSQL is accessible
            if docker exec vantage-postgres pg_isready -U vantage > /dev/null 2>&1; then
                echo -e "${GREEN}✓ PostgreSQL is accessible at localhost:5434${NC}"
            else
                echo -e "${YELLOW}Warning: PostgreSQL container check failed${NC}"
            fi
            
            echo ""
            echo -e "${BLUE}Starting local Python services...${NC}"
            echo ""
            
            # Start services
            check_service 8001 "video-ingestion" && start_service "video-ingestion" "video-ingestion" 8001
            check_service 8002 "emotion-detection" && start_service "emotion-detection" "emotion-detection" 8002
            check_service 8003 "sentiment-analysis" && start_service "sentiment-analysis" "sentiment-analysis" 8003
            
            echo ""
            echo -e "${GREEN}╔════════════════════════════════════════════╗${NC}"
            echo -e "${GREEN}║     All local services started!            ║${NC}"
            echo -e "${GREEN}╚════════════════════════════════════════════╝${NC}"
            echo ""
            echo -e "${BLUE}Services:${NC}"
            echo -e "  • Video Ingestion:    http://localhost:8001"
            echo -e "  • Emotion Detection:  http://localhost:8002"
            echo -e "  • Sentiment Analysis: http://localhost:8003"
            echo ""
            echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
            
            # Wait for interrupt
            wait
            ;;
            
        stop)
            echo -e "${BLUE}Stopping local services...${NC}"
            for service in video-ingestion emotion-detection sentiment-analysis; do
                if [ -f "/tmp/vantage_${service}.pid" ]; then
                    pid=$(cat "/tmp/vantage_${service}.pid")
                    if kill -0 $pid 2>/dev/null; then
                        kill $pid
                        echo -e "${GREEN}✓ Stopped $service (PID: $pid)${NC}"
                    fi
                    rm "/tmp/vantage_${service}.pid"
                fi
            done
            echo -e "${GREEN}All services stopped${NC}"
            ;;
            
        status)
            echo -e "${BLUE}Service Status:${NC}"
            for port in 8001 8002 8003; do
                if lsof -i :$port > /dev/null 2>&1; then
                    echo -e "  Port $port: ${GREEN}RUNNING${NC}"
                else
                    echo -e "  Port $port: ${RED}STOPPED${NC}"
                fi
            done
            ;;
            
        *)
            echo "Usage: $0 {start|stop|status}"
            exit 1
            ;;
    esac
}

# Handle Ctrl+C
trap 'echo -e "\n${YELLOW}Stopping services...${NC}"; $0 stop; exit 0' INT TERM

main "$@"
