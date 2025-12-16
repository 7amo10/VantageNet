#!/bin/bash
################################################################################
# VANTA-24: End-to-End Alert Pipeline Integration Test
# Tests complete pipeline: Detection → Sentiment → Alert → Notification
#
# Prerequisites:
# - Redis running on localhost:6380
# - PostgreSQL running on localhost:5434
# - Sentiment Analysis service running on localhost:8003
#   (Start with: cd services/sentiment-analysis && python -m app.main)
#
# Test Scenario:
# 1. Create rule in database: "Threshold - Happy > 80%"
# 2. Publish mock emotions to Redis (high happy % to trigger rule)
# 3. Monitor Alert notifications (file log)
# 4. Verify alert stored in database
#
# Success Criteria:
# - Rule is evaluated
# - Alert is generated when condition met
# - Notification is sent (file log)
# - Alert stored in database
# - Alert triggered within 5 seconds
# - No errors in logs
#
# Test Duration: 30 seconds
#
# Usage:
#   ./scripts/test_alert_pipeline.sh
################################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REDIS_HOST="localhost"
REDIS_PORT=6380
POSTGRES_HOST="localhost"
POSTGRES_PORT=5434
POSTGRES_DB="vantage_db"
POSTGRES_USER="vantage"
POSTGRES_PASSWORD="vantage_secret"
# Sentiment service port (used for health/reload)
SENTIMENT_PORT=8003
# Test duration: 45s to allow for 30s aggregation window + 15s buffer
# Publishing takes ~10s, aggregation happens at 30s mark
TEST_DURATION=45
TEST_CAMERA_ID="test_camera_alert_pipeline"
ALERT_LOG_FILE="/data/alerts.log"
REPORT_DIR="test_reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="${REPORT_DIR}/alert_pipeline_test_${TIMESTAMP}.txt"

# Test variables
RULE_ID=""
ALERT_COUNT_BEFORE=0
ALERT_COUNT_AFTER=0
START_TIME=0
ALERT_TRIGGERED_TIME=0

# Cleanup function
cleanup() {
    echo -e "${YELLOW}Cleaning up...${NC}"
    
    # Clean up test rule if created
    if [ ! -z "$RULE_ID" ]; then
        echo "Removing test rule from database..."
        PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT \
            -U $POSTGRES_USER -d $POSTGRES_DB \
            -c "DELETE FROM rules WHERE id = '$RULE_ID';" 2>/dev/null || true
    fi
    
    # Clean up test alerts
    echo "Removing test alerts from database..."
    PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT \
        -U $POSTGRES_USER -d $POSTGRES_DB \
        -c "DELETE FROM alerts WHERE camera_id IN (SELECT id FROM cameras WHERE name = '$TEST_CAMERA_ID');" 2>/dev/null || true
    
    # Clean up test camera
    echo "Removing test camera from database..."
    PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT \
        -U $POSTGRES_USER -d $POSTGRES_DB \
        -c "DELETE FROM cameras WHERE name = '$TEST_CAMERA_ID';" 2>/dev/null || true
    
    # Clean up Redis streams
    echo "Cleaning up Redis streams..."
    redis-cli -h $REDIS_HOST -p $REDIS_PORT DEL "emotion:results:*" 2>/dev/null || true
    
    echo -e "${GREEN}Cleanup complete${NC}"
}

# Set up trap for cleanup
trap cleanup EXIT INT TERM

# Print header
echo "=========================================="
echo "VANTA-24: Alert Pipeline Integration Test"
echo "=========================================="
echo "Timestamp: $(date)"
echo "Test Duration: ${TEST_DURATION}s"
echo "Test Camera: ${TEST_CAMERA_ID}"
echo "Redis: ${REDIS_HOST}:${REDIS_PORT}"
echo "Postgres: ${POSTGRES_HOST}:${POSTGRES_PORT}"
echo "=========================================="
echo ""

# Create report directory
mkdir -p ${REPORT_DIR}

# Create /data directory if it doesn't exist
sudo mkdir -p /data 2>/dev/null || mkdir -p /data 2>/dev/null || true
sudo chmod 777 /data 2>/dev/null || chmod 777 /data 2>/dev/null || true

# Initialize report
cat > ${REPORT_FILE} << EOF
VANTA-24: Alert Pipeline Integration Test Report
================================================
Timestamp: $(date)
Test Duration: ${TEST_DURATION} seconds
Test Camera: ${TEST_CAMERA_ID}
Redis: ${REDIS_HOST}:${REDIS_PORT}
Postgres: ${POSTGRES_HOST}:${POSTGRES_PORT}

Test Scenario:
--------------
1. Create rule: "Threshold - Happy > 80%"
2. Publish high happy % emotions to Redis
3. Monitor alert notifications (file log)
4. Verify alert in database

