# VANTA-13 Testing Guide

## Overview
This directory contains integration tests for VANTA-13: Frame-to-Emotion Pipeline.

## Test Scripts

### 1. End-to-End Integration Test
**File:** `test_e2e_pipeline.py`

**Purpose:** Validates the complete pipeline from video ingestion to emotion detection results.

**Tests:**
- Video ingestion service is running and publishing frames
- Emotion detection service is running and processing
- Results are published to Redis streams
- Processing latency < 100ms
- Metrics are published (FPS, latency, errors)

**Usage:**
```bash
~/my_env/bin/python tests/test_e2e_pipeline.py
```

**Prerequisites:**
- Redis running on localhost:6380
- video-ingestion service running
- emotion-detection service running

---

### 2. Multi-Camera Test
**File:** `test_multi_camera.py`

**Purpose:** Tests simultaneous processing of multiple camera streams.

**Tests:**
- Multiple cameras streaming simultaneously
- Each camera has its own result stream
- No crosstalk between camera streams
- Results correctly tagged with source camera_id

**Usage:**
```bash
~/my_env/bin/python tests/test_multi_camera.py
```

**Prerequisites:**
- Redis running on localhost:6380
- video-ingestion service with 2+ cameras
- emotion-detection service running

---

### 3. Stress Test
**File:** `test_stress.py`

**Purpose:** Tests system stability under load.

**Tests:**
- Process 100+ frames consecutively
- Memory usage stays < 2GB
- No memory leaks detected
- Stable performance over time

**Usage:**
```bash
~/my_env/bin/python tests/test_stress.py
```

**Duration:** ~30 seconds

**Prerequisites:**
- Redis running on localhost:6380
- video-ingestion service running
- emotion-detection service running

---

## Running All Tests

```bash
# Run all tests sequentially
cd /home/ahmedashour/Desktop/VantageNet

echo "Running E2E Test..."
~/my_env/bin/python tests/test_e2e_pipeline.py

echo "Running Multi-Camera Test..."
~/my_env/bin/python tests/test_multi_camera.py

echo "Running Stress Test..."
~/my_env/bin/python tests/test_stress.py
```

## Test Requirements

### System Requirements
- Python 3.8+
- Redis server
- psutil package (for CPU/memory monitoring)
- requests package (for HTTP health checks)

### Service Requirements
All tests require:
1. **Redis** running on `localhost:6380`
2. **video-ingestion** service running and publishing frames
3. **emotion-detection** service running with models loaded

### Starting Services

```bash
# Terminal 1: Start Redis (Docker)
docker-compose up -d redis

# Terminal 2: Start video-ingestion
cd services/video-ingestion
~/my_env/bin/python -m app.main

# Terminal 3: Start emotion-detection
cd services/emotion-detection
~/my_env/bin/python -m app.main
```

## Expected Results

### E2E Test
✓ All services communicating correctly
✓ Latency < 100ms
✓ Metrics published

### Multi-Camera Test
✓ 2+ cameras processed
✓ No crosstalk
✓ Separate result streams

### Stress Test
✓ 100+ frames processed
✓ Memory < 2GB
✓ No memory leaks

## Troubleshooting

### "No camera streams found"
- Start video-ingestion service
- Check Redis connection
- Verify camera configuration

### "Detection service not responding"
- Start emotion-detection service
- Check models are loaded
- Verify port 8002 is accessible

### "Latency > 100ms"
- Check CPU load
- Verify GPU is being used (if available)
- Reduce frame rate in ingestion service

### "Memory leak detected"
- Monitor over longer duration
- Check for resource cleanup
- Review model memory usage

## Test Output

All tests output:
- ✓ Green checkmarks for passed tests
- ✗ Red X for failed tests
- ⚠ Yellow warnings for issues

Exit codes:
- `0` = All tests passed
- `1` = One or more tests failed

## Notes

- Tests are non-destructive (read-only on existing streams)
- Can be run while services are processing real data
- Multi-camera test requires at least 2 active cameras
- Stress test duration can be adjusted in the code (default 30s)
