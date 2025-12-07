# Emotion Detection Service

Face detection and emotion classification service for VantageNet using YOLOv8 and DeepFace.

## Overview

This service consumes video frames from Redis Streams, performs face detection using YOLOv8, and classifies emotions using DeepFace FER model. It's designed to run locally with your PyTorch environment to avoid Docker image bloat.

## Architecture

```
Redis Streams → Consumer → YOLO (face detection) → DeepFace (emotion) → Results
emotion:frames:*   ↓           ↓                      ↓                  ↓
                Processing  Batch N      FER Model              emotion:results:*
```

## Features

- **Redis Streams Consumer**: Reads from `emotion:frames:*` pattern with consumer groups
- **YOLOv8 Face Detection**: Pre-trained face detection model from Ultralytics
- **DeepFace Emotion Recognition**: 7-class emotion classification (angry, disgust, fear, happy, sad, surprise, neutral)
- **Batch Processing**: Configurable frame sampling (process every Nth frame)
- **Memory Management**: Tracks memory usage and stays under 2GB limit
- **Graceful Shutdown**: Finishes processing current frame before exit
- **Health Monitoring**: `/health` endpoint with model status and metrics

## Configuration

Environment variables (set in `.env` or export):

```bash
# Service
EMOTION_DETECTION_PORT=8002

# Redis
REDIS_HOST=localhost
REDIS_PORT=6380

# Models
YOLO_MODEL_PATH=yolov8n-face.pt
FER_MODEL_NAME=Emotion
FER_BACKEND=opencv

# Processing
PROCESS_EVERY_N_FRAMES=3  # Process every 3rd frame
MAX_MEMORY_MB=2000
CONFIDENCE_THRESHOLD=0.5
```

## Models

### YOLOv8-face
- **Purpose**: Face detection
- **Source**: Ultralytics Hub
- **Size**: ~6MB
- **Performance**: ~30ms per frame on CPU

### DeepFace FER
- **Purpose**: Emotion classification
- **Classes**: angry, disgust, fear, happy, sad, surprise, neutral
- **Size**: ~100MB
- **Performance**: ~50ms per face on CPU

## Installation

```bash
# Activate your virtual environment with PyTorch
source ~/my_env/bin/activate

# Install dependencies
cd services/emotion-detection
pip install -r requirements.txt

# Download YOLO model (first run)
# The model will auto-download from Ultralytics Hub
```

## Running

```bash
# From project root with virtual environment activated
cd services/emotion-detection
python -m app.main

# Or use the run-local-services.sh script
./scripts/run-local-services.sh start
```

The service will:
1. Connect to Redis
2. Load YOLO and FER models
3. Start consuming frames
4. Process and log frame information

## API Endpoints

### GET /health
Health check with comprehensive status

```json
{
  "status": "healthy",
  "service": "emotion-detection",
  "version": "0.1.0",
  "redis_connected": true,
  "models": [
    {
      "name": "YOLOv8-face",
      "loaded": true,
      "memory_mb": 85.3
    },
    {
      "name": "FER (DeepFace)",
      "loaded": true,
      "memory_mb": 112.7
    }
  ],
  "frames_processed": 150,
  "memory_usage_mb": 198.0,
  "pytorch_available": true,
  "cuda_available": false
}
```

### GET /
Service information and configuration

## Current Implementation (Sprint 1)

This is the **scaffold version** for Sprint 1:
- ✅ FastAPI application on port 8002
- ✅ Redis Streams consumer reading from `emotion:frames:*`
- ✅ YOLOv8 and FER models loaded in memory
- ✅ Dummy processing loop logging frame timestamps
- ✅ Health endpoint with model status
- ✅ Graceful shutdown
- ✅ Memory monitoring
- ✅ Structured logging

**Sprint 2 will add**:
- Actual face detection with YOLO
- Emotion classification with DeepFace
- Results publishing to Redis
- Performance metrics

## Testing

```bash
# Start the service
python -m app.main

# Check health
curl http://localhost:8002/health

# Verify it's consuming frames (check logs)
# You should see: "📸 Frame received | Camera: xxx | Frame: xxx"
```

## Memory Usage

Expected memory footprint:
- Base service: ~50MB
- YOLOv8 model: ~80MB
- DeepFace model: ~120MB
- **Total**: ~250MB

Well under the 2GB limit.

## Logging

Structured JSON logging for all operations:

```json
{"timestamp": "2025-12-07 14:30:15", "level": "INFO", "service": "app.processor", "message": "📸 Frame received | Camera: uuid | Frame: 42 | Timestamp: 2025-12-07T14:30:15"}
```

## Troubleshooting

**Models not loading?**
- Check your virtual environment has PyTorch
- Ensure internet connection for first-time model download
- Check disk space for model caching

**Not consuming frames?**
- Verify video-ingestion service is running and publishing
- Check Redis connection with `redis-cli -p 6380 KEYS emotion:frames:*`
- Verify consumer group created: `XINFO GROUPS emotion:frames:{camera_id}`

**Memory issues?**
- Reduce `process_every_n_frames` to process fewer frames
- Monitor with `/health` endpoint
- Check for memory leaks in logs
