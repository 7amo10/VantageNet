#!/bin/bash
################################################################################
# VANTA-17: End-to-End Integration Test
# Tests complete pipeline: Video Ingestion → Emotion Detection → Redis
#
# Requirements:
# - Redis running on localhost:6380
# - Test video: tests/fixtures/test_video.mp4 (640x480, 30 FPS, 60s)
# - Python environment with all dependencies
#
# Success Criteria:
# - ≥1000 emotions detected
# - Avg latency < 100ms
# - Memory usage < 2GB
# - No errors in logs
#
# Usage:
#   ./scripts/test_pipeline_integration.sh
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
TEST_DURATION=60
TEST_VIDEO="tests/fixtures/test_video.mp4"
CAMERA_ID="test_camera_integration"
REPORT_DIR="test_reports"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="${REPORT_DIR}/integration_test_${TIMESTAMP}.txt"

# Service PIDs
REDIS_PID=""
INGESTION_PID=""
DETECTION_PID=""

# Cleanup function
cleanup() {
    echo -e "${YELLOW}Cleaning up services...${NC}"
    
    if [ ! -z "$DETECTION_PID" ]; then
        echo "Stopping detection service (PID: $DETECTION_PID)"
        kill $DETECTION_PID 2>/dev/null || true
    fi
    
    if [ ! -z "$INGESTION_PID" ]; then
        echo "Stopping ingestion service (PID: $INGESTION_PID)"
        kill $INGESTION_PID 2>/dev/null || true
    fi
    
    # Don't stop Redis if it was already running
    
    echo -e "${GREEN}Cleanup complete${NC}"
}

# Set up trap for cleanup
trap cleanup EXIT INT TERM

# Print header
echo "=================================="
echo "VANTA-17: Integration Test"
echo "=================================="
echo "Timestamp: $(date)"
echo "Test Duration: ${TEST_DURATION}s"
echo "Test Video: ${TEST_VIDEO}"
echo "Redis: ${REDIS_HOST}:${REDIS_PORT}"
echo "=================================="
echo ""

# Create report directory
mkdir -p ${REPORT_DIR}

# Initialize report
cat > ${REPORT_FILE} << EOF
VANTA-17: End-to-End Integration Test Report
=============================================
Timestamp: $(date)
Test Duration: ${TEST_DURATION} seconds
Test Video: ${TEST_VIDEO}
Redis: ${REDIS_HOST}:${REDIS_PORT}

EOF

# Step 1: Check prerequisites
echo -e "${BLUE}Step 1: Checking prerequisites...${NC}"

# Kill any existing services first
echo "Stopping any existing services..."
pkill -9 -f "emotion-detection.*app.main" 2>/dev/null || true
pkill -9 -f "video-ingestion.*app.main" 2>/dev/null || true
sleep 2
echo -e "${GREEN}✓ Existing services stopped${NC}"

# Check if Redis is running
if ! redis-cli -h ${REDIS_HOST} -p ${REDIS_PORT} ping &>/dev/null; then
    echo -e "${RED}✗ Redis is not running on ${REDIS_HOST}:${REDIS_PORT}${NC}"
    echo "Please start Redis with: docker-compose up -d redis"
    exit 1
fi
echo -e "${GREEN}✓ Redis is running${NC}"

# Check if test video exists
if [ ! -f "${TEST_VIDEO}" ]; then
    echo -e "${YELLOW}⚠ Test video not found, generating synthetic video...${NC}"
    python3 << 'PYTHON_SCRIPT'
import cv2
import numpy as np
from pathlib import Path

# Create fixtures directory
Path("tests/fixtures").mkdir(parents=True, exist_ok=True)

# Video parameters
width, height = 640, 480
fps = 30
duration = 60  # seconds
total_frames = fps * duration

# Create video writer
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter('tests/fixtures/test_video.mp4', fourcc, fps, (width, height))

print(f"Generating test video: {width}x{height}, {fps} FPS, {duration}s...")