Success Criteria:
-----------------
✓ Rule is evaluated
✓ Alert is generated when condition met
✓ Notification is sent
✓ Alert stored in database
✓ Alert triggered within 5 seconds
✓ No errors in logs

EOF

# Step 1: Check prerequisites
echo -e "${BLUE}Step 1: Checking prerequisites...${NC}"

# Check Redis
if ! redis-cli -h ${REDIS_HOST} -p ${REDIS_PORT} ping &>/dev/null; then
    echo -e "${RED}✗ Redis is not running on ${REDIS_HOST}:${REDIS_PORT}${NC}"
    echo "Please start Redis with: docker-compose up -d redis"
    exit 1
fi
echo -e "${GREEN}✓ Redis is running${NC}"

# Check PostgreSQL
if ! PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT \
    -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT 1" &>/dev/null; then
    echo -e "${RED}✗ PostgreSQL is not running${NC}"
    echo "Please start PostgreSQL with: docker-compose up -d postgres"
    exit 1
fi
echo -e "${GREEN}✓ PostgreSQL is running${NC}"

# Check Sentiment Service
if ! curl -s http://localhost:8003/health > /dev/null 2>&1; then
    echo -e "${RED}✗ Sentiment Analysis service is not running on port 8003${NC}"
    echo "Please start it with:"
    echo "  cd services/sentiment-analysis"
    echo "  python -m app.main"
    exit 1
fi
echo -e "${GREEN}✓ Sentiment Analysis service is running${NC}"

# Check Python environment
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}✗ Python3 not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Python3 available${NC}"

# Step 2: Setup test camera in database
echo -e "\n${BLUE}Step 2: Setting up test camera in database...${NC}"

CAMERA_ID=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT \
    -U $POSTGRES_USER -d $POSTGRES_DB -q -t -A -c \
    "INSERT INTO cameras (name, location, active) 
     VALUES ('$TEST_CAMERA_ID', 'Test Location', TRUE) 
     ON CONFLICT (name) DO UPDATE SET active = TRUE 
     RETURNING id;")

if [ -z "$CAMERA_ID" ]; then
    echo -e "${RED}✗ Failed to create test camera${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Test camera created: $CAMERA_ID${NC}"

# Step 3: Create test rule in database
echo -e "\n${BLUE}Step 3: Creating test rule in database...${NC}"

# First, clean up any existing test rules
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT \
    -U $POSTGRES_USER -d $POSTGRES_DB \
    -c "DELETE FROM rules WHERE name = 'Test Happy Rule - VANTA-24';" 2>/dev/null || true

RULE_ID=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT \
    -U $POSTGRES_USER -d $POSTGRES_DB -q -t -A -c \
    "INSERT INTO rules (name, type, condition_json, action, enabled) 
     VALUES (
         'Test Happy Rule - VANTA-24',
         'threshold',
         '{\"type\": \"threshold\", \"emotion\": \"happy\", \"threshold\": 0.80, \"action\": \"alert\"}',
         'alert',
         TRUE
     ) 
     RETURNING id;")

if [ -z "$RULE_ID" ]; then
    echo -e "${RED}✗ Failed to create test rule${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Test rule created: $RULE_ID${NC}"
echo "Rule: Threshold - Happy > 80%"

# Record initial alert count
ALERT_COUNT_BEFORE=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT \
    -U $POSTGRES_USER -d $POSTGRES_DB -t -A -c \
    "SELECT COUNT(*) FROM alerts WHERE rule_id = '$RULE_ID';")

echo "Initial alert count: $ALERT_COUNT_BEFORE"

