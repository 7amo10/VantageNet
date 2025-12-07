# Video Ingestion Service

FastAPI-based service for capturing video frames from RTSP streams, webcams, or video files and publishing them to Redis Streams for emotion detection processing.

## Features

- ✅ RTSP stream ingestion
- ✅ Webcam capture support
- ✅ Video file playback
- ✅ Configurable FPS (frames per second)
- ✅ JPEG compression to target size (50KB)
- ✅ Redis Streams publishing
- ✅ Automatic reconnection handling
- ✅ Structured JSON logging
- ✅ Health monitoring endpoint
- ✅ Memory usage tracking

## API Endpoints

### Camera Management

- `POST /cameras` - Register and start a new camera
- `GET /cameras` - List all registered cameras
- `GET /cameras/{camera_id}` - Get camera details
- `DELETE /cameras/{camera_id}` - Stop and remove a camera

### System

- `GET /health` - Service health check
- `GET /` - Service information
- `GET /docs` - Interactive API documentation

## Configuration

Environment variables (set in `.env`):

```env
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6380

# Video Processing
TARGET_FPS=10
FRAME_MAX_SIZE_KB=50
JPEG_QUALITY=85
MAX_CONCURRENT_STREAMS=4

# Connection Management
RECONNECT_INTERVAL_SECONDS=30
MAX_RECONNECT_ATTEMPTS=10
```

## Usage Examples

### Register a webcam

```bash
curl -X POST http://localhost:8001/cameras \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Local Webcam",
    "source_type": "webcam",
    "source_url": "0",
    "fps": 10,
    "enabled": true
  }'
```

### Register an RTSP camera

```bash
curl -X POST http://localhost:8001/cameras \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Security Camera 1",
    "source_type": "rtsp",
    "source_url": "rtsp://192.168.1.100:554/stream",
    "fps": 10,
    "enabled": true
  }'
```

### Register a video file

```bash
curl -X POST http://localhost:8001/cameras \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Video",
    "source_type": "file",
    "source_url": "/path/to/video.mp4",
    "fps": 10,
    "enabled": true
  }'
```

### List all cameras

```bash
curl http://localhost:8001/cameras
```

### Stop a camera

```bash
curl -X DELETE http://localhost:8001/cameras/{camera_id}
```

## Redis Stream Format

Frames are published to Redis Streams with the key pattern:
```
emotion:frames:{camera_id}
```

Each message contains:
- `camera_id` - Camera identifier
- `frame_number` - Sequential frame number
- `timestamp` - ISO format timestamp
- `frame_data` - JPEG-encoded frame bytes
- `frame_size_bytes` - Size of frame in bytes
- `metadata` - Additional camera metadata

### Reading frames from Redis

```bash
# Read latest frame
redis-cli -p 6380 XREAD COUNT 1 STREAMS emotion:frames:{camera_id} 0

# Monitor new frames
redis-cli -p 6380 XREAD BLOCK 0 STREAMS emotion:frames:{camera_id} $
```

## Development

### Install dependencies

```bash
pip install -r requirements.txt
```

### Run locally

```bash
# With my_env virtual environment
python -m app.main

# Or use the local services script
cd ../..
./scripts/run-local-services.sh start
```

### Run tests

```bash
pytest tests/ -v
```

## Performance

- Target FPS: 10 frames/second
- Frame size: ~50KB (JPEG compressed)
- Memory usage: <512MB for 4 concurrent streams
- Reconnection: Automatic with 30s interval

## Logging

Structured JSON logs include:
- Frame processing events
- Connection status changes
- Frame drops and errors
- Memory usage warnings

Example log:
```json
{
  "timestamp": "2025-12-07 13:00:00",
  "level": "INFO",
  "service": "app.video_capture",
  "message": "Published frame 100 to emotion:frames:cam-123 (size: 48576 bytes)"
}
```
