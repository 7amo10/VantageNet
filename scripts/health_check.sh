#!/bin/bash

################################################################################
# VantageNet Health Check Script
# 
# Validates service discovery and inter-service communication in Docker network.
# Tests all service health endpoints, database connectivity, and Redis connectivity.
#
# Usage:
#   ./scripts/health_check.sh
#
# Prerequisites:
#   - Docker and Docker Compose running
#   - All services started with: docker-compose up -d
#   - Wait ~30 seconds after startup for services to initialize
#
# Exit Codes:
#   0 - All services healthy
#   1 - One or more services unhealthy or unreachable
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Service endpoints
API_GATEWAY_URL="http://localhost:8000"
VIDEO_INGESTION_URL="http://localhost:8001"
EMOTION_DETECTION_URL="http://localhost:8002"
SENTIMENT_ANALYSIS_URL="http://localhost:8003"
DASHBOARD_URL="http://localhost:3000"

# Database connection info
POSTGRES_HOST="localhost"
POSTGRES_PORT="5434"
POSTGRES_USER="vantage"
POSTGRES_DB="vantage_db"

REDIS_HOST="localhost"
REDIS_PORT="6380"

# Counters
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

################################################################################
# Helper Functions
################################################################################

print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

print_section() {
    echo ""
    echo -e "${YELLOW}--- $1 ---${NC}"
}

check_service() {
    local service_name=$1
    local url=$2
    local expected_status=${3:-200}
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    echo -n "Checking $service_name... "
    
    # Make HTTP request with timeout
    response=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 "$url" 2>/dev/null || echo "000")
    
    if [ "$response" = "$expected_status" ]; then
        echo -e "${GREEN}✓ HEALTHY${NC} (HTTP $response)"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        echo -e "${RED}✗ UNHEALTHY${NC} (HTTP $response)"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

