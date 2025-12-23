#!/bin/bash

# ============================================
# Register Laptop Webcam Camera
# ============================================
# This script registers your laptop's webcam with the video-ingestion service
# ============================================

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Register Laptop Webcam to VantageNet    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════╝${NC}"
echo ""

# Configuration
API_URL="${API_URL:-http://localhost:8000}"
CAMERA_NAME="${CAMERA_NAME:-Laptop Webcam}"
WEBCAM_INDEX="${WEBCAM_INDEX:-0}"

# Check if API is accessible
echo -e "${YELLOW}Checking API Gateway connectivity...${NC}"
if ! curl -s -f "$API_URL/health" > /dev/null 2>&1; then
    echo -e "${RED}Error: API Gateway is not responding at $API_URL${NC}"
    echo -e "${YELLOW}Please make sure services are running:${NC}"
    echo "  ./scripts/run-local-services.sh"
    exit 1
fi

echo -e "${GREEN}✓ API Gateway is running${NC}"
echo ""

# Register webcam camera
echo -e "${YELLOW}Registering webcam camera...${NC}"
RESPONSE=$(curl -s -X POST "$API_URL/api/cameras/" \
    -H "Content-Type: application/json" \
    -d "{
        \"name\": \"$CAMERA_NAME\",
        \"source_type\": \"webcam\",
        \"source_url\": \"$WEBCAM_INDEX\",
        \"fps\": 10,
        \"enabled\": true,
        \"metadata\": {
            \"location\": \"Local\",
            \"type\": \"Laptop Webcam\"
        }
    }")

# Check if registration was successful
if echo "$RESPONSE" | grep -q '"camera_id"'; then
    CAMERA_ID=$(echo "$RESPONSE" | grep -o '"camera_id":"[^"]*"' | cut -d'"' -f4)
    echo -e "${GREEN}✓ Webcam registered successfully!${NC}"
    echo ""
    echo -e "${BLUE}Camera Details:${NC}"
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    echo ""
    echo -e "${GREEN}✓ Camera ID: $CAMERA_ID${NC}"
    echo -e "${GREEN}✓ You can now select this camera in the dashboard!${NC}"
else
    echo -e "${RED}✗ Failed to register webcam${NC}"
    echo "Response: $RESPONSE"
    exit 1
fi
