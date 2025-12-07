# Redis Streams Architecture

## Overview

VantageNet uses Redis Streams as the backbone for real-time data flow between microservices. This document describes the stream architecture, message formats, consumer patterns, and operational guidelines.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         Redis Streams                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ emotion:events (MAXLEN ~1000)                           │    │
│  │ - Raw emotion detections from video frames              │    │
│  │ - High frequency updates (per frame)                    │    │
│  │ - TTL: ~16 seconds at 60fps                             │    │
│  └─────────────────────────────────────────────────────────┘    │
│           │                          │                          │
│           │ (consume)                │ (consume)                │
│           ▼                          ▼                          │
│  ┌──────────────────┐      ┌──────────────────┐                 │
│  │ emotion-detector │      │ sentiment-       │                 │
│  │ -group           │      │ analyzer-group   │                 │
│  └──────────────────┘      └──────────────────┘                 │
│                                     │                           │
│                                     │ (publish)                 │
│                                     ▼                           │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ sentiment:crowd (MAXLEN ~10000)                         │    │
│  │ - Aggregated sentiment analytics                        │    │
│  │ - Lower frequency (per time window)                     │    │
│  │ - TTL: ~2.7 hours at 1/sec rate                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│           │                                                     │
│           │ (consume)                                           │
│           ▼                                                     │
│  ┌──────────────────┐                                           │
│  │ api-gateway-     │                                           │
│  │ group            │                                           │
│  └──────────────────┘                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Stream Definitions

### emotion:events

**Purpose**: Carries raw emotion detection results from the emotion-detection service to downstream consumers.

**Configuration**:
- MAXLEN: ~1000 (approximate, uses MINID for efficient trimming)
- TTL: ~16 seconds at 60fps frame rate
- Retention Strategy: Keep most recent detections only

**Message Format**:
```json
{
  "frame_id": "cam_001_frame_12345",
  "camera_id": "cam_001",
  "timestamp": "2025-01-15T10:30:45.123Z",
  "faces": [
    {
      "face_id": "face_001",
      "bounding_box": {"x": 100, "y": 150, "width": 80, "height": 100},
      "emotion": "happy",
      "confidence": 0.95,
      "emotion_scores": {
        "happy": 0.95,
        "neutral": 0.03,
        "sad": 0.01,
        "angry": 0.005,
        "surprise": 0.003,
        "fear": 0.001,
        "disgust": 0.001
      }
    }
  ],
  "metadata": {
    "model_version": "deepface-1.0",
    "processing_time_ms": 45
  }
}
```

**Consumer Groups**:
1. **emotion-detector-group**: Used by emotion-detection service for internal state tracking
2. **sentiment-analyzer-group**: Used by sentiment-analysis service to consume detections for aggregation

### sentiment:crowd

**Purpose**: Carries aggregated sentiment analytics from sentiment-analysis service to API gateway for dashboard updates.

**Configuration**:
- MAXLEN: ~10000 (approximate, uses MINID for efficient trimming)
- TTL: ~2.7 hours at 1 message/second
- Retention Strategy: Keep historical analytics for short-term trends

**Message Format**:
```json
{
  "camera_id": "cam_001",
  "timestamp": "2025-01-15T10:30:00.000Z",
  "time_window": 60,
  "sentiment_stats": {
    "sentiment_score": 0.45,
    "avg_happy": 0.62,
    "avg_neutral": 0.20,
    "avg_sad": 0.08,
    "avg_angry": 0.04,
    "avg_surprise": 0.03,
    "avg_fear": 0.02,
    "avg_disgust": 0.01
  },
  "face_count": 15,
  "total_detections": 850,
  "metadata": {
    "aggregation_method": "weighted_average",
    "rule_triggers": []
  }
}
```

**Consumer Groups**:
1. **api-gateway-group**: Used by API gateway to consume sentiment analytics for real-time dashboard updates

## Producer Patterns

### Publishing to emotion:events

**Service**: emotion-detection service

**Code Example** (Python):
```python
import redis
import json

redis_client = redis.Redis(host='redis', port=6379)

def publish_emotion_detection(frame_id, camera_id, faces):
    message = {
        "frame_id": frame_id,
        "camera_id": camera_id,
        "timestamp": datetime.utcnow().isoformat(),
        "faces": faces,
        "metadata": {
            "model_version": "deepface-1.0",
            "processing_time_ms": processing_time
        }
    }
    
    # Publish with automatic trimming
    redis_client.xadd(
        'emotion:events',
        message,
        maxlen=1000,
        approximate=True
    )
```

