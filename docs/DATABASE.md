# Database Documentation

## Overview

VantageNet uses **PostgreSQL 15** for persistent storage of emotion detection events, sentiment analytics, camera configurations, rule definitions, and alerts. The database is optimized for high-volume write operations and efficient time-series queries.

### Key Features

- **Partitioned Emotions Table**: Monthly partitions for optimal write performance
- **16+ Strategic Indexes**: Optimized for common query patterns
- **Foreign Key Constraints**: Ensures data integrity across relationships
- **Automatic Timestamps**: Trigger-based `updated_at` column management
- **JSONB Support**: Flexible metadata and condition storage

### Quick Stats

- **Tables**: 5 core tables (1 partitioned)
- **Indexes**: 16+ covering timestamp, camera, emotion queries
- **Partitions**: Monthly (emotions table)
- **Write Throughput**: ~1000 emotion events/second
- **Storage Estimate**: ~500MB per month (emotions table)

---

## Table of Contents

- [Schema Overview](#schema-overview)
- [Table Details](#table-details)
- [Indexes and Performance](#indexes-and-performance)
- [Query Examples](#query-examples)
- [Partitioning Strategy](#partitioning-strategy)
- [Optimization Notes](#optimization-notes)
- [Maintenance Procedures](#maintenance-procedures)
- [Backup and Recovery](#backup-and-recovery)
- [Monitoring](#monitoring)

---

## Schema Overview

### Entity Relationship Diagram

```
┌─────────────┐       ┌──────────────────┐       ┌───────────────┐
│  cameras    │◄──────│    emotions      │       │     rules     │
│             │       │  (partitioned)   │       │               │
│ • id (PK)   │       │ • id (PK)        │       │ • id (PK)     │
│ • name      │       │ • frame_id       │       │ • name        │
│ • rtsp_url  │       │ • face_id        │       │ • type        │
│ • location  │       │ • emotion        │       │ • condition   │
│ • active    │       │ • confidence     │       │ • action      │
└─────────────┘       │ • camera_id (FK) │       │ • enabled     │
       │              │ • timestamp      │       └───────────────┘
       │              └──────────────────┘              │
       │                                                │
       │              ┌──────────────────┐              │
       └──────────────│ sentiment_stats  │              │
       │              │                  │              │
       │              │ • id (PK)        │              │
       │              │ • camera_id (FK) │              │
       │              │ • timestamp      │              │
       │              │ • avg_happy      │              │
       │              │ • avg_sad        │              │
       │              │ • avg_angry      │              │
       │              │ • sentiment_score│              │
       │              └──────────────────┘              │
       │                                                │
       │              ┌──────────────────┐              │
       └──────────────│     alerts       │◄─────────────┘
                      │                  │
                      │ • id (PK)        │
                      │ • rule_id (FK)   │
                      │ • camera_id (FK) │
                      │ • message        │
                      │ • severity       │
                      │ • triggered_at   │
                      │ • resolved_at    │
                      └──────────────────┘
```

### Tables Summary

| Table            | Purpose                                  | Partitioned | Estimated Size      |
|------------------|------------------------------------------|-------------|---------------------|
| cameras          | Camera configuration and metadata        | No          | < 1MB (hundreds)    |
| emotions         | Individual emotion detection events      | Yes (monthly)| ~500MB/month       |
| sentiment_stats  | Aggregated sentiment statistics          | No          | ~50MB/year          |
| rules            | Alert rule definitions                   | No          | < 1MB (hundreds)    |
| alerts           | Triggered alert records                  | No          | ~10MB/month         |

---

## Table Details

### 1. cameras

Stores camera configuration and metadata. Each camera represents a video source for emotion detection.

**Schema:**

| Column      | Type            | Constraints       | Description                    |
|-------------|-----------------|-------------------|--------------------------------|
| id          | UUID            | PRIMARY KEY       | Unique camera identifier       |
| name        | VARCHAR(200)    | NOT NULL, UNIQUE  | Camera display name            |
| rtsp_url    | VARCHAR(500)    | NULL              | RTSP stream URL                |
| location    | VARCHAR(500)    | NULL              | Physical location              |
| active      | BOOLEAN         | DEFAULT TRUE      | Camera active status           |
| created_at  | TIMESTAMPTZ     | DEFAULT NOW()     | Record creation timestamp      |
| updated_at  | TIMESTAMPTZ     | DEFAULT NOW()     | Last update timestamp          |

**Example Record:**

```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Store Entrance Camera 1",
  "rtsp_url": "rtsp://192.168.1.100:554/stream1",
  "location": "Store Entrance - Left Side",
  "active": true,
  "created_at": "2025-12-15T10:30:00Z",
  "updated_at": "2025-12-15T10:30:00Z"
}
```

**Indexes:**

- `PRIMARY KEY (id)`: Fast lookups by UUID
- `UNIQUE (name)`: Ensures unique camera names
- `idx_cameras_active`: Partial index on active cameras only
- `idx_cameras_created_at`: Creation date queries

**Relationships:**

- One camera → Many emotions (CASCADE delete)
- One camera → Many sentiment_stats (CASCADE delete)
- One camera → Many alerts (SET NULL on delete)

---

### 2. emotions (Partitioned Table)

Stores individual emotion detection events from video frames. **Partitioned by timestamp** with monthly partitions for optimal performance.

**Schema:**

| Column        | Type            | Constraints       | Description                        |
|---------------|-----------------|-------------------|------------------------------------|
| id            | UUID            | PRIMARY KEY       | Event identifier                   |
| frame_id      | VARCHAR(100)    | NOT NULL          | Video frame identifier             |
| face_id       | VARCHAR(100)    | NULL              | Detected face identifier           |
| emotion       | VARCHAR(50)     | NOT NULL          | Detected emotion label             |
| confidence    | DECIMAL(5,4)    | 0-1, NOT NULL     | Model confidence score             |
| camera_id     | UUID            | NOT NULL, FK      | Reference to camera                |
| timestamp     | TIMESTAMPTZ     | NOT NULL, DEFAULT | Event timestamp (partition key)    |
| bounding_box  | JSONB           | NULL              | Face bounding box coordinates      |
| metadata      | JSONB           | NULL              | Additional event metadata          |
| created_at    | TIMESTAMPTZ     | DEFAULT NOW()     | Record creation timestamp          |

**Supported Emotions:**

- `happy`, `sad`, `angry`, `neutral`, `surprised`, `fear`, `disgust`

**Example Record:**

```json
{
  "id": "223e4567-e89b-12d3-a456-426614174001",
  "frame_id": "frame_1702649400_001",
  "face_id": "face_42",
  "emotion": "happy",
  "confidence": 0.8952,
  "camera_id": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2025-12-15T14:30:00Z",
  "bounding_box": {
    "x": 120,
    "y": 80,
    "width": 150,
    "height": 180
  },
  "metadata": {
    "face_size": "large",
    "quality": "high"
  },
  "created_at": "2025-12-15T14:30:00.123Z"
}
```

**Partitioning:**

- Monthly partitions: `emotions_2025_12`, `emotions_2026_01`, etc.
- Partition key: `timestamp`
- Automatic partition creation available (see [Partitioning Strategy](#partitioning-strategy))

**Indexes (per partition):**

- `PRIMARY KEY (id)`: Fast lookups by UUID
- `idx_emotions_timestamp`: Timestamp DESC for latest events
- `idx_emotions_camera_id`: `(camera_id, timestamp)` composite for filtering
- `idx_emotions_emotion`: `(emotion, timestamp)` for emotion-specific queries
- `idx_emotions_frame_id`: Frame lookups
- `idx_emotions_face_id`: Face tracking (partial, where `face_id IS NOT NULL`)

**Foreign Keys:**

- `camera_id` → `cameras(id)` ON DELETE CASCADE

**Performance Notes:**

- Writes: ~1000 events/second sustained
- Reads: Partition pruning for time-range queries
- Storage: ~500MB per month (typical load)

---

### 3. sentiment_stats

Stores aggregated sentiment statistics per camera over time windows. Calculated by sentiment-analysis service.

**Schema:**

| Column              | Type            | Constraints       | Description                       |
|---------------------|-----------------|-------------------|-----------------------------------|
| id                  | UUID            | PRIMARY KEY       | Stats record identifier           |
| camera_id           | UUID            | NOT NULL, FK      | Reference to camera               |
| timestamp           | TIMESTAMPTZ     | NOT NULL, DEFAULT | Stats calculation timestamp       |
| time_window_start   | TIMESTAMPTZ     | NOT NULL          | Window start time                 |
| time_window_end     | TIMESTAMPTZ     | NOT NULL          | Window end time                   |
| total_faces         | INTEGER         | DEFAULT 0, ≥0     | Total faces in window             |
| avg_happy           | DECIMAL(5,4)    | 0-1, NULL         | Average happy score               |
| avg_sad             | DECIMAL(5,4)    | 0-1, NULL         | Average sad score                 |
| avg_angry           | DECIMAL(5,4)    | 0-1, NULL         | Average angry score               |
| avg_neutral         | DECIMAL(5,4)    | 0-1, NULL         | Average neutral score             |
| avg_surprised       | DECIMAL(5,4)    | 0-1, NULL         | Average surprised score           |
| avg_fear            | DECIMAL(5,4)    | 0-1, NULL         | Average fear score                |
| avg_disgust         | DECIMAL(5,4)    | 0-1, NULL         | Average disgust score             |
| dominant_emotion    | VARCHAR(50)     | NULL              | Most prevalent emotion            |
| sentiment_score     | DECIMAL(5,4)    | -1 to 1, NULL     | Overall sentiment score           |
| average_confidence  | DECIMAL(5,4)    | 0-1, NULL         | Average detection confidence      |
| emotion_distribution| JSONB           | NULL              | Full emotion distribution         |
| metadata            | JSONB           | NULL              | Additional statistics             |
| created_at          | TIMESTAMPTZ     | DEFAULT NOW()     | Record creation timestamp         |

**Sentiment Score Interpretation:**

- `-1.0 to -0.5`: Highly negative
- `-0.5 to -0.1`: Negative
- `-0.1 to 0.1`: Neutral
- `0.1 to 0.5`: Positive
- `0.5 to 1.0`: Highly positive

**Example Record:**

```json
{
  "id": "323e4567-e89b-12d3-a456-426614174002",
  "camera_id": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2025-12-15T14:35:00Z",
  "time_window_start": "2025-12-15T14:30:00Z",
  "time_window_end": "2025-12-15T14:35:00Z",
  "total_faces": 42,
  "avg_happy": 0.6234,
  "avg_sad": 0.1123,
  "avg_angry": 0.0532,
  "avg_neutral": 0.1876,
  "avg_surprised": 0.0156,
  "avg_fear": 0.0045,
  "avg_disgust": 0.0034,
  "dominant_emotion": "happy",
  "sentiment_score": 0.4512,
  "average_confidence": 0.8845,
  "emotion_distribution": {
    "happy": 26,
    "neutral": 8,
    "sad": 5,
    "angry": 2,
    "surprised": 1
  },
  "metadata": {
    "aggregation_method": "weighted_average",
    "min_confidence_threshold": 0.7
  },
  "created_at": "2025-12-15T14:35:02Z"
}
```

**Indexes:**

- `PRIMARY KEY (id)`: Fast lookups by UUID
- `idx_sentiment_stats_timestamp`: Timestamp DESC
- `idx_sentiment_stats_camera_id`: `(camera_id, timestamp)` for filtering
- `idx_sentiment_stats_time_window`: `(time_window_start, time_window_end)` for range queries
- `idx_sentiment_stats_dominant_emotion`: Emotion filtering

**Foreign Keys:**

- `camera_id` → `cameras(id)` ON DELETE CASCADE

---

### 4. rules

Stores sentiment-based alert rule definitions. Rules are evaluated by sentiment-analysis service.

**Schema:**

| Column          | Type            | Constraints       | Description                    |
|-----------------|-----------------|-------------------|--------------------------------|
| id              | UUID            | PRIMARY KEY       | Rule identifier                |
| name            | VARCHAR(200)    | NOT NULL, UNIQUE  | Rule display name              |
| type            | VARCHAR(50)     | NOT NULL          | Rule type (e.g., 'sentiment')  |
| condition_json  | JSONB           | NOT NULL          | Rule condition definition      |
| action          | VARCHAR(100)    | NOT NULL, CHECK   | Action type                    |
| enabled         | BOOLEAN         | DEFAULT TRUE      | Rule enabled status            |
| created_at      | TIMESTAMPTZ     | DEFAULT NOW()     | Rule creation timestamp        |
| updated_at      | TIMESTAMPTZ     | DEFAULT NOW()     | Last update timestamp          |

**Action Types:**

- `alert`: Create alert record in database
- `log`: Log event to service logs
- `webhook`: Send webhook notification (future)
- `email`: Send email notification (future)

**Condition JSON Format:**

```json
{
  "metric": "sentiment_score",
  "operator": "<",
  "threshold": -0.5
}
```

**Supported Operators:**

- `<`, `>`, `<=`, `>=`, `==`, `!=`

**Example Record:**

```json
{
  "id": "423e4567-e89b-12d3-a456-426614174003",
  "name": "High Negative Sentiment Alert",
  "type": "sentiment",
  "condition_json": {
    "metric": "sentiment_score",
    "operator": "<",
    "threshold": -0.5
  },
  "action": "alert",
  "enabled": true,
  "created_at": "2025-12-10T09:00:00Z",
  "updated_at": "2025-12-10T09:00:00Z"
}
```

**Indexes:**

- `PRIMARY KEY (id)`: Fast lookups by UUID
- `UNIQUE (name)`: Ensures unique rule names
- `idx_rules_enabled`: Partial index on enabled rules only
- `idx_rules_type`: Rule type filtering
- `idx_rules_created_at`: Creation date queries

**Relationships:**

- One rule → Many alerts (CASCADE delete)

---

### 5. alerts

Stores triggered alerts from rules with resolution tracking and acknowledgment status.

**Schema:**

| Column           | Type            | Constraints       | Description                    |
|------------------|-----------------|-------------------|--------------------------------|
| id               | UUID            | PRIMARY KEY       | Alert identifier               |
| rule_id          | UUID            | NOT NULL, FK      | Reference to rule              |
| message          | TEXT            | NOT NULL          | Alert message                  |
| severity         | VARCHAR(20)     | NOT NULL, CHECK   | Alert severity level           |
| triggered_at     | TIMESTAMPTZ     | NOT NULL, DEFAULT | Alert trigger timestamp        |
| resolved_at      | TIMESTAMPTZ     | NULL              | Alert resolution timestamp     |
| camera_id        | UUID            | NULL, FK          | Related camera                 |
| trigger_data     | JSONB           | NULL              | Trigger context data           |
| acknowledged     | BOOLEAN         | DEFAULT FALSE     | Acknowledgment status          |
| acknowledged_by  | VARCHAR(100)    | NULL              | User who acknowledged          |
| acknowledged_at  | TIMESTAMPTZ     | NULL              | Acknowledgment timestamp       |
| created_at       | TIMESTAMPTZ     | DEFAULT NOW()     | Record creation timestamp      |

**Severity Levels:**

- `low`: Informational
- `medium`: Warning
- `high`: Important
- `critical`: Urgent action required

**Example Record:**

```json
{
  "id": "523e4567-e89b-12d3-a456-426614174004",
  "rule_id": "423e4567-e89b-12d3-a456-426614174003",
  "message": "High negative sentiment detected: -0.62",
  "severity": "high",
  "triggered_at": "2025-12-15T14:35:05Z",
  "resolved_at": null,
  "camera_id": "123e4567-e89b-12d3-a456-426614174000",
  "trigger_data": {
    "sentiment_score": -0.62,
    "total_faces": 42,
    "dominant_emotion": "sad",
    "time_window": "5min"
  },
  "acknowledged": true,
  "acknowledged_by": "admin@example.com",
  "acknowledged_at": "2025-12-15T14:40:00Z",
  "created_at": "2025-12-15T14:35:05.234Z"
}
```

**Indexes:**

- `PRIMARY KEY (id)`: Fast lookups by UUID
- `idx_alerts_triggered_at`: Trigger timestamp DESC
- `idx_alerts_rule_id`: `(rule_id, triggered_at)` for rule-specific alerts
- `idx_alerts_severity`: Unresolved alerts by severity
- `idx_alerts_camera_id`: Camera-specific alerts
- `idx_alerts_unresolved`: Partial index on unresolved alerts (`resolved_at IS NULL`)

**Foreign Keys:**

- `rule_id` → `rules(id)` ON DELETE CASCADE
- `camera_id` → `cameras(id)` ON DELETE SET NULL

---

## Indexes and Performance

### Index Strategy

VantageNet uses **16+ strategic indexes** optimized for common query patterns:

1. **Composite Indexes**: `(camera_id, timestamp)` for camera-filtered time-range queries
2. **Partial Indexes**: Active/enabled records only to reduce index size
3. **DESC Ordering**: Recent records first (most queries access recent data)
4. **JSONB Indexing**: Available for `condition_json` and `metadata` if needed

### Index Usage Guidelines

**When indexes are used:**

- `WHERE camera_id = '...' AND timestamp > ...` → Uses `idx_emotions_camera_id`
- `WHERE emotion = 'happy' AND timestamp > ...` → Uses `idx_emotions_emotion`
- `WHERE resolved_at IS NULL` → Uses `idx_alerts_unresolved` (partial)
- `ORDER BY timestamp DESC LIMIT 100` → Uses `idx_emotions_timestamp`

**When indexes are NOT used:**

- `WHERE EXTRACT(hour FROM timestamp) = 14` → Full table scan
- `WHERE emotion LIKE 'happ%'` → Full table scan (use `emotion = 'happy'` instead)
- Large result sets (>30% of table) → Postgres may prefer seq scan

### Query Performance

**Typical Query Times** (on emotions table with 10M records):

| Query Type                              | Time      | Index Used                |
|-----------------------------------------|-----------|---------------------------|
| Latest 100 emotions for camera          | < 10ms    | `idx_emotions_camera_id`  |
| Emotion distribution last hour          | < 50ms    | `idx_emotions_timestamp`  |
| Specific emotion over time range        | < 100ms   | `idx_emotions_emotion`    |
| Face tracking across frames             | < 20ms    | `idx_emotions_face_id`    |
| Unresolved alerts                       | < 5ms     | `idx_alerts_unresolved`   |

### Index Maintenance

```sql
-- Check index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as scans,
    idx_tup_read as tuples_read,
    idx_tup_fetch as tuples_fetched,
    pg_size_pretty(pg_relation_size(indexrelid)) as size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan ASC;

-- Find unused indexes (idx_scan = 0)
SELECT 
    schemaname || '.' || tablename as table,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as size
FROM pg_stat_user_indexes
WHERE schemaname = 'public' AND idx_scan = 0;

-- Rebuild bloated indexes
REINDEX TABLE emotions_2025_12;
```

---

## Query Examples

### 1. Insert Camera

```sql
INSERT INTO cameras (id, name, rtsp_url, location, active)
VALUES (
    gen_random_uuid(),
    'Store Entrance Camera 1',
    'rtsp://192.168.1.100:554/stream1',
    'Store Entrance - Left Side',
    true
)
RETURNING *;
```

### 2. Insert Emotion Event

```sql
INSERT INTO emotions (
    id, frame_id, face_id, emotion, confidence, 
    camera_id, timestamp, bounding_box
)
VALUES (
    gen_random_uuid(),
    'frame_1702649400_001',
    'face_42',
    'happy',
    0.8952,
    '123e4567-e89b-12d3-a456-426614174000',
    NOW(),
    '{"x": 120, "y": 80, "width": 150, "height": 180}'::jsonb
)
RETURNING *;
```

### 3. Recent Emotions by Camera

```sql
SELECT 
    e.id,
    e.frame_id,
    e.emotion,
    e.confidence,
    e.timestamp,
    c.name as camera_name
FROM emotions e
JOIN cameras c ON e.camera_id = c.id
WHERE 
    c.id = '123e4567-e89b-12d3-a456-426614174000'
    AND e.timestamp > NOW() - INTERVAL '1 hour'
ORDER BY e.timestamp DESC
LIMIT 100;
```

### 4. Emotion Distribution by Camera (Last Hour)

```sql
SELECT 
    c.name as camera,
    e.emotion,
    COUNT(*) as count,
    AVG(e.confidence)::DECIMAL(5,4) as avg_confidence
FROM emotions e
JOIN cameras c ON e.camera_id = c.id
WHERE e.timestamp > NOW() - INTERVAL '1 hour'
GROUP BY c.name, e.emotion
ORDER BY c.name, count DESC;
```

**Expected Output:**

```
        camera         | emotion  | count | avg_confidence
-----------------------+----------+-------+---------------
 Entrance Camera 1     | happy    |   156 |        0.8823
 Entrance Camera 1     | neutral  |    89 |        0.9012
 Entrance Camera 1     | sad      |    23 |        0.7645
 Lobby Camera 2        | happy    |   201 |        0.8956
 Lobby Camera 2        | neutral  |   112 |        0.9123
```

### 5. Average Sentiment by Hour (24 Hours)

```sql
SELECT 
    DATE_TRUNC('hour', timestamp) as hour,
    AVG(sentiment_score)::DECIMAL(5,4) as avg_sentiment,
    SUM(total_faces) as total_faces,
    COUNT(*) as stat_records
FROM sentiment_stats
WHERE 
    camera_id = '123e4567-e89b-12d3-a456-426614174000'
    AND timestamp > NOW() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', timestamp)
ORDER BY hour DESC;
```

**Expected Output:**

```
         hour         | avg_sentiment | total_faces | stat_records
----------------------+---------------+-------------+--------------
 2025-12-15 14:00:00  |        0.4512 |        1242 |           12
 2025-12-15 13:00:00  |        0.3821 |        1189 |           12
 2025-12-15 12:00:00  |        0.2134 |        1056 |           12
```

### 6. Active Unresolved Alerts

```sql
SELECT 
    a.id,
    a.message,
    a.severity,
    a.triggered_at,
    r.name as rule_name,
    c.name as camera_name,
    a.acknowledged,
    a.acknowledged_by
FROM alerts a
JOIN rules r ON a.rule_id = r.id
LEFT JOIN cameras c ON a.camera_id = c.id
WHERE a.resolved_at IS NULL
ORDER BY 
    CASE a.severity
        WHEN 'critical' THEN 1
        WHEN 'high' THEN 2
        WHEN 'medium' THEN 3
        WHEN 'low' THEN 4
    END,
    a.triggered_at DESC;
```

### 7. Top Emotions by Confidence

```sql
SELECT 
    emotion,
    COUNT(*) as occurrences,
    AVG(confidence)::DECIMAL(5,4) as avg_confidence,
    MAX(confidence)::DECIMAL(5,4) as max_confidence,
    MIN(confidence)::DECIMAL(5,4) as min_confidence
FROM emotions
WHERE 
    timestamp > NOW() - INTERVAL '1 hour'
    AND confidence > 0.8
GROUP BY emotion
ORDER BY avg_confidence DESC;
```

### 8. Camera Statistics (Last 24 Hours)

```sql
SELECT 
    c.name as camera,
    COUNT(DISTINCT e.frame_id) as total_frames,
    COUNT(DISTINCT e.face_id) as unique_faces,
    COUNT(*) as total_emotions,
    AVG(e.confidence)::DECIMAL(5,4) as avg_confidence
FROM cameras c
LEFT JOIN emotions e ON c.id = e.camera_id 
    AND e.timestamp > NOW() - INTERVAL '24 hours'
WHERE c.active = true
GROUP BY c.id, c.name
ORDER BY total_emotions DESC;
```

### 9. Sentiment Trend (15-Minute Intervals)

```sql
SELECT 
    DATE_TRUNC('minute', timestamp) 
        - INTERVAL '1 minute' * (EXTRACT(minute FROM timestamp)::int % 15) as interval_start,
    AVG(sentiment_score)::DECIMAL(5,4) as avg_sentiment,
    MAX(sentiment_score)::DECIMAL(5,4) as max_sentiment,
    MIN(sentiment_score)::DECIMAL(5,4) as min_sentiment,
    SUM(total_faces) as total_faces
FROM sentiment_stats
WHERE 
    camera_id = '123e4567-e89b-12d3-a456-426614174000'
    AND timestamp > NOW() - INTERVAL '6 hours'
GROUP BY interval_start
ORDER BY interval_start DESC;
```

### 10. Face Tracking Across Frames

```sql
SELECT 
    face_id,
    COUNT(*) as appearances,
    COUNT(DISTINCT frame_id) as unique_frames,
    ARRAY_AGG(DISTINCT emotion ORDER BY emotion) as emotions_detected,
    AVG(confidence)::DECIMAL(5,4) as avg_confidence,
    MIN(timestamp) as first_seen,
    MAX(timestamp) as last_seen
FROM emotions
WHERE 
    face_id IS NOT NULL
    AND timestamp > NOW() - INTERVAL '1 hour'
GROUP BY face_id
HAVING COUNT(*) > 5
ORDER BY appearances DESC
LIMIT 20;
```

### 11. Partition Information

```sql
SELECT 
    parent.relname AS parent_table,
    child.relname AS partition_name,
    pg_get_expr(child.relpartbound, child.oid) AS partition_expression,
    pg_size_pretty(pg_relation_size(child.oid)) as partition_size
FROM pg_inherits
JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
JOIN pg_class child ON pg_inherits.inhrelid = child.oid
WHERE parent.relname = 'emotions'
ORDER BY child.relname DESC;
```

**Expected Output:**

```
 parent_table | partition_name  |      partition_expression       | partition_size
--------------+-----------------+---------------------------------+---------------
 emotions     | emotions_2026_01| FOR VALUES FROM (...) TO (...)  |        523 MB
 emotions     | emotions_2025_12| FOR VALUES FROM (...) TO (...)  |        487 MB
```

### 12. Alert History for Camera

```sql
SELECT 
    a.triggered_at,
    a.resolved_at,
    a.severity,
    a.message,
    r.name as rule_name,
    a.trigger_data->>'sentiment_score' as sentiment_score,
    EXTRACT(EPOCH FROM (COALESCE(a.resolved_at, NOW()) - a.triggered_at)) / 60 as duration_minutes
FROM alerts a
JOIN rules r ON a.rule_id = r.id
WHERE 
    a.camera_id = '123e4567-e89b-12d3-a456-426614174000'
    AND a.triggered_at > NOW() - INTERVAL '7 days'
ORDER BY a.triggered_at DESC;
```

### 13. Batch Insert Emotions (Optimized)

```sql
INSERT INTO emotions (
    id, frame_id, face_id, emotion, confidence, camera_id, timestamp
)
VALUES 
    (gen_random_uuid(), 'frame_001', 'face_1', 'happy', 0.89, '...', NOW()),
    (gen_random_uuid(), 'frame_001', 'face_2', 'neutral', 0.92, '...', NOW()),
    (gen_random_uuid(), 'frame_001', 'face_3', 'sad', 0.78, '...', NOW()),
    (gen_random_uuid(), 'frame_002', 'face_1', 'happy', 0.91, '...', NOW()),
    (gen_random_uuid(), 'frame_002', 'face_2', 'neutral', 0.88, '...', NOW())
RETURNING id, emotion, confidence;
```

### 14. Query Performance Analysis (EXPLAIN ANALYZE)

```sql
EXPLAIN ANALYZE
SELECT 
    e.emotion,
    COUNT(*) as count
FROM emotions e
WHERE 
    e.camera_id = '123e4567-e89b-12d3-a456-426614174000'
    AND e.timestamp > NOW() - INTERVAL '1 hour'
GROUP BY e.emotion;
```

**Expected Plan:**

```
 HashAggregate  (cost=1234.56..1234.78 rows=7 width=16) (actual time=8.234..8.567 rows=5 loops=1)
   Group Key: emotion
   ->  Index Scan using idx_emotions_camera_id on emotions_2025_12 e  (cost=0.56..1200.12 rows=4567 width=8) (actual time=0.123..6.789 rows=4523 loops=1)
         Index Cond: (camera_id = '...')
         Filter: (timestamp > (now() - '01:00:00'::interval))
 Planning Time: 0.234 ms
 Execution Time: 8.678 ms
```

### 15. Delete Old Emotions (Maintenance)

```sql
-- Drop old partition (automatically deletes all data)
DROP TABLE IF EXISTS emotions_2025_01 CASCADE;

-- Or delete from current partition (slower)
DELETE FROM emotions
WHERE timestamp < NOW() - INTERVAL '90 days';
```

---

## Partitioning Strategy

### Why Partitioning?

The `emotions` table uses **range partitioning by timestamp** for several reasons:

1. **Write Performance**: Inserts go to a single partition, reducing index contention
2. **Query Performance**: Partition pruning eliminates scanning irrelevant partitions
3. **Maintenance**: Easy to drop old partitions (instant vs. slow DELETE)
4. **Storage Management**: Archive old partitions to cold storage
5. **Index Size**: Smaller indexes per partition improve cache hit rates

### Partition Scheme

- **Partition Type**: Range partitioning
- **Partition Key**: `timestamp` column
- **Partition Interval**: Monthly (1st of month to 1st of next month)
- **Naming Convention**: `emotions_YYYY_MM`

**Current Partitions:**

```sql
-- December 2025 partition
CREATE TABLE emotions_2025_12 PARTITION OF emotions
FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');

-- January 2026 partition
CREATE TABLE emotions_2026_01 PARTITION OF emotions
FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
```

### Automatic Partition Creation

Use the `create_emotions_partition()` function to create next month's partition:

```sql
-- Create next month's partition
SELECT create_emotions_partition();

-- Or specify year and month
SELECT create_emotions_partition(2026, 2);
```

**Function Definition:**

```sql
CREATE OR REPLACE FUNCTION create_emotions_partition()
RETURNS TEXT AS $$
DECLARE
    partition_date DATE := DATE_TRUNC('month', NOW() + INTERVAL '1 month');
    partition_name TEXT := 'emotions_' || TO_CHAR(partition_date, 'YYYY_MM');
    start_date TEXT := partition_date::TEXT;
    end_date TEXT := (partition_date + INTERVAL '1 month')::TEXT;
BEGIN
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF emotions FOR VALUES FROM (%L) TO (%L)',
        partition_name, start_date, end_date
    );
    RETURN 'Created partition: ' || partition_name;
END;
$$ LANGUAGE plpgsql;
```

### Partition Maintenance Schedule

**Recommended Cron Job:**

```bash
# Create next month's partition on the 25th of each month
0 0 25 * * docker exec vantage-postgres psql -U vantage -d vantage_db -c "SELECT create_emotions_partition();"
```

### Partition Archival

```sql
-- Archive old partition to cold storage
-- 1. Detach partition (makes it a regular table)
ALTER TABLE emotions DETACH PARTITION emotions_2025_01;

-- 2. Dump to file
docker exec vantage-postgres pg_dump -U vantage -t emotions_2025_01 vantage_db > emotions_2025_01.sql

-- 3. Drop partition
DROP TABLE emotions_2025_01;
```

### Querying Across Partitions

Queries automatically scan relevant partitions:

```sql
-- Scans only December 2025 partition
SELECT COUNT(*) FROM emotions
WHERE timestamp >= '2025-12-01' AND timestamp < '2026-01-01';

-- Scans both December 2025 and January 2026 partitions
SELECT COUNT(*) FROM emotions
WHERE timestamp >= '2025-12-15' AND timestamp < '2026-01-15';

-- Scans ALL partitions (avoid this!)
SELECT COUNT(*) FROM emotions;
```

**View partition pruning in EXPLAIN:**

```sql
EXPLAIN SELECT * FROM emotions WHERE timestamp > '2025-12-01';
-- Shows: Seq Scan on emotions_2025_12
```

---

## Optimization Notes

### Write Optimization

**Batch Inserts:**

Use multi-value `INSERT` statements for better performance:

```python
# Good: Batch insert (10x faster)
values = [(uuid.uuid4(), frame_id, emotion, confidence, camera_id, timestamp) 
          for emotion in emotions]
cursor.executemany(
    "INSERT INTO emotions (id, frame_id, emotion, confidence, camera_id, timestamp) VALUES (%s, %s, %s, %s, %s, %s)",
    values
)

# Better: Single INSERT with multiple VALUES
query = "INSERT INTO emotions (id, frame_id, emotion, confidence, camera_id, timestamp) VALUES " + \
        ",".join(["(gen_random_uuid(), %s, %s, %s, %s, %s)"] * len(emotions))
cursor.execute(query, flattened_values)
```

**Connection Pooling:**

Use connection pools to avoid connection overhead:

```python
from psycopg2.pool import ThreadedConnectionPool

pool = ThreadedConnectionPool(
    minconn=5,
    maxconn=20,
    host="localhost",
    port=5433,
    database="vantage_db",
    user="vantage",
    password="vantage123"
)
```

**Disable AutoCommit for Bulk Loads:**

```python
conn.autocommit = False
try:
    cursor.executemany(insert_query, values)
    conn.commit()
except:
    conn.rollback()
    raise
```

### Read Optimization

**Use Appropriate Indexes:**

```sql
-- Good: Uses idx_emotions_camera_id
SELECT * FROM emotions 
WHERE camera_id = '...' AND timestamp > NOW() - INTERVAL '1 hour';

-- Bad: Full table scan
SELECT * FROM emotions 
WHERE EXTRACT(hour FROM timestamp) = 14;
```

**Limit Result Sets:**

```sql
-- Always use LIMIT for large queries
SELECT * FROM emotions 
ORDER BY timestamp DESC 
LIMIT 1000;
```

**Use Partial Indexes for Common Filters:**

```sql
-- Create partial index for high-confidence emotions
CREATE INDEX idx_emotions_high_confidence 
ON emotions (camera_id, timestamp)
WHERE confidence > 0.8;
```

### Query Patterns to Avoid

**1. SELECT * on Large Tables:**

```sql
-- Bad: Fetches all columns
SELECT * FROM emotions WHERE timestamp > NOW() - INTERVAL '1 day';

-- Good: Select only needed columns
SELECT id, emotion, confidence, timestamp FROM emotions 
WHERE timestamp > NOW() - INTERVAL '1 day';
```

**2. Function Calls on Indexed Columns:**

```sql
-- Bad: Function on indexed column prevents index usage
SELECT * FROM emotions WHERE DATE(timestamp) = '2025-12-15';

-- Good: Range query uses index
SELECT * FROM emotions 
WHERE timestamp >= '2025-12-15' AND timestamp < '2025-12-16';
```

**3. OR Conditions on Different Columns:**

```sql
-- Bad: May not use indexes efficiently
SELECT * FROM emotions WHERE camera_id = '...' OR emotion = 'happy';

-- Good: Use UNION or separate queries
SELECT * FROM emotions WHERE camera_id = '...';
UNION ALL
SELECT * FROM emotions WHERE emotion = 'happy' AND camera_id IS DISTINCT FROM '...';
```

### VACUUM and ANALYZE

Regular maintenance improves query planning:

```sql
-- Analyze all tables (updates statistics)
ANALYZE;

-- Vacuum and analyze specific table
VACUUM ANALYZE emotions;

-- Verbose output
VACUUM VERBOSE ANALYZE emotions_2025_12;
```

**Recommended Schedule:**

```bash
# Daily ANALYZE
0 2 * * * docker exec vantage-postgres psql -U vantage -d vantage_db -c "ANALYZE;"

# Weekly VACUUM ANALYZE
0 3 * * 0 docker exec vantage-postgres psql -U vantage -d vantage_db -c "VACUUM ANALYZE;"
```

---

## Maintenance Procedures

### Daily Maintenance

**1. Monitor Table Sizes:**

```bash
docker exec vantage-postgres psql -U vantage -d vantage_db -c "
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size('public.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size('public.'||tablename) DESC;
"
```

**2. Check for Unresolved Alerts:**

```bash
docker exec vantage-postgres psql -U vantage -d vantage_db -c "
SELECT severity, COUNT(*) 
FROM alerts 
WHERE resolved_at IS NULL 
GROUP BY severity;
"
```

### Weekly Maintenance

**1. Create Next Month's Partition (on 25th):**

```bash
docker exec vantage-postgres psql -U vantage -d vantage_db -c "SELECT create_emotions_partition();"
```

**2. VACUUM ANALYZE:**

```bash
docker exec vantage-postgres psql -U vantage -d vantage_db -c "VACUUM ANALYZE;"
```

**3. Check Index Health:**

```bash
docker exec vantage-postgres psql -U vantage -d vantage_db -c "
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as scans,
    pg_size_pretty(pg_relation_size(indexrelid)) as size
FROM pg_stat_user_indexes
WHERE schemaname = 'public' AND idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;
"
```

### Monthly Maintenance

**1. Archive Old Partitions (>90 days):**

```bash
# Dump old partition
docker exec vantage-postgres pg_dump -U vantage -t emotions_2025_01 vantage_db > emotions_2025_01.sql

# Compress backup
gzip emotions_2025_01.sql

# Drop partition
docker exec vantage-postgres psql -U vantage -d vantage_db -c "DROP TABLE IF EXISTS emotions_2025_01 CASCADE;"
```

**2. Clean Old Sentiment Stats (>1 year):**

```bash
docker exec vantage-postgres psql -U vantage -d vantage_db -c "
DELETE FROM sentiment_stats WHERE timestamp < NOW() - INTERVAL '1 year';
"
```

**3. Clean Resolved Alerts (>6 months):**

```bash
docker exec vantage-postgres psql -U vantage -d vantage_db -c "
DELETE FROM alerts WHERE resolved_at < NOW() - INTERVAL '6 months';
"
```

### Automated Maintenance Script

Create `/scripts/db-maintenance.sh`:

```bash
#!/bin/bash
set -e

CONTAINER="vantage-postgres"
USER="vantage"
DB="vantage_db"

echo "=== Database Maintenance: $(date) ==="

# 1. Table sizes
echo "--- Table Sizes ---"
docker exec $CONTAINER psql -U $USER -d $DB -c "
SELECT tablename, pg_size_pretty(pg_total_relation_size('public.'||tablename)) AS size
FROM pg_tables WHERE schemaname = 'public'
ORDER BY pg_total_relation_size('public.'||tablename) DESC;
"

# 2. Partition info
echo "--- Emotion Partitions ---"
docker exec $CONTAINER psql -U $USER -d $DB -c "
SELECT 
    child.relname AS partition,
    pg_size_pretty(pg_relation_size(child.oid)) as size
FROM pg_inherits
JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
JOIN pg_class child ON pg_inherits.inhrelid = child.oid
WHERE parent.relname = 'emotions'
ORDER BY child.relname DESC;
"

# 3. VACUUM ANALYZE
echo "--- Running VACUUM ANALYZE ---"
docker exec $CONTAINER psql -U $USER -d $DB -c "VACUUM ANALYZE;"

# 4. Create next partition (if 25th or later)
DAY=$(date +%d)
if [ "$DAY" -ge 25 ]; then
    echo "--- Creating next month's partition ---"
    docker exec $CONTAINER psql -U $USER -d $DB -c "SELECT create_emotions_partition();"
fi

echo "=== Maintenance Complete ==="
```

**Make executable and schedule:**

```bash
chmod +x scripts/db-maintenance.sh

# Add to cron (weekly on Sunday at 3 AM)
0 3 * * 0 /home/ahmedashour/Desktop/VantageNet/scripts/db-maintenance.sh >> /var/log/vantage-db-maintenance.log 2>&1
```

---

## Backup and Recovery

### Backup Strategies

**1. Full Database Backup:**

```bash
# Dump entire database
docker exec vantage-postgres pg_dump -U vantage vantage_db > backup_$(date +%Y%m%d).sql

# Compress
gzip backup_$(date +%Y%m%d).sql

# Expected size: ~1-5GB (depends on data volume)
```

**2. Schema-Only Backup:**

```bash
docker exec vantage-postgres pg_dump -U vantage --schema-only vantage_db > schema_$(date +%Y%m%d).sql
```

**3. Specific Table Backup:**

```bash
# Backup emotions partition
docker exec vantage-postgres pg_dump -U vantage -t emotions_2025_12 vantage_db > emotions_2025_12.sql

# Backup cameras and rules
docker exec vantage-postgres pg_dump -U vantage -t cameras -t rules vantage_db > config_backup.sql
```

**4. Continuous Archiving (WAL):**

Enable in `postgresql.conf` for point-in-time recovery:

```ini
wal_level = replica
archive_mode = on
archive_command = 'cp %p /backups/wal/%f'
```

### Automated Backup Script

Create `/scripts/db-backup.sh`:

```bash
#!/bin/bash
set -e

BACKUP_DIR="/backups/postgres"
RETENTION_DAYS=30

mkdir -p $BACKUP_DIR

# Full database backup
BACKUP_FILE="$BACKUP_DIR/vantage_db_$(date +%Y%m%d_%H%M%S).sql.gz"
docker exec vantage-postgres pg_dump -U vantage vantage_db | gzip > $BACKUP_FILE

echo "Backup created: $BACKUP_FILE"

# Delete backups older than retention period
find $BACKUP_DIR -name "vantage_db_*.sql.gz" -mtime +$RETENTION_DAYS -delete

echo "Old backups cleaned (>$RETENTION_DAYS days)"
```

**Schedule daily backups:**

```bash
chmod +x scripts/db-backup.sh

# Daily at 1 AM
0 1 * * * /home/ahmedashour/Desktop/VantageNet/scripts/db-backup.sh >> /var/log/vantage-db-backup.log 2>&1
```

### Restore Procedures

**1. Restore Full Database:**

```bash
# Stop services
docker compose stop api-gateway emotion-detection sentiment-analysis video-ingestion

# Drop and recreate database
docker exec vantage-postgres psql -U vantage -c "DROP DATABASE vantage_db;"
docker exec vantage-postgres psql -U vantage -c "CREATE DATABASE vantage_db;"

# Restore from backup
gunzip -c backup_20251215.sql.gz | docker exec -i vantage-postgres psql -U vantage vantage_db

# Restart services
docker compose start api-gateway emotion-detection sentiment-analysis video-ingestion
```

**2. Restore Specific Table:**

```bash
# Restore cameras table
docker exec -i vantage-postgres psql -U vantage vantage_db < cameras_backup.sql
```

**3. Point-in-Time Recovery (requires WAL archiving):**

```bash
# Stop database
docker compose stop postgres

# Restore base backup
docker exec -i vantage-postgres psql -U vantage vantage_db < base_backup.sql

# Create recovery.conf
cat > recovery.conf << EOF
restore_command = 'cp /backups/wal/%f %p'
recovery_target_time = '2025-12-15 14:30:00'
EOF

# Copy recovery.conf to data directory
docker cp recovery.conf vantage-postgres:/var/lib/postgresql/data/

# Start database (will enter recovery mode)
docker compose start postgres
```

---

## Monitoring

### Database Health Checks

**1. Connection Count:**

```sql
SELECT 
    COUNT(*) as total_connections,
    COUNT(*) FILTER (WHERE state = 'active') as active,
    COUNT(*) FILTER (WHERE state = 'idle') as idle
FROM pg_stat_activity
WHERE datname = 'vantage_db';
```

**2. Table Sizes:**

```sql
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size('public.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size('public.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size('public.'||tablename) - pg_relation_size('public.'||tablename)) AS indexes_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size('public.'||tablename) DESC;
```

**3. Long-Running Queries:**

```sql
SELECT 
    pid,
    now() - query_start AS duration,
    state,
    query
FROM pg_stat_activity
WHERE state != 'idle' 
  AND query_start < now() - INTERVAL '1 minute'
ORDER BY duration DESC;
```

**4. Cache Hit Ratio:**

```sql
SELECT 
    'cache hit rate' AS metric,
    ROUND(sum(blks_hit) * 100.0 / (sum(blks_hit) + sum(blks_read)), 2) AS percentage
FROM pg_stat_database
WHERE datname = 'vantage_db';
```

**Target:** > 99% (indicates good memory allocation)

**5. Index Hit Ratio:**

```sql
SELECT 
    'index hit rate' AS metric,
    ROUND((sum(idx_blks_hit) * 100.0 / (sum(idx_blks_hit) + sum(idx_blks_read))), 2) AS percentage
FROM pg_statio_user_indexes;
```

**Target:** > 95%

### Monitoring Script

Create `/scripts/db-monitor.sh`:

```bash
#!/bin/bash

CONTAINER="vantage-postgres"
USER="vantage"
DB="vantage_db"

echo "=== VantageNet Database Health: $(date) ==="

# Connections
echo -e "\n--- Connections ---"
docker exec $CONTAINER psql -U $USER -d $DB -c "
SELECT 
    COUNT(*) as total,
    COUNT(*) FILTER (WHERE state = 'active') as active,
    COUNT(*) FILTER (WHERE state = 'idle') as idle
FROM pg_stat_activity WHERE datname = '$DB';
"

# Cache hit rate
echo -e "\n--- Cache Hit Rate ---"
docker exec $CONTAINER psql -U $USER -d $DB -c "
SELECT ROUND(sum(blks_hit) * 100.0 / (sum(blks_hit) + sum(blks_read)), 2) || '%' AS cache_hit_rate
FROM pg_stat_database WHERE datname = '$DB';
"

# Table sizes
echo -e "\n--- Top 5 Tables by Size ---"
docker exec $CONTAINER psql -U $USER -d $DB -c "
SELECT tablename, pg_size_pretty(pg_total_relation_size('public.'||tablename)) AS size
FROM pg_tables WHERE schemaname = 'public'
ORDER BY pg_total_relation_size('public.'||tablename) DESC LIMIT 5;
"

# Recent emotions count
echo -e "\n--- Recent Activity (Last Hour) ---"
docker exec $CONTAINER psql -U $USER -d $DB -c "
SELECT 
    'Emotions' as table,
    COUNT(*) as count
FROM emotions WHERE timestamp > NOW() - INTERVAL '1 hour'
UNION ALL
SELECT 
    'Sentiment Stats' as table,
    COUNT(*) as count
FROM sentiment_stats WHERE timestamp > NOW() - INTERVAL '1 hour'
UNION ALL
SELECT 
    'Alerts' as table,
    COUNT(*) as count
FROM alerts WHERE triggered_at > NOW() - INTERVAL '1 hour';
"

# Unresolved alerts
echo -e "\n--- Unresolved Alerts ---"
docker exec $CONTAINER psql -U $USER -d $DB -c "
SELECT severity, COUNT(*) as count
FROM alerts WHERE resolved_at IS NULL
GROUP BY severity ORDER BY 
CASE severity 
    WHEN 'critical' THEN 1 
    WHEN 'high' THEN 2 
    WHEN 'medium' THEN 3 
    WHEN 'low' THEN 4 
END;
"

echo -e "\n=== Health Check Complete ===\n"
```

**Make executable:**

```bash
chmod +x scripts/db-monitor.sh

# Run on demand
./scripts/db-monitor.sh

# Or schedule (every 15 minutes)
*/15 * * * * /home/ahmedashour/Desktop/VantageNet/scripts/db-monitor.sh >> /var/log/vantage-db-monitor.log 2>&1
```

### Alerts and Thresholds

**Recommended Alert Thresholds:**

- **Connections:** > 80 total (max 100)
- **Cache Hit Rate:** < 95%
- **Disk Usage:** > 80% full
- **Partition Age:** Oldest partition > 90 days
- **Table Bloat:** pg_stat_user_tables.n_dead_tup > 100,000
- **Long Queries:** Queries running > 5 minutes

---

## Additional Resources

### Documentation

- **Detailed Schema:** [database-schema.md](./database-schema.md)
- **Architecture:** [ARCHITECTURE.md](./ARCHITECTURE.md)
- **Setup Guide:** [SETUP.md](./SETUP.md)
- **API Documentation:** [API.md](./API.md)

### PostgreSQL Resources

- **Official Docs:** https://www.postgresql.org/docs/15/
- **Partitioning:** https://www.postgresql.org/docs/15/ddl-partitioning.html
- **Performance Tuning:** https://wiki.postgresql.org/wiki/Performance_Optimization
- **pg_stat_statements:** https://www.postgresql.org/docs/15/pgstatstatements.html

### Tools

- **pgAdmin:** Web-based database management (http://localhost:5050 if installed)
- **psql:** Command-line interface (included in Docker container)
- **pg_dump/pg_restore:** Backup and restore utilities

---

## Troubleshooting

### Connection Issues

**Problem:** `psql: error: connection to server failed`

```bash
# Check if container is running
docker ps | grep vantage-postgres

# Check logs
docker logs vantage-postgres

# Restart container
docker compose restart postgres
```

### Slow Queries

**Problem:** Queries taking too long

```sql
-- 1. Check for missing ANALYZE
ANALYZE emotions;

-- 2. Check if indexes are being used
EXPLAIN ANALYZE SELECT * FROM emotions WHERE camera_id = '...' AND timestamp > NOW() - INTERVAL '1 hour';

-- 3. Check for table bloat
SELECT 
    schemaname,
    tablename,
    n_dead_tup,
    n_live_tup,
    ROUND(n_dead_tup * 100.0 / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_pct
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
ORDER BY n_dead_tup DESC;

-- 4. Run VACUUM if high dead tuple count
VACUUM ANALYZE emotions;
```

### Partition Errors

**Problem:** `no partition of relation "emotions" found for row`

```bash
# Create missing partition
docker exec vantage-postgres psql -U vantage -d vantage_db -c "SELECT create_emotions_partition();"
```

### Disk Space Issues

**Problem:** Database running out of disk space

```bash
# Check disk usage
docker exec vantage-postgres df -h

# Check database size
docker exec vantage-postgres psql -U vantage -d vantage_db -c "
SELECT pg_size_pretty(pg_database_size('vantage_db')) AS database_size;
"

# Drop old partitions
docker exec vantage-postgres psql -U vantage -d vantage_db -c "DROP TABLE IF EXISTS emotions_2025_01 CASCADE;"

# Clean old alerts
docker exec vantage-postgres psql -U vantage -d vantage_db -c "
DELETE FROM alerts WHERE resolved_at < NOW() - INTERVAL '6 months';
"
```

### Lock Contention

**Problem:** Queries waiting for locks

```sql
-- Check for blocking queries
SELECT 
    blocked_locks.pid AS blocked_pid,
    blocking_locks.pid AS blocking_pid,
    blocked_activity.query AS blocked_statement,
    blocking_activity.query AS blocking_statement
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks 
    ON blocking_locks.locktype = blocked_locks.locktype
    AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
    AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
    AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;

-- Kill blocking query (use with caution!)
SELECT pg_terminate_backend(12345);  -- Replace with actual PID
```

---

**For additional help, refer to [SETUP.md](./SETUP.md) or contact the development team.**
