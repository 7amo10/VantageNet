# VantageNet Architecture

This document provides a comprehensive overview of VantageNet's system architecture, design decisions, and service communication patterns.

## Table of Contents

- [System Overview](#system-overview)
- [Architecture Diagram](#architecture-diagram)
- [Service Descriptions](#service-descriptions)
- [Data Flow](#data-flow)
- [Communication Patterns](#communication-patterns)
- [Design Decisions](#design-decisions)
- [Technology Stack](#technology-stack)
- [Deployment Model](#deployment-model)

## System Overview

VantageNet is a **real-time emotion analytics platform** that processes video streams to detect emotions and generate crowd sentiment insights. The system follows a **microservices architecture** with 5 core services:

1. **Video Ingestion Service** - Captures and preprocesses video frames
2. **Emotion Detection Service** - Analyzes faces and detects emotions using DeepFace
3. **Sentiment Analysis Service** - Aggregates emotions into crowd sentiment metrics
4. **API Gateway** - Provides REST/WebSocket API for frontend communication
5. **Dashboard** - React-based web UI for visualization and configuration

### Key Characteristics

- **Asynchronous**: Services communicate via Redis Streams (pub/sub pattern)
- **Scalable**: Each service can be scaled independently
- **Resilient**: Failure in one service doesn't cascade to others
- **Real-time**: Sub-second latency from video capture to dashboard update
- **Hybrid**: Mix of containerized and local services for optimal resource usage

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           VantageNet System                             │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   Camera Feed    │     │   Camera Feed    │     │   Camera Feed    │
│  (RTSP Stream)   │     │  (RTSP Stream)   │     │  (RTSP Stream)   │
└────────┬─────────┘     └────────┬─────────┘     └────────┬─────────┘
         │                        │                        │
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                                  ▼
         ┌───────────────────────────────────────────────┐
         │     Video Ingestion Service (Port 8001)       │
         │  - Captures frames from RTSP streams          │
         │  - Preprocesses and publishes to Redis        │
         │  - Memory: 256MB                              │
         └────────────────────┬──────────────────────────┘
                              │
                              │ Publishes frames to
                              │ Redis Stream: "frames"
                              ▼
         ┌───────────────────────────────────────────────┐
         │            Redis Streams (Port 6380)          │
         │  ┌──────────────────────────────────────────┐ │
         │  │ emotion:events (MAXLEN ~1000)            │ │
         │  │ - Raw emotion detections                 │ │
         │  │ - Consumer groups:                       │ │
         │  │   • emotion-detector-group               │ │
         │  │   • sentiment-analyzer-group             │ │
         │  └──────────────────────────────────────────┘ │
         │  ┌──────────────────────────────────────────┐ │
         │  │ sentiment:crowd (MAXLEN ~10000)          │ │
         │  │ - Aggregated sentiment analytics         │ │
         │  │ - Consumer groups:                       │ │
         │  │   • api-gateway-group                    │ │
         │  └──────────────────────────────────────────┘ │
         │                                               │
         │  Config: 512MB max, allkeys-lru, AOF enabled  │
         └────┬───────────────────────────────────┬──────┘
              │                                   │
              │ Consumes                          │ Consumes
              │ emotion:events                    │ sentiment:crowd
              ▼                                   ▼
┌──────────────────────────────┐   ┌──────────────────────────────┐
│ Emotion Detection (Port 8002)│   │   API Gateway (Port 8000)    │
│ - YOLOv8 face detection      │   │ - REST API endpoints         │
│ - DeepFace emotion analysis  │   │ - WebSocket for live updates │
│ - Publishes to emotion:events│   │ - CRUD for cameras/rules     │
│ - Memory: 512MB              │   │ - Memory: 52MB               │
└──────────┬───────────────────┘   └────────┬─────────────────────┘
           │                                 │
           │ Publishes to                    │ HTTP/WebSocket
           │ emotion:events                  │
           ▼                                 ▼
┌────────────────────────────────────────────────────────────────┐
│          Sentiment Analysis Service (Port 8003)                │
│  - Aggregates emotions into sentiment scores                   │
│  - Applies rules engine                                        │
│  - Publishes to sentiment:crowd stream                         │
│  - Writes to PostgreSQL for persistence                        │
│  - Memory: 256MB                                               │
└────────────────────┬───────────────────────────────────────────┘
                     │
                     │ Writes aggregated data
                     ▼
         ┌────────────────────────────────────┐
         │   PostgreSQL Database (Port 5434)  │
         │  ┌──────────────────────────────┐  │
         │  │ cameras                      │  │
         │  │ emotions (partitioned)       │  │
         │  │ rules                        │  │
         │  │ alerts                       │  │
         │  │ sentiment_stats              │  │
         │  └──────────────────────────────┘  │
         │                                    │
         │  16+ indexes, AOF persistence      │
         └────────────────────────────────────┘
                     ▲
                     │ Reads configuration
                     │ and historical data
                     │
         ┌───────────┴──────────────────────────┐
         │      Dashboard (Port 3001)           │
         │  - Next.js 14 (React 18)             │
         │  - Real-time WebSocket updates       │
         │  - Camera management UI              │
         │  - Rules configuration UI            │
         │  - Analytics visualization           │
         └──────────────────────────────────────┘
```

## Service Descriptions

### 1. Video Ingestion Service

**Purpose**: Captures video frames from RTSP camera streams and publishes them to Redis for processing.

**Technology**: Python 3.11, FastAPI, OpenCV

**Key Components**:
- `CameraManager`: Manages multiple camera connections
- `VideoCapture`: Captures frames from RTSP streams
- `RedisClient`: Publishes frames to Redis streams

**Responsibilities**:
- Connect to RTSP camera feeds
- Capture frames at configurable FPS (default: 30fps)
- Resize/preprocess frames
- Publish frames to Redis stream
- Handle camera failures and reconnection

**Resource Usage**:
- Memory: 256MB limit
- CPU: Moderate (video decoding)
- Network: High (RTSP streaming)

**Configuration**:
- Port: 8001
- Frame rate: 30 FPS
- Frame resize: 640x480

### 2. Emotion Detection Service

**Purpose**: Detects faces in video frames and analyzes emotions using deep learning models.

**Technology**: Python 3.11, FastAPI, PyTorch, DeepFace, YOLOv8

**Key Components**:
- `ModelLoader`: Loads YOLOv8 and DeepFace models
- `Processor`: Processes frames and detects emotions
- `RedisConsumer`: Consumes frames from Redis stream

**Responsibilities**:
- Detect faces using YOLOv8
- Analyze emotions using DeepFace (7 emotions: happy, sad, angry, surprise, fear, disgust, neutral)
- Extract confidence scores and bounding boxes
- Publish emotion detections to Redis stream
- Track faces across frames (face_id)

**Models Used**:
- **YOLOv8n**: Fast face detection (~50ms per frame)
- **DeepFace**: Emotion classification (~100ms per face)

**Resource Usage**:
- Memory: 512MB limit (models loaded once)
- CPU: High (inference)
- GPU: Optional (CUDA support)

**Configuration**:
- Port: 8002
- Batch size: 1 (real-time processing)
- Confidence threshold: 0.5

### 3. Sentiment Analysis Service

**Purpose**: Aggregates individual emotion detections into crowd-level sentiment metrics and triggers rules.

**Technology**: Python 3.11, FastAPI, SQLAlchemy, Pandas

**Key Components**:
- `Aggregator`: Aggregates emotions into sentiment scores
- `RulesEngine`: Evaluates rules and triggers alerts
- `RedisConsumer`: Consumes from emotion:events stream
- `RedisPublisher`: Publishes to sentiment:crowd stream
- `Database`: Writes to PostgreSQL

**Responsibilities**:
- Consume emotion detections from Redis
- Aggregate emotions over time windows (default: 60 seconds)
- Calculate sentiment score (-1 to +1)
- Evaluate custom rules (e.g., "Alert if crowd sentiment < -0.5")
- Publish aggregated sentiment to Redis
- Persist sentiment stats to PostgreSQL

**Aggregation Logic**:
```python
sentiment_score = (
    avg_happy * 1.0 +
    avg_neutral * 0.0 +
    avg_sad * -0.5 +
    avg_angry * -1.0 +
    avg_fear * -0.8 +
    avg_surprise * 0.3 +
    avg_disgust * -0.7
)
```

**Resource Usage**:
- Memory: 256MB limit
- CPU: Low to moderate
- Database: Moderate writes

**Configuration**:
- Port: 8003
- Aggregation window: 60 seconds
- Rule evaluation frequency: 5 seconds

### 4. API Gateway

**Purpose**: Provides REST API and WebSocket interface for dashboard and external integrations.

**Technology**: Python 3.11, FastAPI, SQLAlchemy, WebSocket

**Key Components**:
- `main.py`: FastAPI app with CORS and routing
- `websocket_manager.py`: Manages WebSocket connections
- `routers/`: REST endpoints for cameras, rules, analytics
- `models.py`: Pydantic models for request/response

**Responsibilities**:
- CRUD operations for cameras and rules
- Query analytics and historical data
- Stream live sentiment updates via WebSocket
- Serve API documentation (Swagger)
- Handle authentication (future)

**Endpoints**:
- `GET /health`: Health check
- `GET /cameras`: List cameras
- `POST /cameras`: Register camera
- `GET /rules`: List rules
- `POST /rules`: Create rule
- `GET /analytics/sentiment`: Get sentiment data
- `WS /ws/live`: Live sentiment stream

**Resource Usage**:
- Memory: 52MB limit
- CPU: Low
- Network: Moderate (WebSocket)

**Configuration**:
- Port: 8000
- CORS: Allow all origins (development)
- Max connections: 100

### 5. Dashboard

**Purpose**: Web-based user interface for monitoring, configuration, and visualization.

**Technology**: Next.js 14, React 18, TypeScript, Tailwind CSS, Axios

**Key Components**:
- `services/api.ts`: API client for REST calls
- `services/websocket.ts`: WebSocket client for live updates
- `pages/`: Page components (Home, Analytics, Rules, Settings)
- `components/`: Reusable UI components

**Responsibilities**:
- Display live sentiment analytics
- Manage cameras (add, edit, delete)
- Configure rules for alerts
- Visualize emotion trends (charts)
- Real-time updates via WebSocket

**Pages**:
- **Home**: Dashboard overview, live camera feeds
- **Analytics**: Historical sentiment trends, charts
- **Rules**: Configure and manage alert rules
- **Settings**: System configuration

**Resource Usage**:
- Memory: ~100MB (browser)
- Network: Low (REST) + Moderate (WebSocket)

**Configuration**:
- Port: 3001 (dev), 3000 (prod)
- API URL: http://localhost:8000
- WebSocket URL: ws://localhost:8000/ws/live

## Data Flow

### Frame Processing Flow

```
1. Camera (RTSP)
   │
   │ RTSP Stream
   ▼
2. Video Ingestion Service
   │ - Capture frame
   │ - Resize to 640x480
   │ - Encode as JPEG
   │
   │ XADD frames:camera_001
   ▼
3. Redis Stream (frames)
   │
   │ XREADGROUP
   ▼
4. Emotion Detection Service
   │ - YOLOv8 face detection
   │ - DeepFace emotion analysis
   │ - Extract features
   │
   │ XADD emotion:events
   ▼
5. Redis Stream (emotion:events)
   │
   ├─────────────────┬─────────────────┐
   │                 │                 │
   │ XREADGROUP      │ XREADGROUP      │
   ▼                 ▼                 ▼
6a. Emotion         6b. Sentiment     6c. API Gateway
    Detection           Analysis          (for monitoring)
    (feedback loop)     │
                        │ Aggregate emotions
                        │ Apply rules
                        │ Calculate sentiment
                        │
                        │ XADD sentiment:crowd
                        ▼
                   7. Redis Stream (sentiment:crowd)
                        │
                        │ XREADGROUP
                        ▼
                   8. API Gateway
                        │ Broadcast via WebSocket
                        ▼
                   9. Dashboard
                        (Live update)
```

### Database Write Flow

```
Sentiment Analysis Service
│
├─ INSERT INTO emotions (...)
│  ├─ Partitioned by timestamp
│  └─ Indexed by camera_id, timestamp
│
├─ INSERT INTO sentiment_stats (...)
│  ├─ Aggregated metrics
│  └─ Indexed by camera_id, timestamp
│
└─ INSERT INTO alerts (...)
   ├─ Rule triggers
   └─ Indexed by rule_id, triggered_at
```

### WebSocket Update Flow

```
1. Sentiment Analysis → Redis (sentiment:crowd)
2. API Gateway → XREADGROUP → Reads new sentiment
3. API Gateway → WebSocket Broadcast → All connected clients
4. Dashboard → Receives update → Updates UI
```

## Communication Patterns

### 1. Pub/Sub via Redis Streams

**Pattern**: Producer publishes messages to Redis stream, consumers read from consumer groups.

**Advantages**:
- Decoupling: Producers and consumers don't know about each other
- Reliability: Messages persist in Redis until consumed
- Scalability: Multiple consumers can process messages in parallel
- Replay: Consumers can re-read messages from any point

**Implementation**:
```python
# Producer
redis_client.xadd('emotion:events', message, maxlen=1000)

# Consumer
messages = redis_client.xreadgroup(
    groupname='sentiment-analyzer-group',
    consumername='worker-1',
    streams={'emotion:events': '>'},
    count=10,
    block=1000
)
```

**Streams**:
- `emotion:events`: Emotion detections (MAXLEN ~1000)
- `sentiment:crowd`: Sentiment analytics (MAXLEN ~10000)

### 2. REST API

**Pattern**: Synchronous HTTP requests for CRUD operations.

**Advantages**:
- Simple: Standard HTTP verbs (GET, POST, PUT, DELETE)
- Stateless: Each request is independent
- Cacheable: GET requests can be cached

**Usage**:
- Camera management (CRUD)
- Rules configuration (CRUD)
- Historical data queries (GET)

### 3. WebSocket

**Pattern**: Persistent bidirectional connection for real-time updates.

**Advantages**:
- Low latency: No HTTP overhead
- Efficient: Single connection for many updates
- Real-time: Instant push notifications

**Usage**:
- Live sentiment updates to dashboard
- Real-time emotion stream visualization

**Message Format**:
```json
{
  "type": "sentiment_update",
  "data": {
    "camera_id": "cam_001",
    "sentiment_score": 0.45,
    "avg_happy": 0.62,
    "avg_neutral": 0.20,
    "timestamp": "2025-12-08T10:30:00Z"
  }
}
```

### 4. Database (PostgreSQL)

**Pattern**: Direct SQL queries for persistence and historical data.

**Advantages**:
- ACID transactions: Data consistency
- Complex queries: JOINs, aggregations, window functions
- Indexing: Fast lookups on time ranges

**Usage**:
- Store camera configurations
- Persist emotion detections (partitioned)
- Store sentiment aggregations
- Log alerts and rule triggers

## Design Decisions

### 1. Hybrid Docker Compose Setup

**Decision**: Run infrastructure (PostgreSQL, Redis, API Gateway) in Docker, but run Python services locally.

**Rationale**:
- **Storage savings**: PyTorch and DeepFace are ~2GB; local installation avoids duplicating in Docker images
- **Development speed**: Faster iteration without rebuilding Docker images
- **Resource efficiency**: Local Python env shared across services

**Trade-off**:
- Setup complexity: Developers need to install Python dependencies locally
- Consistency: Docker would provide more consistent environments

### 2. Redis Streams Over Message Queue

**Decision**: Use Redis Streams instead of RabbitMQ or Kafka.

**Rationale**:
- **Simplicity**: Redis already used for caching; one less service to manage
- **Performance**: Redis Streams are fast (~100k msg/sec)
- **Consumer groups**: Built-in support for multiple consumers
- **Stream replay**: Can re-read messages for debugging

**Trade-off**:
- Feature set: Kafka has more advanced features (partitioning, replication)
- Persistence: Redis is primarily in-memory (AOF enabled for durability)

### 3. Partitioned Emotions Table

**Decision**: Partition emotions table by timestamp (monthly partitions).

**Rationale**:
- **Performance**: Queries on recent data are much faster
- **Maintenance**: Old partitions can be dropped easily
- **Scalability**: Partitions can be moved to separate disks

**Trade-off**:
- Complexity: Need to create partitions manually or with automation
- Cross-partition queries: Slower if querying across multiple months

### 4. Microservices Architecture

**Decision**: Split into 5 independent services instead of monolithic application.

**Rationale**:
- **Scalability**: Scale emotion detection independently from ingestion
- **Resilience**: Failure in one service doesn't crash entire system
- **Technology choice**: Use best tool for each job (PyTorch for ML, React for UI)
- **Team autonomy**: Different teams can work on different services

**Trade-off**:
- Operational complexity: More services to deploy and monitor
- Network overhead: Inter-service communication adds latency

### 5. DeepFace for Emotion Detection

**Decision**: Use DeepFace library instead of training custom model.

**Rationale**:
- **Accuracy**: DeepFace provides state-of-the-art emotion recognition
- **Speed**: Pre-trained models available, no training required
- **Maintenance**: Library is actively maintained

**Trade-off**:
- Model size: DeepFace models are large (~500MB)
- Customization: Limited ability to fine-tune for specific use cases

### 6. Next.js for Dashboard

**Decision**: Use Next.js (React framework) instead of pure React or Vue.

**Rationale**:
- **SSR support**: Server-side rendering for better SEO
- **File-based routing**: Simpler than React Router
- **Built-in optimizations**: Image optimization, code splitting
- **TypeScript support**: Strong typing for better DX

**Trade-off**:
- Learning curve: Next.js has its own conventions
- Bundle size: Larger than minimal React setup

## Technology Stack

### Backend Services

| Service | Language | Framework | Key Libraries |
|---------|----------|-----------|---------------|
| Video Ingestion | Python 3.11 | FastAPI | OpenCV, redis-py |
| Emotion Detection | Python 3.11 | FastAPI | PyTorch, DeepFace, YOLOv8 |
| Sentiment Analysis | Python 3.11 | FastAPI | Pandas, SQLAlchemy |
| API Gateway | Python 3.11 | FastAPI | SQLAlchemy, WebSocket |

### Frontend

| Component | Technology | Version |
|-----------|------------|---------|
| Framework | Next.js | 14.0 |
| UI Library | React | 18.2 |
| Language | TypeScript | 5.0 |
| Styling | Tailwind CSS | 3.4 |
| HTTP Client | Axios | 1.6 |

### Infrastructure

| Service | Technology | Version | Purpose |
|---------|------------|---------|---------|
| Database | PostgreSQL | 15-alpine | Data persistence |
| Cache/Streams | Redis | 7-alpine | Message streaming, caching |
| Container | Docker | 20.10+ | Containerization |
| Orchestration | Docker Compose | v2+ | Local development |

### Machine Learning

| Model | Framework | Purpose |
|-------|-----------|---------|
| YOLOv8n | Ultralytics | Face detection |
| DeepFace | TensorFlow/Keras | Emotion recognition |

## Deployment Model

### Development Environment

```
Local Machine
├─ Docker (PostgreSQL, Redis, API Gateway)
├─ Python venv (Emotion Detection, Sentiment Analysis, Video Ingestion)
└─ Node.js (Dashboard)
```

### Production Environment (Future)

```
Kubernetes Cluster
├─ Namespace: vantagenet
├─ PostgreSQL (StatefulSet with PVC)
├─ Redis (StatefulSet with PVC)
├─ API Gateway (Deployment, 2 replicas)
├─ Emotion Detection (Deployment, 3 replicas)
├─ Sentiment Analysis (Deployment, 2 replicas)
├─ Video Ingestion (Deployment, 2 replicas)
└─ Dashboard (Deployment, 2 replicas, Ingress)
```

### Scaling Strategy

**Horizontal Scaling**:
- Emotion Detection: Scale to N replicas based on CPU usage
- Sentiment Analysis: Scale based on Redis stream lag
- Video Ingestion: One replica per camera (or camera group)

**Vertical Scaling**:
- Emotion Detection: Increase memory for larger models or batch processing
- PostgreSQL: Increase storage as data grows

**Resource Limits** (Production):
```yaml
emotion-detection:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: 2000m
    memory: 1Gi
```

## Performance Characteristics

### Latency

- Frame capture to Redis: ~10ms
- Emotion detection per frame: ~150ms (CPU), ~50ms (GPU)
- Sentiment aggregation: ~5ms
- API Gateway response: ~10ms
- WebSocket update: ~5ms
- **End-to-end latency**: ~180ms (camera to dashboard)

### Throughput

- Video Ingestion: 30 FPS per camera
- Emotion Detection: ~6 frames/sec per replica (CPU)
- Sentiment Analysis: ~200 updates/sec
- API Gateway: ~1000 req/sec
- WebSocket: ~10k messages/sec

### Resource Usage (Development)

| Service | Memory | CPU |
|---------|--------|-----|
| PostgreSQL | ~150MB | 0.1 cores |
| Redis | ~50MB | 0.1 cores |
| API Gateway | ~52MB | 0.1 cores |
| Emotion Detection | ~512MB | 0.8 cores |
| Sentiment Analysis | ~256MB | 0.2 cores |
| Video Ingestion | ~256MB | 0.3 cores |
| Dashboard | ~100MB | 0.1 cores |
| **Total** | **~1.4GB** | **1.8 cores** |

## Security Considerations

### Current State (Development)

- No authentication/authorization
- CORS allow all origins
- Database credentials in environment variables
- No HTTPS/TLS encryption

### Future Improvements

- Add JWT-based authentication
- Implement role-based access control (RBAC)
- Use secrets management (Kubernetes Secrets, Vault)
- Enable HTTPS with Let's Encrypt
- Encrypt database connections (SSL)
- Add rate limiting on API Gateway
- Implement input validation and sanitization

## Monitoring & Observability

### Logs

Each service logs to stdout/stderr with structured logging:
```python
logger.info("Processing frame", extra={
    "camera_id": "cam_001",
    "frame_id": "frame_12345",
    "processing_time_ms": 150
})
```

### Metrics (Future)

- Prometheus metrics exposed on `/metrics` endpoint
- Key metrics:
  - Frames processed per second
  - Emotion detection latency
  - Redis stream lag
  - API response times
  - WebSocket connection count

### Tracing (Future)

- OpenTelemetry for distributed tracing
- Trace request flow from camera to dashboard
- Identify bottlenecks in pipeline

## References

- [SETUP.md](./SETUP.md) - Development setup guide
- [API.md](./API.md) - API documentation
- [DATABASE.md](./DATABASE.md) - Database schema details
- [redis-streams.md](./redis-streams.md) - Redis Streams architecture
- [database-schema.md](./database-schema.md) - Detailed schema documentation