### Publishing to sentiment:crowd

**Service**: sentiment-analysis service

**Code Example** (Python):
```python
import redis
import json

redis_client = redis.Redis(host='redis', port=6379)

def publish_sentiment_analytics(camera_id, stats):
    message = {
        "camera_id": camera_id,
        "timestamp": datetime.utcnow().isoformat(),
        "time_window": 60,
        "sentiment_stats": stats,
        "face_count": face_count,
        "total_detections": total_detections,
        "metadata": {
            "aggregation_method": "weighted_average",
            "rule_triggers": []
        }
    }
    
    # Publish with automatic trimming
    redis_client.xadd(
        'sentiment:crowd',
        message,
        maxlen=10000,
        approximate=True
    )
```

## Consumer Patterns

### Consuming from emotion:events

**Services**: emotion-detection, sentiment-analysis

**Pattern**: Consumer Group with multiple consumers for load balancing

**Code Example** (Python):
```python
import redis

redis_client = redis.Redis(host='redis', port=6379)

def consume_emotion_events(consumer_name):
    group_name = 'sentiment-analyzer-group'
    stream_name = 'emotion:events'
    
    # Create consumer group if not exists
    try:
        redis_client.xgroup_create(stream_name, group_name, id='0', mkstream=True)
    except redis.ResponseError:
        pass  # Group already exists
    
    while True:
        # Read new messages
        messages = redis_client.xreadgroup(
            groupname=group_name,
            consumername=consumer_name,
            streams={stream_name: '>'},
            count=10,
            block=5000  # Block for 5 seconds
        )
        
        for stream, stream_messages in messages:
            for message_id, data in stream_messages:
                try:
                    # Process message
                    process_emotion_detection(data)
                    
                    # Acknowledge message
                    redis_client.xack(stream_name, group_name, message_id)
                except Exception as e:
                    print(f"Error processing message {message_id}: {e}")
                    # Message remains in pending list for retry
```

### Consuming from sentiment:crowd

**Service**: api-gateway

**Pattern**: Single consumer group for real-time dashboard updates

**Code Example** (Python):
```python
import redis
import asyncio

redis_client = redis.Redis(host='redis', port=6379)

async def consume_sentiment_analytics():
    group_name = 'api-gateway-group'
    stream_name = 'sentiment:crowd'
    consumer_name = 'api-gateway-001'
    
    # Create consumer group if not exists
    try:
        redis_client.xgroup_create(stream_name, group_name, id='0', mkstream=True)
    except redis.ResponseError:
        pass
    
    while True:
        messages = redis_client.xreadgroup(
            groupname=group_name,
            consumername=consumer_name,
            streams={stream_name: '>'},
            count=5,
            block=1000
        )
        
        for stream, stream_messages in messages:
            for message_id, data in stream_messages:
                # Broadcast to WebSocket clients
                await broadcast_to_dashboard(data)
                
                # Acknowledge
                redis_client.xack(stream_name, group_name, message_id)
```

## Configuration

### Redis Configuration (redis.conf)

```conf
# Memory Management
maxmemory 512mb
maxmemory-policy allkeys-lru

# Persistence (AOF)
appendonly yes
appendfsync everysec
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb

# Performance Monitoring
slowlog-log-slower-than 10000
slowlog-max-len 128

# Network
bind 0.0.0.0
protected-mode no
port 6379
tcp-backlog 511
timeout 300
```

### Stream MAXLEN Strategy

**emotion:events**: MAXLEN ~1000
- Uses approximate trimming (MINID) for O(1) performance
- Keeps ~16 seconds of data at 60fps
- Prioritizes recent detections over historical data

**sentiment:crowd**: MAXLEN ~10000
- Uses approximate trimming for O(1) performance
- Keeps ~2.7 hours of data at 1 message/second
- Enables short-term trend analysis

## Monitoring

### Stream Health Checks

```bash
# Check stream lengths
redis-cli XLEN emotion:events
redis-cli XLEN sentiment:crowd

# Check consumer group lag
redis-cli XINFO GROUPS emotion:events
redis-cli XINFO GROUPS sentiment:crowd

# Check pending messages
redis-cli XPENDING emotion:events emotion-detector-group
redis-cli XPENDING sentiment:crowd api-gateway-group
```