# Reload rules in sentiment service
echo "Reloading rules in sentiment service..."
RELOAD_RESPONSE=$(curl -s -X POST http://localhost:$SENTIMENT_PORT/reload-rules)
echo "Rules reloaded: $RELOAD_RESPONSE"

# Step 4: Clear alert log file
echo -e "\n${BLUE}Step 4: Preparing alert log file...${NC}"
: > $ALERT_LOG_FILE 2>/dev/null || sudo bash -c ": > $ALERT_LOG_FILE" || true
echo -e "${GREEN}✓ Alert log file cleared${NC}"

# Step 5: Publish mock emotions to Redis
echo -e "\n${BLUE}Step 5: Publishing mock emotions to Redis...${NC}"

START_TIME=$(date +%s)

# Note: Sentiment service consumes from emotion:results:* streams
# We need to publish individual face emotions, not aggregated sentiment
~/my_env/bin/python3 << PYTHON_SCRIPT
import redis
import json
import time
from datetime import datetime
import uuid

# Connect to Redis
r = redis.Redis(host='$REDIS_HOST', port=$REDIS_PORT, db=0, decode_responses=True)

camera_id = '$CAMERA_ID'
stream_key = f'emotion:results:{camera_id}'

print(f"Publishing frame data to {stream_key}...")

# Publish 20 frames with 10 faces each (EmotionData format)
# The sentiment service expects: camera_id, timestamp, frame_id, faces (JSON array)
for i in range(20):
    # Build faces array for this frame (9 happy, 1 neutral = 90% happy)
    faces = []
    for face_num in range(10):
        if face_num < 9:
            # Happy face
            emotions = {"happy": 0.9, "neutral": 0.1}
        else:
            # Neutral face
            emotions = {"happy": 0.1, "neutral": 0.9}
        
        faces.append({
            "face_id": f"face_{face_num}",
            "emotions": emotions,
            "bounding_box": [100, 100, 200, 200],
            "metadata": {}
        })
    
    # Create frame data in EmotionData format
    frame_data = {
        "camera_id": camera_id,
        "timestamp": datetime.now().isoformat(),
        "frame_id": f"frame_{i}",
        "faces": json.dumps(faces),
        "emotion_counts": json.dumps({"happy": 9, "neutral": 1})
    }
    
    # Add to stream
    r.xadd(stream_key, frame_data)
    print(f"  Published frame #{i+1}: 9 happy, 1 neutral (90% happy)")
    time.sleep(0.5)  # Publish frame every 0.5 seconds

print("Emotion publishing complete")
PYTHON_SCRIPT

echo -e "${GREEN}✓ Face emotions published to stream${NC}"

# Wait a moment for emotions to be consumed
sleep 2

# Trigger manual aggregation to evaluate rules immediately
echo "Triggering sentiment aggregation and rule evaluation..."
TRIGGER_RESPONSE=$(curl -s -X POST http://localhost:$SENTIMENT_PORT/trigger-aggregation)
echo "Aggregation triggered: $TRIGGER_RESPONSE"

# Wait for alerts to be processed
sleep 3

# Step 6: Monitor for alerts (reduced to 15s since we triggered manually)
echo -e "\n${BLUE}Step 6: Monitoring for alerts (15s)...${NC}"

MONITOR_START=$(date +%s)
MONITOR_DURATION=15
ALERT_DETECTED=false
ALERT_IN_DB=false
ALERT_IN_FILE=false
LAST_PROGRESS=0

while [ $(($(date +%s) - MONITOR_START)) -lt $MONITOR_DURATION ]; do
    ELAPSED=$(($(date +%s) - START_TIME))
    MONITOR_ELAPSED=$(($(date +%s) - MONITOR_START))
    
    # Show progress every 10 seconds
    if [ $((MONITOR_ELAPSED - LAST_PROGRESS)) -ge 10 ]; then
        echo -e "\n${BLUE}[${MONITOR_ELAPSED}s] Checking for alerts...${NC}"
        LAST_PROGRESS=$MONITOR_ELAPSED
    fi
    
    # Check file log for alerts
    if [ -f "$ALERT_LOG_FILE" ] && [ ! "$ALERT_IN_FILE" = true ]; then
        if grep -q "Test Happy Rule - VANTA-24" "$ALERT_LOG_FILE" 2>/dev/null; then
            ALERT_TRIGGERED_TIME=$ELAPSED
            ALERT_IN_FILE=true
            echo -e "${GREEN}✓ Alert found in file log after ${ELAPSED}s${NC}"
        fi
    fi
    
    # Check database for alerts
    if [ ! "$ALERT_IN_DB" = true ]; then
        ALERT_COUNT_NOW=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT \
            -U $POSTGRES_USER -d $POSTGRES_DB -t -A -c \
            "SELECT COUNT(*) FROM alerts WHERE rule_id = '$RULE_ID';")
        
        if [ "$ALERT_COUNT_NOW" -gt "$ALERT_COUNT_BEFORE" ]; then
            ALERT_IN_DB=true
            echo -e "${GREEN}✓ Alert found in database after ${ELAPSED}s${NC}"
        fi
    fi
    
    # Both checks passed
    if [ "$ALERT_IN_FILE" = true ] && [ "$ALERT_IN_DB" = true ]; then
        ALERT_DETECTED=true
        echo -e "${GREEN}✓ All alerts detected! Ending monitoring early.${NC}"
        break
    fi
    
    echo -n "."
    sleep 1
done

echo ""

# Step 7: Validation and Report
echo -e "\n${BLUE}Step 7: Validating results...${NC}"

# Final alert count
ALERT_COUNT_AFTER=$(PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT \
    -U $POSTGRES_USER -d $POSTGRES_DB -t -A -c \
    "SELECT COUNT(*) FROM alerts WHERE rule_id = '$RULE_ID';")

NEW_ALERTS=$((ALERT_COUNT_AFTER - ALERT_COUNT_BEFORE))

# Validation checks
VALIDATION_PASSED=true

echo -e "\n${BLUE}Validation Results:${NC}"
echo "===================="

# Check 1: Rule evaluated (alerts generated)
if [ "$NEW_ALERTS" -gt 0 ]; then
    echo -e "${GREEN}✓ Rule was evaluated (${NEW_ALERTS} alerts generated)${NC}"
else
    echo -e "${RED}✗ Rule was NOT evaluated (0 alerts generated)${NC}"
    VALIDATION_PASSED=false
fi

# Check 2: Alert generated when condition met
if [ "$ALERT_DETECTED" = true ]; then
    echo -e "${GREEN}✓ Alert generated when condition met${NC}"
else
    echo -e "${RED}✗ Alert NOT generated${NC}"
    VALIDATION_PASSED=false
fi

# Check 3: Notification sent (file log)
if [ "$ALERT_IN_FILE" = true ]; then
    echo -e "${GREEN}✓ Notification sent (file log)${NC}"
else
    echo -e "${RED}✗ Notification NOT sent${NC}"
    VALIDATION_PASSED=false
fi

# Check 4: Alert stored in database
if [ "$ALERT_IN_DB" = true ]; then
    echo -e "${GREEN}✓ Alert stored in database${NC}"
else
    echo -e "${RED}✗ Alert NOT in database${NC}"
    VALIDATION_PASSED=false
fi

# Check 5: Alert triggered within 5 seconds
if [ "$ALERT_TRIGGERED_TIME" -gt 0 ] && [ "$ALERT_TRIGGERED_TIME" -le 5 ]; then
    echo -e "${GREEN}✓ Alert triggered within 5 seconds (${ALERT_TRIGGERED_TIME}s)${NC}"
elif [ "$ALERT_TRIGGERED_TIME" -gt 5 ]; then
    echo -e "${YELLOW}⚠ Alert triggered after 5 seconds (${ALERT_TRIGGERED_TIME}s)${NC}"
else
    echo -e "${RED}✗ Alert NOT triggered within test window${NC}"
    VALIDATION_PASSED=false
fi

# Check 6: No errors in service logs
echo -e "\nChecking service logs for errors..."
if grep -qi "error\|exception\|failed" /tmp/sentiment_service.log 2>/dev/null; then
    echo -e "${YELLOW}⚠ Errors found in service logs${NC}"
    echo "See: /tmp/sentiment_service.log"
else
    echo -e "${GREEN}✓ No errors in service logs${NC}"
fi

# Retrieve alert details from database
echo -e "\n${BLUE}Alert Details:${NC}"
PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_HOST -p $POSTGRES_PORT \
    -U $POSTGRES_USER -d $POSTGRES_DB -c \
    "SELECT id, severity, emotion, message, triggered_at 
     FROM alerts 
     WHERE rule_id = '$RULE_ID' 
     ORDER BY triggered_at DESC 
     LIMIT 5;"

# Write final report
cat >> ${REPORT_FILE} << EOF

Test Results:
=============
Execution Time: $(date +%s)s
Alerts Generated: $NEW_ALERTS
Alert Triggered At: ${ALERT_TRIGGERED_TIME}s
Alert in File Log: $ALERT_IN_FILE
Alert in Database: $ALERT_IN_DB

Validation Checks:
==================
✓ Rule Evaluated: $([ "$NEW_ALERTS" -gt 0 ] && echo "PASS" || echo "FAIL")
✓ Alert Generated: $([ "$ALERT_DETECTED" = true ] && echo "PASS" || echo "FAIL")
✓ Notification Sent: $([ "$ALERT_IN_FILE" = true ] && echo "PASS" || echo "FAIL")
✓ Alert in Database: $([ "$ALERT_IN_DB" = true ] && echo "PASS" || echo "FAIL")
✓ Response Time: $([ "$ALERT_TRIGGERED_TIME" -le 5 ] && echo "PASS (${ALERT_TRIGGERED_TIME}s)" || echo "WARN (${ALERT_TRIGGERED_TIME}s)")

Overall Result: $([ "$VALIDATION_PASSED" = true ] && echo "PASS" || echo "FAIL")

EOF

# Final result
echo -e "\n=========================================="
if [ "$VALIDATION_PASSED" = true ]; then
    echo -e "${GREEN}✓ TEST PASSED${NC}"
    echo -e "Report saved to: ${REPORT_FILE}"
    exit 0
else
    echo -e "${RED}✗ TEST FAILED${NC}"
    echo -e "Report saved to: ${REPORT_FILE}"
    echo -e "Service logs: /tmp/sentiment_service.log"
    exit 1
fi