for frame_num in range(total_frames):
    # Create frame with moving face-like blob
    frame = np.ones((height, width, 3), dtype=np.uint8) * 180
    
    # Calculate position (moving horizontally)
    x = int(200 + 200 * np.sin(frame_num * 0.05))
    y = 240
    
    # Draw face-like shape
    cv2.rectangle(frame, (x-50, y-60), (x+50, y+60), (120, 160, 200), -1)
    cv2.circle(frame, (x-20, y-20), 8, (30, 30, 30), -1)  # Left eye
    cv2.circle(frame, (x+20, y-20), 8, (30, 30, 30), -1)  # Right eye
    cv2.ellipse(frame, (x, y+20), (25, 12), 0, 0, 180, (30, 30, 30), 2)  # Mouth
    
    # Add frame number
    cv2.putText(frame, f"Frame {frame_num}", (10, 30), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    out.write(frame)
    
    if frame_num % 300 == 0:
        print(f"  Progress: {frame_num}/{total_frames} frames ({frame_num/total_frames*100:.1f}%)")

out.release()
print(f"✓ Video generated: tests/fixtures/test_video.mp4")
PYTHON_SCRIPT
fi
echo -e "${GREEN}✓ Test video ready${NC}"

# Clear ALL Redis emotion streams
echo -e "${BLUE}Clearing Redis streams...${NC}"
redis-cli -h ${REDIS_HOST} -p ${REDIS_PORT} --scan --pattern "emotion:*" | xargs -r redis-cli -h ${REDIS_HOST} -p ${REDIS_PORT} DEL 2>/dev/null || true
echo -e "${GREEN}✓ Redis streams cleared${NC}"
echo ""

# Step 2: Start services
echo -e "${BLUE}Step 2: Starting services...${NC}"

# Start emotion detection service
echo "Starting emotion detection service..."
cd /home/ahmedashour/Desktop/VantageNet/services/emotion-detection
source ~/my_env/bin/activate 2>/dev/null || source ../../.venv/bin/activate
REDIS_HOST=${REDIS_HOST} REDIS_PORT=${REDIS_PORT} python -m app.main > ../../logs/detection_${TIMESTAMP}.log 2>&1 &
DETECTION_PID=$!
cd ../..
echo -e "${GREEN}✓ Detection service started (PID: ${DETECTION_PID})${NC}"

# Wait for detection service to initialize
echo "Waiting for detection service to initialize (10s)..."
sleep 10

# Start video ingestion service
echo "Starting video ingestion service..."
cd services/video-ingestion
source ~/my_env/bin/activate 2>/dev/null || source ../../.venv/bin/activate
REDIS_HOST=${REDIS_HOST} REDIS_PORT=${REDIS_PORT} python -m app.main \
    --camera-id ${CAMERA_ID} \
    --source ../../${TEST_VIDEO} \
    --fps 30 > ../../logs/ingestion_${TIMESTAMP}.log 2>&1 &
INGESTION_PID=$!
cd ../..
echo -e "${GREEN}✓ Ingestion service started (PID: ${INGESTION_PID})${NC}"

# Wait for ingestion to start (5s)...
sleep 5

# Discover actual camera_id from Redis streams
echo "Discovering camera_id from Redis..."
ACTUAL_CAMERA_ID=$(redis-cli -h ${REDIS_HOST} -p ${REDIS_PORT} --scan --pattern "emotion:frames:*" | head -1 | sed 's/emotion:frames://')
if [ -z "$ACTUAL_CAMERA_ID" ]; then
    echo -e "${RED}✗ No emotion streams found! Ingestion may have failed.${NC}"
    echo "Check logs/ingestion_${TIMESTAMP}.log for errors"
    exit 1
fi
echo -e "${GREEN}✓ Found camera_id: ${ACTUAL_CAMERA_ID}${NC}"
echo ""

# Step 3: Monitor pipeline
echo -e "${BLUE}Step 3: Monitoring pipeline for ${TEST_DURATION} seconds...${NC}"

# Monitor script in Python
python3 << PYTHON_MONITOR
import redis
import json
import time
import psutil
from datetime import datetime

# Connect to Redis
r = redis.Redis(host='${REDIS_HOST}', port=${REDIS_PORT}, decode_responses=True)

# Use actual camera_id discovered from Redis
camera_id = '${ACTUAL_CAMERA_ID}'
results_stream = f'emotion:results:{camera_id}'

# Metrics
start_time = time.time()
emotion_count = 0
latencies = []
frame_numbers = set()
errors = []
memory_samples = []

print(f"Monitoring Redis stream: {results_stream}")
print(f"Duration: ${TEST_DURATION} seconds")
print("-" * 60)

# Get detection service PID for memory monitoring
detection_pid = ${DETECTION_PID}

# Track last message ID
last_id = '0'

# Monitor for TEST_DURATION seconds
while time.time() - start_time < ${TEST_DURATION}:
    try:
        # Read from emotion results stream
        streams = r.xread({results_stream: last_id}, count=100, block=1000)
        
        if streams:
            for stream_key, messages in streams:
                for msg_id, data in messages:
                    last_id = msg_id  # Update last_id to avoid re-reading
                    emotion_count += 1
                    
                    # Data is already a dict with Redis hash fields
                    # Track frame numbers
                    if 'frame_number' in data:
                        try:
                            frame_numbers.add(int(data['frame_number']))
                        except:
                            pass
                    
                    # Track latency
                    if 'processing_time_ms' in data:
                        try:
                            latencies.append(float(data['processing_time_ms']))
                        except:
                            pass
                    
                    # Check for errors
                    if 'error' in data:
                        errors.append(data['error'])
        
        # Sample memory every 5 seconds
        if int(time.time() - start_time) % 5 == 0:
            try:
                process = psutil.Process(detection_pid)
                memory_mb = process.memory_info().rss / 1024 / 1024
                memory_samples.append(memory_mb)
            except:
                pass
        
        # Progress update every 10 seconds
        elapsed = time.time() - start_time
        if int(elapsed) % 10 == 0 and elapsed > 0:
            print(f"[{int(elapsed)}s] Emotions: {emotion_count}, Frames: {len(frame_numbers)}")
    
    except Exception as e:
        print(f"Error during monitoring: {e}")
        errors.append(str(e))

# Calculate final metrics
elapsed_total = time.time() - start_time
avg_latency = sum(latencies) / len(latencies) if latencies else 0
max_latency = max(latencies) if latencies else 0
avg_memory = sum(memory_samples) / len(memory_samples) if memory_samples else 0
max_memory = max(memory_samples) if memory_samples else 0

print("-" * 60)
print(f"Monitoring complete!")
print(f"Total Duration: {elapsed_total:.2f}s")
print(f"Emotions Detected: {emotion_count}")
print(f"Unique Frames: {len(frame_numbers)}")
print(f"Avg Latency: {avg_latency:.2f}ms")
print(f"Max Latency: {max_latency:.2f}ms")
print(f"Avg Memory: {avg_memory:.2f} MB")
print(f"Max Memory: {max_memory:.2f} MB")
print(f"Errors: {len(errors)}")

# Write detailed report
with open('${REPORT_FILE}', 'a') as f:
    f.write(f"""
Test Results
============
Duration: {elapsed_total:.2f} seconds
Emotions Detected: {emotion_count}
Unique Frames Processed: {len(frame_numbers)}

Performance Metrics
===================
Average Latency: {avg_latency:.2f} ms
Maximum Latency: {max_latency:.2f} ms
Average Memory: {avg_memory:.2f} MB
Maximum Memory: {max_memory:.2f} MB

Acceptance Criteria Validation
===============================
✓ Emotions detected: {emotion_count} (target: ≥1000) {'PASS' if emotion_count >= 1000 else 'FAIL'}
✓ Avg latency: {avg_latency:.2f}ms (target: <100ms) {'PASS' if avg_latency < 100 else 'FAIL'}
✓ Memory usage: {max_memory:.2f}MB (target: <2048MB) {'PASS' if max_memory < 2048 else 'FAIL'}
✓ No errors: {len(errors)} errors {'PASS' if len(errors) == 0 else 'FAIL'}

""")

    if errors:
        f.write("Errors Encountered:\n")
        for i, error in enumerate(errors[:10], 1):
            f.write(f"{i}. {error}\n")
        if len(errors) > 10:
            f.write(f"... and {len(errors) - 10} more errors\n")
    
    f.write(f"\nTest completed at: {datetime.now()}\n")

# Determine overall result
all_pass = (
    emotion_count >= 1000 and
    avg_latency < 100 and
    max_memory < 2048 and
    len(errors) == 0
)

exit(0 if all_pass else 1)
PYTHON_MONITOR

MONITOR_EXIT_CODE=$?

echo ""
echo "=================================="
echo -e "${BLUE}Test Summary${NC}"
echo "=================================="
cat ${REPORT_FILE} | tail -20
echo ""

if [ $MONITOR_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ Integration test PASSED${NC}"
    echo -e "Report: ${REPORT_FILE}"
    exit 0
else
    echo -e "${RED}✗ Integration test FAILED${NC}"
    echo -e "Report: ${REPORT_FILE}"
    echo -e "Check logs:"
    echo -e "  - logs/detection_${TIMESTAMP}.log"
    echo -e "  - logs/ingestion_${TIMESTAMP}.log"
    exit 1
fi
