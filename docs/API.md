# VantageNet API Documentation

Complete API reference for the VantageNet API Gateway, including REST endpoints, WebSocket protocol, and error handling.

## Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [REST API](#rest-api)
  - [Health & Status](#health--status)
  - [Cameras](#cameras)
  - [Rules](#rules)
  - [Analytics](#analytics)
- [WebSocket API](#websocket-api)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Examples](#examples)

## Base URL

**Development**: `http://localhost:8000`
**Production**: `https://api.vantagenet.example.com` (TBD)

## Authentication

**Current**: No authentication required (development mode)

**Future**: JWT-based authentication
```http
Authorization: Bearer <token>
```

## REST API

### Health & Status

#### GET /health

Get API Gateway health status.

**Response**: `200 OK`
```json
{
  "status": "healthy",
  "service": "api-gateway",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "memory_mb": 52.3,
  "timestamp": "2025-12-08T10:30:00Z"
}
```

**Example**:
```bash
curl http://localhost:8000/health
```

#### GET /

Get API information and links.

**Response**: `200 OK`
```json
{
  "service": "VantageNet API Gateway",
  "version": "1.0.0",
  "docs": "http://localhost:8000/docs",
  "health": "http://localhost:8000/health"
}
```

---

### Cameras

#### POST /api/cameras

Create and register a new camera.

**Request Body**:
```json
{
  "name": "Lobby Camera 1",
  "source_type": "rtsp",
  "source_url": "rtsp://192.168.1.100:554/stream",
  "enabled": true,
  "metadata": {
    "location": "Building A - Lobby",
    "floor": 1,
    "zone": "entrance"
  }
}
```

**Request Schema**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Camera display name |
| `source_type` | string | Yes | Type: `rtsp`, `http`, `file` |
| `source_url` | string | Yes | Stream URL or file path |
| `enabled` | boolean | No | Enable/disable camera (default: `true`) |
| `metadata` | object | No | Additional metadata |

**Response**: `201 Created`
```json
{
  "camera_id": "cam_001",
  "name": "Lobby Camera 1",
  "source_type": "rtsp",
  "source_url": "rtsp://192.168.1.100:554/stream",
  "enabled": true,
  "status": "inactive",
  "frames_processed": 0,
  "last_frame_time": null,
  "created_at": "2025-12-08T10:30:00Z",
  "metadata": {
    "location": "Building A - Lobby",
    "floor": 1,
    "zone": "entrance"
  }
}
```

**Example**:
```bash
curl -X POST http://localhost:8000/api/cameras \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Lobby Camera 1",
    "source_type": "rtsp",
    "source_url": "rtsp://192.168.1.100:554/stream",
    "enabled": true,
    "metadata": {
      "location": "Building A - Lobby"
    }
  }'
```

#### GET /api/cameras

List all registered cameras.

**Response**: `200 OK`
```json
[
  {
    "camera_id": "cam_001",
    "name": "Lobby Camera 1",
    "source_type": "rtsp",
    "source_url": "rtsp://192.168.1.100:554/stream",
    "enabled": true,
    "status": "active",
    "frames_processed": 15234,
    "last_frame_time": "2025-12-08T10:30:00Z",
    "created_at": "2025-12-08T09:00:00Z",
    "metadata": {
      "location": "Building A - Lobby"
    }
  },
  {
    "camera_id": "cam_002",
    "name": "Cafeteria Camera",
    "source_type": "rtsp",
    "source_url": "rtsp://192.168.1.101:554/stream",
    "enabled": true,
    "status": "active",
    "frames_processed": 12890,
    "last_frame_time": "2025-12-08T10:29:58Z",
    "created_at": "2025-12-08T09:15:00Z",
    "metadata": {
      "location": "Building A - Cafeteria"
    }
  }
]
```

**Example**:
```bash
curl http://localhost:8000/api/cameras
```

#### GET /api/cameras/{camera_id}

Get camera details by ID.

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `camera_id` | string | Camera ID (e.g., `cam_001`) |

**Response**: `200 OK`
```json
{
  "camera_id": "cam_001",
  "name": "Lobby Camera 1",
  "source_type": "rtsp",
  "source_url": "rtsp://192.168.1.100:554/stream",
  "enabled": true,
  "status": "active",
  "frames_processed": 15234,
  "last_frame_time": "2025-12-08T10:30:00Z",
  "created_at": "2025-12-08T09:00:00Z",
  "metadata": {
    "location": "Building A - Lobby"
  }
}
```

**Error**: `404 Not Found`
```json
{
  "error": "Not Found",
  "detail": "Camera cam_999 not found",
  "timestamp": "2025-12-08T10:30:00Z"
}
```

**Example**:
```bash
curl http://localhost:8000/api/cameras/cam_001
```

#### PUT /api/cameras/{camera_id}

Update camera configuration.

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `camera_id` | string | Camera ID (e.g., `cam_001`) |

**Request Body** (all fields optional):
```json
{
  "name": "Lobby Camera 1 - Updated",
  "enabled": false,
  "metadata": {
    "location": "Building A - Lobby (Relocated)",
    "maintenance": true
  }
}
```

**Response**: `200 OK`
```json
{
  "camera_id": "cam_001",
  "name": "Lobby Camera 1 - Updated",
  "source_type": "rtsp",
  "source_url": "rtsp://192.168.1.100:554/stream",
  "enabled": false,
  "status": "inactive",
  "frames_processed": 15234,
  "last_frame_time": "2025-12-08T10:30:00Z",
  "created_at": "2025-12-08T09:00:00Z",
  "metadata": {
    "location": "Building A - Lobby (Relocated)",
    "maintenance": true
  }
}
```

**Example**:
```bash
curl -X PUT http://localhost:8000/api/cameras/cam_001 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Lobby Camera 1 - Updated",
    "enabled": false
  }'
```

#### DELETE /api/cameras/{camera_id}

Delete a camera.

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `camera_id` | string | Camera ID (e.g., `cam_001`) |

**Response**: `204 No Content`

**Error**: `404 Not Found`
```json
{
  "error": "Not Found",
  "detail": "Camera cam_999 not found",
  "timestamp": "2025-12-08T10:30:00Z"
}
```

**Example**:
```bash
curl -X DELETE http://localhost:8000/api/cameras/cam_001
```

---

### Rules

Rules allow you to define conditions and actions for sentiment/emotion monitoring. The API supports CRUD operations, enable/disable, and historical evaluation tracking.

#### POST /api/rules

Create a new sentiment/emotion rule.

**Request Body**:
```json
{
  "name": "High Anger Detection",
  "type": "threshold",
  "condition_json": {
    "emotion": "angry",
    "threshold": 0.7,
    "min_confidence": 0.8
  },
  "action": "alert",
  "enabled": true
}
```

**Request Schema**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Rule name (1-200 chars, must be unique) |
| `type` | string | Yes | Type: `threshold`, `trend`, `duration`, `sentiment` |
| `condition_json` | object | Yes | Rule configuration (varies by type) |
| `action` | string | Yes | Action: `log`, `alert`, `notification`, `webhook`, `email` |
| `enabled` | boolean | No | Enable/disable rule (default: `true`) |

**Condition JSON by Type**:
- **threshold**: `{ "emotion": "angry", "threshold": 0.7, "min_confidence": 0.8 }`
- **sentiment**: `{ "sentiment_threshold": 0.5, "min_confidence": 0.7 }`
- **duration**: `{ "emotion": "sad", "threshold": 0.6, "duration_seconds": 30 }`
- **trend**: `{ "window_size": 10, "trend_direction": "increasing" }`

**Validation Rules**:
- `threshold`, `sentiment_threshold`, `min_confidence`: Must be 0.0-1.0
- `duration_seconds`: Must be positive number
- Rule names must be unique

**Response**: `201 Created`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "High Anger Detection",
  "type": "threshold",
  "condition_json": {
    "emotion": "angry",
    "threshold": 0.7,
    "min_confidence": 0.8
  },
  "action": "alert",
  "enabled": true,
  "created_at": "2025-12-16T10:30:00Z",
  "updated_at": "2025-12-16T10:30:00Z"
}
```

**Error Responses**:
- `400 Bad Request`: Invalid input (e.g., threshold out of range, missing required fields)
- `409 Conflict`: Rule with this name already exists

**Example**:
```bash
curl -X POST http://localhost:8000/api/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "High Anger Detection",
    "type": "threshold",
    "condition_json": {
      "emotion": "angry",
      "threshold": 0.7,
      "min_confidence": 0.8
    },
    "action": "alert",
    "enabled": true
  }'
```

#### GET /api/rules

List all rules.

**Response**: `200 OK`
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "High Anger Detection",
    "type": "threshold",
    "condition_json": {
      "emotion": "angry",
      "threshold": 0.7
    },
    "action": "alert",
    "enabled": true,
    "created_at": "2025-12-16T09:00:00Z",
    "updated_at": "2025-12-16T09:00:00Z"
  },
  {
    "id": "660e8400-e29b-41d4-a716-446655440001",
    "name": "Negative Sentiment Trend",
    "type": "sentiment",
    "condition_json": {
      "sentiment_threshold": -0.5
    },
    "action": "email",
    "enabled": true,
    "created_at": "2025-12-16T09:15:00Z",
    "updated_at": "2025-12-16T09:15:00Z"
  }
]
```

**Example**:
```bash
curl http://localhost:8000/api/rules
```

#### GET /api/rules/{rule_id}

Get rule details by ID.

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `rule_id` | uuid | Rule UUID |

**Response**: `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "High Anger Detection",
  "type": "threshold",
  "condition_json": {
    "emotion": "angry",
    "threshold": 0.7,
    "min_confidence": 0.8
  },
  "action": "alert",
  "enabled": true,
  "created_at": "2025-12-16T09:00:00Z",
  "updated_at": "2025-12-16T09:00:00Z"
}
```

**Error Responses**:
- `404 Not Found`: Rule does not exist

**Example**:
```bash
curl http://localhost:8000/api/rules/550e8400-e29b-41d4-a716-446655440000
```

#### PUT /api/rules/{rule_id}

Update rule configuration.

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `rule_id` | uuid | Rule UUID |

**Request Body** (all fields optional):
```json
{
  "name": "Updated Rule Name",
  "type": "threshold",
  "condition_json": {
    "emotion": "angry",
    "threshold": 0.8
  },
  "action": "webhook",
  "enabled": false
}
```

**Response**: `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Updated Rule Name",
  "type": "threshold",
  "condition_json": {
    "emotion": "angry",
    "threshold": 0.8
  },
  "action": "webhook",
  "enabled": false,
  "created_at": "2025-12-16T09:00:00Z",
  "updated_at": "2025-12-16T11:30:00Z"
}
```

**Error Responses**:
- `400 Bad Request`: Invalid input
- `404 Not Found`: Rule does not exist
- `409 Conflict`: Duplicate rule name

**Example**:
```bash
curl -X PUT http://localhost:8000/api/rules/550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -d '{
    "condition_json": {
      "threshold": 0.8
    }
  }'
```

#### DELETE /api/rules/{rule_id}

Delete a rule.

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `rule_id` | uuid | Rule UUID |

**Response**: `204 No Content`

**Error Responses**:
- `404 Not Found`: Rule does not exist

**Example**:
```bash
curl -X DELETE http://localhost:8000/api/rules/550e8400-e29b-41d4-a716-446655440000
```

#### PATCH /api/rules/{rule_id}/enable

Enable a rule.

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `rule_id` | uuid | Rule UUID |

**Response**: `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "High Anger Detection",
  "type": "threshold",
  "condition_json": {
    "emotion": "angry",
    "threshold": 0.7
  },
  "action": "alert",
  "enabled": true,
  "created_at": "2025-12-16T09:00:00Z",
  "updated_at": "2025-12-16T11:45:00Z"
}
```

**Error Responses**:
- `404 Not Found`: Rule does not exist

**Example**:
```bash
curl -X PATCH http://localhost:8000/api/rules/550e8400-e29b-41d4-a716-446655440000/enable
```

#### PATCH /api/rules/{rule_id}/disable

Disable a rule.

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `rule_id` | uuid | Rule UUID |

**Response**: `200 OK`
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "High Anger Detection",
  "type": "threshold",
  "condition_json": {
    "emotion": "angry",
    "threshold": 0.7
  },
  "action": "alert",
  "enabled": false,
  "created_at": "2025-12-16T09:00:00Z",
  "updated_at": "2025-12-16T11:46:00Z"
}
```

**Error Responses**:
- `404 Not Found`: Rule does not exist

**Example**:
```bash
curl -X PATCH http://localhost:8000/api/rules/550e8400-e29b-41d4-a716-446655440000/disable
```

#### GET /api/rules/{rule_id}/history

Get past rule evaluations (history).

Returns evaluation history from the rule_evaluations table, showing when the rule was evaluated, whether it matched, and what action was taken.

**Path Parameters**:
| Parameter | Type | Description |
|-----------|------|-------------|
| `rule_id` | uuid | Rule UUID |

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | Number of records to return (1-1000, default: 100) |
| `matched_only` | boolean | No | Filter by matched status (true/false) |

**Response**: `200 OK`
```json
[
  {
    "id": "770e8400-e29b-41d4-a716-446655440002",
    "rule_id": "550e8400-e29b-41d4-a716-446655440000",
    "camera_id": "880e8400-e29b-41d4-a716-446655440003",
    "evaluated_at": "2025-12-16T11:30:00Z",
    "matched": true,
    "emotion": "angry",
    "sentiment_score": null,
    "threshold_value": 0.75,
    "evaluation_result": {
      "detected_value": 0.82,
      "threshold": 0.7,
      "confidence": 0.85
    },
    "action_taken": "alert"
  },
  {
    "id": "770e8400-e29b-41d4-a716-446655440003",
    "rule_id": "550e8400-e29b-41d4-a716-446655440000",
    "camera_id": "880e8400-e29b-41d4-a716-446655440003",
    "evaluated_at": "2025-12-16T11:15:00Z",
    "matched": false,
    "emotion": "angry",
    "sentiment_score": null,
    "threshold_value": 0.65,
    "evaluation_result": {
      "detected_value": 0.65,
      "threshold": 0.7,
      "confidence": 0.88
    },
    "action_taken": null
  }
]
```

**Error Responses**:
- `404 Not Found`: Rule does not exist

**Example**:
```bash
# Get last 100 evaluations
curl http://localhost:8000/api/rules/550e8400-e29b-41d4-a716-446655440000/history

# Get only matched evaluations
curl "http://localhost:8000/api/rules/550e8400-e29b-41d4-a716-446655440000/history?matched_only=true"

# Get last 50 evaluations
curl "http://localhost:8000/api/rules/550e8400-e29b-41d4-a716-446655440000/history?limit=50"
```

---

### Analytics

#### GET /api/analytics/summary

Get analytics summary (sentiment statistics).

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `camera_id` | string | No | Filter by camera ID |
| `start_time` | ISO 8601 | No | Start time (default: 24h ago) |
| `end_time` | ISO 8601 | No | End time (default: now) |

**Response**: `200 OK`
```json
{
  "summary": {
    "avg_sentiment": 0.35,
    "avg_happy": 0.45,
    "avg_neutral": 0.30,
    "avg_sad": 0.10,
    "avg_angry": 0.05,
    "avg_surprise": 0.05,
    "avg_fear": 0.03,
    "avg_disgust": 0.02,
    "total_faces": 1250,
    "total_frames": 5430
  },
  "timeline": [
    {
      "timestamp": "2025-12-08T09:00:00Z",
      "sentiment_score": 0.40,
      "face_count": 15
    },
    {
      "timestamp": "2025-12-08T09:15:00Z",
      "sentiment_score": 0.35,
      "face_count": 18
    }
  ]
}
```

**Example**:
```bash
# Get analytics for all cameras
curl http://localhost:8000/api/analytics/summary

# Get analytics for specific camera
curl "http://localhost:8000/api/analytics/summary?camera_id=cam_001"

# Get analytics for time range
curl "http://localhost:8000/api/analytics/summary?start_time=2025-12-08T00:00:00Z&end_time=2025-12-08T12:00:00Z"
```

---

## WebSocket API

### Connection

**Endpoint**: `ws://localhost:8000/ws/live`

**Protocol**: WebSocket over HTTP

### Message Format

All WebSocket messages follow this format:

```json
{
  "type": "message_type",
  "data": { /* message-specific data */ },
  "timestamp": "2025-12-08T10:30:00Z"
}
```

### Message Types

#### 1. Sentiment Update

Real-time sentiment analytics updates.

**Type**: `sentiment_update`

**Data**:
```json
{
  "type": "sentiment_update",
  "data": {
    "camera_id": "cam_001",
    "sentiment_score": 0.45,
    "avg_happy": 0.62,
    "avg_neutral": 0.20,
    "avg_sad": 0.08,
    "avg_angry": 0.04,
    "avg_surprise": 0.03,
    "avg_fear": 0.02,
    "avg_disgust": 0.01,
    "face_count": 15,
    "time_window": 60
  },
  "timestamp": "2025-12-08T10:30:00Z"
}
```

#### 2. Alert Notification

Alert triggered by rules engine.

**Type**: `alert`

**Data**:
```json
{
  "type": "alert",
  "data": {
    "alert_id": "alert_123",
    "rule_id": "rule_001",
    "rule_name": "High Negative Sentiment Alert",
    "camera_id": "cam_001",
    "message": "Crowd sentiment dropped below -0.5 for 30 seconds",
    "severity": "high",
    "sentiment_score": -0.62
  },
  "timestamp": "2025-12-08T10:30:00Z"
}
```

#### 3. Camera Status

Camera status change notifications.

**Type**: `camera_status`

**Data**:
```json
{
  "type": "camera_status",
  "data": {
    "camera_id": "cam_001",
    "status": "active",
    "frames_processed": 15234,
    "last_frame_time": "2025-12-08T10:30:00Z"
  },
  "timestamp": "2025-12-08T10:30:00Z"
}
```

#### 4. Error

Error notifications from backend.

**Type**: `error`

**Data**:
```json
{
  "type": "error",
  "data": {
    "error": "Connection failed",
    "detail": "Camera cam_001 connection timeout",
    "camera_id": "cam_001"
  },
  "timestamp": "2025-12-08T10:30:00Z"
}
```

### Client Example (JavaScript)

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws/live');

// Handle connection open
ws.onopen = () => {
  console.log('Connected to VantageNet WebSocket');
};

// Handle messages
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  
  switch (message.type) {
    case 'sentiment_update':
      console.log('Sentiment:', message.data.sentiment_score);
      updateDashboard(message.data);
      break;
    
    case 'alert':
      console.warn('Alert:', message.data.message);
      showAlertNotification(message.data);
      break;
    
    case 'camera_status':
      console.log('Camera status:', message.data.status);
      updateCameraStatus(message.data);
      break;
    
    case 'error':
      console.error('Error:', message.data.error);
      break;
  }
};

// Handle errors
ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

// Handle connection close
ws.onclose = () => {
  console.log('Disconnected from WebSocket');
  // Implement reconnection logic
};
```

### Client Example (Python)

```python
import asyncio
import websockets
import json

async def connect():
    uri = "ws://localhost:8000/ws/live"
    
    async with websockets.connect(uri) as websocket:
        print("Connected to VantageNet WebSocket")
        
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            
            if data['type'] == 'sentiment_update':
                print(f"Sentiment: {data['data']['sentiment_score']}")
            
            elif data['type'] == 'alert':
                print(f"ALERT: {data['data']['message']}")

# Run client
asyncio.run(connect())
```

---

## Error Handling

### Error Response Format

All error responses follow this format:

```json
{
  "error": "Error Type",
  "detail": "Detailed error message",
  "timestamp": "2025-12-08T10:30:00Z"
}
```

### HTTP Status Codes

| Status Code | Description | Example |
|-------------|-------------|---------|
| `200 OK` | Success | GET request successful |
| `201 Created` | Resource created | Camera or rule created |
| `204 No Content` | Success, no response body | DELETE successful |
| `400 Bad Request` | Invalid request | Missing required field |
| `404 Not Found` | Resource not found | Camera ID doesn't exist |
| `422 Unprocessable Entity` | Validation error | Invalid field type |
| `500 Internal Server Error` | Server error | Unexpected exception |

### Error Examples

#### 400 Bad Request
```json
{
  "error": "Bad Request",
  "detail": "Field 'name' is required",
  "timestamp": "2025-12-08T10:30:00Z"
}
```

#### 404 Not Found
```json
{
  "error": "Not Found",
  "detail": "Camera cam_999 not found",
  "timestamp": "2025-12-08T10:30:00Z"
}
```

#### 422 Validation Error
```json
{
  "error": "Validation Error",
  "detail": "value is not a valid enumeration member; permitted: 'rtsp', 'http', 'file'",
  "timestamp": "2025-12-08T10:30:00Z"
}
```

#### 500 Internal Server Error
```json
{
  "error": "Internal Server Error",
  "detail": "Database connection failed",
  "timestamp": "2025-12-08T10:30:00Z"
}
```

---

## Rate Limiting

**Current**: No rate limiting (development mode)

**Future**: Rate limits will be enforced:
- **Authenticated users**: 1000 requests/hour
- **Anonymous users**: 100 requests/hour
- **WebSocket**: 1 connection per user

Rate limit headers:
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 987
X-RateLimit-Reset: 1670500800
```

---

## Examples

### Complete Workflow

```bash
# 1. Create a camera
CAMERA_RESPONSE=$(curl -s -X POST http://localhost:8000/api/cameras \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Camera",
    "source_type": "rtsp",
    "source_url": "rtsp://example.com/stream",
    "enabled": true
  }')

CAMERA_ID=$(echo $CAMERA_RESPONSE | jq -r '.camera_id')
echo "Created camera: $CAMERA_ID"

# 2. Create a rule for this camera
curl -X POST http://localhost:8000/api/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Low Sentiment Alert",
    "rule_type": "sentiment_threshold",
    "conditions": {
      "sentiment_score": {
        "operator": "less_than",
        "value": -0.5
      }
    },
    "actions": {
      "send_email": true,
      "email_recipients": ["admin@example.com"]
    },
    "enabled": true,
    "camera_ids": ["'$CAMERA_ID'"]
  }'

# 3. Get analytics
curl "http://localhost:8000/api/analytics/summary?camera_id=$CAMERA_ID"

# 4. Update camera
curl -X PUT "http://localhost:8000/api/cameras/$CAMERA_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "enabled": false
  }'

# 5. Delete camera
curl -X DELETE "http://localhost:8000/api/cameras/$CAMERA_ID"
```

### WebSocket Connection Test

```bash
# Using websocat (install: cargo install websocat)
websocat ws://localhost:8000/ws/live

# Using wscat (install: npm install -g wscat)
wscat -c ws://localhost:8000/ws/live
```

---

## Interactive Documentation

FastAPI provides interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

These interfaces allow you to:
- Browse all endpoints
- View request/response schemas
- Test endpoints directly from the browser
- Download OpenAPI specification

---

## SDK Examples

### Python SDK

```python
import requests

class VantageNetClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def create_camera(self, name, source_url, source_type="rtsp"):
        response = requests.post(
            f"{self.base_url}/api/cameras",
            json={
                "name": name,
                "source_type": source_type,
                "source_url": source_url,
                "enabled": True
            }
        )
        response.raise_for_status()
        return response.json()
    
    def get_analytics(self, camera_id=None):
        params = {}
        if camera_id:
            params['camera_id'] = camera_id
        
        response = requests.get(
            f"{self.base_url}/api/analytics/summary",
            params=params
        )
        response.raise_for_status()
        return response.json()

# Usage
client = VantageNetClient()
camera = client.create_camera("My Camera", "rtsp://example.com/stream")
analytics = client.get_analytics(camera['camera_id'])
print(f"Average sentiment: {analytics['summary']['avg_sentiment']}")
```

### TypeScript/JavaScript SDK

```typescript
class VantageNetClient {
  constructor(private baseUrl: string = 'http://localhost:8000') {}
  
  async createCamera(data: {
    name: string;
    source_url: string;
    source_type?: string;
  }): Promise<any> {
    const response = await fetch(`${this.baseUrl}/api/cameras`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ...data,
        source_type: data.source_type || 'rtsp',
        enabled: true
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }
    
    return response.json();
  }
  
  async getAnalytics(cameraId?: string): Promise<any> {
    const url = new URL(`${this.baseUrl}/api/analytics/summary`);
    if (cameraId) {
      url.searchParams.set('camera_id', cameraId);
    }
    
    const response = await fetch(url.toString());
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }
    
    return response.json();
  }
}

// Usage
const client = new VantageNetClient();
const camera = await client.createCamera({
  name: 'My Camera',
  source_url: 'rtsp://example.com/stream'
});
const analytics = await client.getAnalytics(camera.camera_id);
console.log(`Average sentiment: ${analytics.summary.avg_sentiment}`);
```

---

## Next Steps

- Read [SETUP.md](./SETUP.md) for development environment setup
- Check [ARCHITECTURE.md](./ARCHITECTURE.md) for system architecture details
- Review [DATABASE.md](./DATABASE.md) for database schema documentation

## Support

For issues or questions:
- **GitHub Issues**: https://github.com/7amo10/VantageNet/issues
- **Documentation**: https://github.com/7amo10/VantageNet/tree/main/docs