### Key Metrics

**Stream Metrics**:
- `XLEN`: Current stream length (should be near MAXLEN)
- `XINFO STREAM`: Stream details including first/last entry

**Consumer Group Metrics**:
- `lag`: Number of messages not yet consumed
- `pending`: Messages delivered but not acknowledged
- `last-delivered-id`: Last message ID delivered to any consumer

**Performance Metrics**:
- `INFO stats`: Total operations, connections
- `MEMORY STATS`: Memory usage breakdown
- `SLOWLOG GET 10`: Slow commands (>10ms)

### Monitoring Script

Use the provided monitoring script:
```bash
./scripts/redis-monitor.sh
```

This script provides:
- Stream lengths and info
- Consumer group status
- Memory usage
- Performance metrics
- Slowlog entries
- Health summary

## Operational Guidelines

### Scaling Consumers

Add more consumers to a group for horizontal scaling:

```python
# Start multiple consumers with unique names
consumer_1 = Thread(target=consume_emotion_events, args=('consumer-001',))
consumer_2 = Thread(target=consume_emotion_events, args=('consumer-002',))
```

Redis automatically load balances messages across consumers in the same group.

### Handling Failed Messages

Messages that fail processing remain in the pending list. Implement retry logic:

```python
# Check for pending messages older than 5 minutes
pending = redis_client.xpending_range(
    'emotion:events',
    'sentiment-analyzer-group',
    min='-',
    max='+',
    count=100
)

for p in pending:
    if p['time_since_delivered'] > 300000:  # 5 minutes in ms
        # Claim and retry
        messages = redis_client.xclaim(
            'emotion:events',
            'sentiment-analyzer-group',
            'consumer-retry',
            min_idle_time=300000,
            message_ids=[p['message_id']]
        )
```

### Stream Trimming

Automatic trimming is handled by Redis with MAXLEN ~approximate:

```python
# Manual trim if needed
redis_client.xtrim('emotion:events', maxlen=1000, approximate=True)
```

### Backup and Recovery

**AOF Persistence** is enabled for durability:
- Streams survive Redis restarts
- Consumer group state is preserved
- Pending messages are retained

**Backup Strategy**:
```bash
# Save current AOF
redis-cli BGSAVE

# Copy AOF file
cp /data/appendonly.aof /backup/appendonly_$(date +%Y%m%d).aof
```

## Performance Tuning

### Producer Optimization

- Use pipelining for bulk publishes
- Set appropriate MAXLEN to avoid excessive trimming
- Monitor publish latency with SLOWLOG

### Consumer Optimization

- Batch message reads with COUNT parameter
- Use blocking reads with BLOCK parameter
- Acknowledge messages promptly to avoid pending buildup
- Scale horizontally with multiple consumers

### Memory Optimization

- Monitor memory usage: `INFO memory`
- Adjust MAXLEN based on workload
- Use approximate trimming for O(1) performance
- Enable maxmemory-policy for eviction

## Troubleshooting

### High Lag in Consumer Groups

**Symptom**: `lag` metric in XINFO GROUPS is increasing

**Solutions**:
- Add more consumers to the group
- Optimize message processing code
- Increase BLOCK timeout to reduce polling overhead

### High Memory Usage

**Symptom**: `used_memory` approaching `maxmemory`

**Solutions**:
- Reduce MAXLEN on streams
- Verify trimming is working (check stream lengths)
- Increase maxmemory limit if needed
- Check for memory leaks in consumers

### Messages Not Being Consumed

**Symptom**: Stream length growing, consumers idle

**Solutions**:
- Verify consumer is connected: `CLIENT LIST`
- Check consumer group exists: `XINFO GROUPS`
- Verify consumer is reading: `XINFO CONSUMERS`
- Check for errors in consumer logs

### Lost Messages After Restart

**Symptom**: Streams empty after Redis restart

**Solutions**:
- Verify AOF is enabled: `CONFIG GET appendonly`
- Check AOF file integrity: `redis-check-aof`
- Restore from backup if needed

## References

- [Redis Streams Documentation](https://redis.io/docs/data-types/streams/)
- [Redis Consumer Groups](https://redis.io/docs/data-types/streams-tutorial/#consumer-groups)
- [Redis Persistence](https://redis.io/docs/management/persistence/)
- [Redis Memory Optimization](https://redis.io/docs/management/optimization/memory-optimization/)