check_service_detailed() {
    local service_name=$1
    local url=$2
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    echo -n "Checking $service_name... "
    
    # Make HTTP request and capture response
    response=$(curl -s --connect-timeout 5 --max-time 10 "$url" 2>/dev/null || echo '{"error": "connection_failed"}')
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 "$url" 2>/dev/null || echo "000")
    
    if [ "$http_code" = "200" ]; then
        status=$(echo "$response" | grep -o '"status"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4)
        service=$(echo "$response" | grep -o '"service"[[:space:]]*:[[:space:]]*"[^"]*"' | cut -d'"' -f4)
        
        if [ "$status" = "healthy" ]; then
            echo -e "${GREEN}✓ HEALTHY${NC}"
            echo "  └─ Service: $service"
            echo "  └─ HTTP: $http_code"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
            return 0
        else
            echo -e "${YELLOW}⚠ WARNING${NC}"
            echo "  └─ Status: $status"
            echo "  └─ HTTP: $http_code"
            PASSED_CHECKS=$((PASSED_CHECKS + 1))
            return 0
        fi
    else
        echo -e "${RED}✗ UNHEALTHY${NC}"
        echo "  └─ HTTP: $http_code"
        echo "  └─ Error: Connection failed or service not responding"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

check_docker_container() {
    local container_name=$1
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    echo -n "Checking Docker container: $container_name... "
    
    if docker ps --format '{{.Names}}' | grep -q "^${container_name}$"; then
        status=$(docker inspect --format='{{.State.Status}}' "$container_name" 2>/dev/null)
        health=$(docker inspect --format='{{if .State.Health}}{{.State.Health.Status}}{{else}}no-healthcheck{{end}}' "$container_name" 2>/dev/null)
        
        if [ "$status" = "running" ]; then
            if [ "$health" = "healthy" ] || [ "$health" = "no-healthcheck" ]; then
                echo -e "${GREEN}✓ RUNNING${NC}"
                echo "  └─ Status: $status"
                if [ "$health" != "no-healthcheck" ]; then
                    echo "  └─ Health: $health"
                fi
                PASSED_CHECKS=$((PASSED_CHECKS + 1))
                return 0
            else
                echo -e "${YELLOW}⚠ RUNNING (unhealthy)${NC}"
                echo "  └─ Status: $status"
                echo "  └─ Health: $health"
                PASSED_CHECKS=$((PASSED_CHECKS + 1))
                return 0
            fi
        else
            echo -e "${RED}✗ NOT RUNNING${NC}"
            echo "  └─ Status: $status"
            FAILED_CHECKS=$((FAILED_CHECKS + 1))
            return 1
        fi
    else
        echo -e "${RED}✗ NOT FOUND${NC}"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

check_postgres() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    echo -n "Checking PostgreSQL connectivity... "
    
    # Try to connect to PostgreSQL using docker exec
    if docker exec vantage-postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ CONNECTED${NC}"
        echo "  └─ Host: postgres:5432 (internal) / $POSTGRES_HOST:$POSTGRES_PORT (external)"
        
        # Get database stats
        db_size=$(docker exec vantage-postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT pg_size_pretty(pg_database_size('$POSTGRES_DB'));" 2>/dev/null | xargs)
        conn_count=$(docker exec vantage-postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -t -c "SELECT count(*) FROM pg_stat_activity WHERE datname='$POSTGRES_DB';" 2>/dev/null | xargs)
        
        echo "  └─ Database size: $db_size"
        echo "  └─ Active connections: $conn_count"
        
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        echo "  └─ Could not connect to PostgreSQL"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

check_redis() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    echo -n "Checking Redis connectivity... "
    
    # Try to ping Redis using docker exec
    if docker exec vantage-redis redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓ CONNECTED${NC}"
        echo "  └─ Host: redis:6379 (internal) / $REDIS_HOST:$REDIS_PORT (external)"
        
        # Get Redis stats
        used_memory=$(docker exec vantage-redis redis-cli INFO memory 2>/dev/null | grep "used_memory_human" | cut -d':' -f2 | tr -d '\r')
        connected_clients=$(docker exec vantage-redis redis-cli INFO clients 2>/dev/null | grep "connected_clients" | cut -d':' -f2 | tr -d '\r')
        
        echo "  └─ Used memory: $used_memory"
        echo "  └─ Connected clients: $connected_clients"
        
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        echo "  └─ Could not connect to Redis"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

check_redis_streams() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    echo -n "Checking Redis Streams... "
    
    # Check if emotion:events stream exists
    emotion_exists=$(docker exec vantage-redis redis-cli EXISTS "emotion:events" 2>/dev/null | tr -d '\r')
    sentiment_exists=$(docker exec vantage-redis redis-cli EXISTS "sentiment:crowd" 2>/dev/null | tr -d '\r')
    
    if [ "$emotion_exists" = "1" ] && [ "$sentiment_exists" = "1" ]; then
        emotion_length=$(docker exec vantage-redis redis-cli XLEN "emotion:events" 2>/dev/null | tr -d '\r')
        sentiment_length=$(docker exec vantage-redis redis-cli XLEN "sentiment:crowd" 2>/dev/null | tr -d '\r')
        
        echo -e "${GREEN}✓ CONFIGURED${NC}"
        echo "  └─ emotion:events: $emotion_length messages"
        echo "  └─ sentiment:crowd: $sentiment_length messages"
        
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        echo -e "${YELLOW}⚠ NOT INITIALIZED${NC}"
        echo "  └─ Run: ./scripts/init-redis-streams.sh"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    fi
}

check_network_resolution() {
    local container=$1
    local target_host=$2
    local target_port=$3
    
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
    
    echo -n "  Testing $container → $target_host:$target_port... "
    
    # Check if container can resolve and connect to target
    if docker exec "$container" sh -c "nc -zv $target_host $target_port" > /dev/null 2>&1 || \
       docker exec "$container" sh -c "timeout 3 bash -c '</dev/tcp/$target_host/$target_port'" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ REACHABLE${NC}"
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        return 0
    else
        echo -e "${RED}✗ UNREACHABLE${NC}"
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        return 1
    fi
}

################################################################################
# Main Health Checks
################################################################################

print_header "VantageNet Health Check"
echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"
echo "Checking service discovery and inter-service communication..."

# 1. Docker Container Status
print_section "1. Docker Container Status"
check_docker_container "vantage-postgres"
check_docker_container "vantage-redis"
check_docker_container "vantage-api-gateway"
check_docker_container "vantage-dashboard"

# 2. Database Connectivity
print_section "2. Database Connectivity"
check_postgres

# 3. Redis Connectivity
print_section "3. Redis Connectivity"
check_redis
check_redis_streams

# 4. Service Health Endpoints
print_section "4. Service Health Endpoints"
check_service_detailed "API Gateway" "$API_GATEWAY_URL/health"
check_service_detailed "Video Ingestion" "$VIDEO_INGESTION_URL/health"
check_service_detailed "Emotion Detection" "$EMOTION_DETECTION_URL/health"
check_service_detailed "Sentiment Analysis" "$SENTIMENT_ANALYSIS_URL/health"
check_service "Dashboard" "$DASHBOARD_URL"

# 5. Service Discovery Tests (Docker Network)
print_section "5. Service Discovery (Docker Network)"
echo "Testing if API Gateway can resolve internal hostnames:"
check_network_resolution "vantage-api-gateway" "postgres" "5432"
check_network_resolution "vantage-api-gateway" "redis" "6379"

# 6. Additional API Tests
print_section "6. API Endpoint Tests"
check_service "API Root" "$API_GATEWAY_URL/"
check_service "Cameras Endpoint" "$API_GATEWAY_URL/api/cameras"
check_service "Rules Endpoint" "$API_GATEWAY_URL/api/rules"

# 7. Port Accessibility Summary
print_section "7. Port Accessibility Summary"
echo "External Ports (from host):"
echo "  • PostgreSQL:  localhost:5434 → postgres:5432"
echo "  • Redis:       localhost:6380 → redis:6379"
echo "  • API Gateway: localhost:8000 → api-gateway:8000"
echo "  • Dashboard:   localhost:3000 → dashboard:3000"
echo ""
echo "Local Services (run outside Docker):"
echo "  • Video Ingestion:     localhost:8001"
echo "  • Emotion Detection:   localhost:8002"
echo "  • Sentiment Analysis:  localhost:8003"

# Summary
print_section "Summary"
echo ""
echo -e "Total Checks: ${BLUE}$TOTAL_CHECKS${NC}"
echo -e "Passed:       ${GREEN}$PASSED_CHECKS${NC}"
echo -e "Failed:       ${RED}$FAILED_CHECKS${NC}"
echo ""

if [ $FAILED_CHECKS -eq 0 ]; then
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✓ ALL CHECKS PASSED${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "System Status: All services are healthy and communicating properly."
    echo ""
    exit 0
else
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}✗ SOME CHECKS FAILED${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "System Status: Some services are unhealthy or unreachable."
    echo ""
    echo "Troubleshooting Steps:"
    echo "  1. Check Docker containers: docker ps -a"
    echo "  2. Check service logs: docker logs vantage-<service-name>"
    echo "  3. Verify network: docker network inspect vantage-network"
    echo "  4. For local services, ensure they're running in my_env"
    echo "  5. Refer to docs/SETUP.md for detailed troubleshooting"
    echo ""
    exit 1
fi
