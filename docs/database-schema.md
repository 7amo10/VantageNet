# Database Schema Documentation

## VantageNet Database Schema v2.0

### Overview
The VantageNet database is designed for high-volume emotion analytics with optimized write performance and efficient querying. The schema supports real-time emotion detection, sentiment analysis, rule-based alerting, and time-series analytics.

### Design Principles
1. **Write Optimization**: Table partitioning and batch inserts for emotions table
2. **Query Efficiency**: Strategic indexes on timestamp, camera_id, and emotion fields
3. **Data Integrity**: Foreign key constraints and CHECK constraints
4. **Scalability**: Partitioned emotions table by date
5. **Auditability**: Timestamps on all tables with automatic update triggers

---

## Entity Relationship Diagram

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

---

## Table Definitions

### 1. cameras

Stores camera configuration and metadata.

| Column      | Type            | Constraints       | Description                    |
|-------------|-----------------|-------------------|--------------------------------|
| id          | UUID            | PRIMARY KEY       | Unique camera identifier       |
| name        | VARCHAR(200)    | NOT NULL, UNIQUE  | Camera display name            |
| rtsp_url    | VARCHAR(500)    | NULL              | RTSP stream URL                |
| location    | VARCHAR(500)    | NULL              | Physical location              |
| active      | BOOLEAN         | DEFAULT TRUE      | Camera active status           |
| created_at  | TIMESTAMPTZ     | DEFAULT NOW()     | Record creation timestamp      |
| updated_at  | TIMESTAMPTZ     | DEFAULT NOW()     | Last update timestamp          |

**Indexes:**
- `idx_cameras_active` - Active cameras (partial index)
- `idx_cameras_created_at` - Creation date queries

**Relationships:**
- One camera → Many emotions
- One camera → Many sentiment_stats
- One camera → Many alerts

---

### 2. emotions (Partitioned Table)

Stores individual emotion detection events from video frames. **Partitioned by timestamp** for optimal write performance and query efficiency.

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

**Partitioning Strategy:**
- Monthly partitions: `emotions_YYYY_MM`
- Automatic partition creation function available
- Current partitions: 2025-12, 2026-01

**Indexes (on all partitions):**
- `idx_emotions_timestamp` - Timestamp DESC for latest events
- `idx_emotions_camera_id` - Camera + timestamp for filtering
- `idx_emotions_emotion` - Emotion type + timestamp
- `idx_emotions_frame_id` - Frame lookups
- `idx_emotions_face_id` - Face tracking (partial, where NOT NULL)

**Foreign Keys:**
- `camera_id` → `cameras(id)` ON DELETE CASCADE

**Supported Emotions:**
- happy, sad, angry, neutral, surprised, fear, disgust

---

### 3. rules

Stores sentiment-based alert rules configuration.

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
- `alert` - Create alert record
- `log` - Log event
- `webhook` - Send webhook notification
- `email` - Send email notification

**Condition JSON Format:**
```json
{
  "metric": "sentiment_score",
  "operator": "<",
  "threshold": -0.5
}
```

**Indexes:**
- `idx_rules_enabled` - Active rules only (partial index)
- `idx_rules_type` - Rule type filtering
- `idx_rules_created_at` - Creation date queries

**Relationships:**
- One rule → Many alerts

---

### 4. alerts

Stores triggered alerts from rules with resolution tracking.

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
- `low` - Informational
- `medium` - Warning
- `high` - Important
- `critical` - Urgent action required

**Indexes:**
- `idx_alerts_triggered_at` - Trigger timestamp DESC
- `idx_alerts_rule_id` - Rule + timestamp filtering
- `idx_alerts_severity` - Unresolved alerts by severity
- `idx_alerts_camera_id` - Camera-specific alerts
- `idx_alerts_unresolved` - Active/unresolved alerts (partial index)

**Foreign Keys:**
- `rule_id` → `rules(id)` ON DELETE CASCADE
- `camera_id` → `cameras(id)` ON DELETE SET NULL

---

### 5. sentiment_stats

Stores aggregated sentiment statistics per camera over time windows.

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

**Indexes:**
- `idx_sentiment_stats_timestamp` - Timestamp DESC
- `idx_sentiment_stats_camera_id` - Camera + timestamp filtering
- `idx_sentiment_stats_time_window` - Window range queries
- `idx_sentiment_stats_dominant_emotion` - Emotion filtering

**Foreign Keys:**
- `camera_id` → `cameras(id)` ON DELETE CASCADE

---

## Database Functions

### create_emotions_partition()
Automatically creates a new partition for the emotions table for the next month.

```sql
SELECT create_emotions_partition();
```

### update_updated_at_column()
Trigger function that automatically updates the `updated_at` column on table updates.

---

## Performance Optimization

### Partitioning Strategy
The `emotions` table uses **range partitioning by timestamp** with monthly partitions:
- Improves write performance for high-volume inserts
- Enables efficient data archival/deletion
- Reduces index size per partition
- Optimizes time-range queries

### Index Strategy
1. **Composite Indexes**: `(camera_id, timestamp)` for common filter patterns
2. **Partial Indexes**: Active/enabled records only
3. **DESC Ordering**: Recent records first (most common query pattern)
4. **JSONB Indexing**: Can be added for condition_json/metadata if needed

### Batch Insert Optimization
- Use `COPY` or `INSERT ... VALUES (...)` with multiple rows
- Disable indexes temporarily for bulk loads if needed
- Consider `UNLOGGED` tables for transient data

---

## Migration Strategy

### Using Alembic (Python)

1. Install Alembic:
```bash
pip install alembic psycopg2-binary
```

2. Initialize Alembic:
```bash
alembic init migrations
```

3. Create migration:
```bash
alembic revision --autogenerate -m "Initial schema"
```

4. Apply migration:
```bash
alembic upgrade head
```

### Direct SQL Initialization

The schema is automatically initialized when PostgreSQL container starts:
```bash
docker-compose up -d postgres
```

The `init-scripts/01-init.sql` file is executed on first database creation.

---

## Data Retention Policy

### Recommended Retention Periods
- **emotions**: 90 days (archive older partitions)
- **sentiment_stats**: 1 year
- **alerts**: 6 months (resolved), 1 year (unresolved)
- **cameras**: Permanent
- **rules**: Permanent

### Archival Process
```sql
-- Drop old emotion partitions
DROP TABLE IF EXISTS emotions_2025_01;

-- Archive sentiment_stats older than 1 year
DELETE FROM sentiment_stats WHERE timestamp < NOW() - INTERVAL '1 year';

-- Archive resolved alerts older than 6 months
DELETE FROM alerts WHERE resolved_at < NOW() - INTERVAL '6 months';
```

---

## Query Examples

### Recent Emotions by Camera
```sql
SELECT e.*, c.name as camera_name
FROM emotions e
JOIN cameras c ON e.camera_id = c.id
WHERE c.id = 'camera-uuid'
  AND e.timestamp > NOW() - INTERVAL '1 hour'
ORDER BY e.timestamp DESC
LIMIT 100;
```

### Average Sentiment by Hour
```sql
SELECT 
    DATE_TRUNC('hour', timestamp) as hour,
    AVG(sentiment_score) as avg_sentiment,
    COUNT(*) as face_count
FROM sentiment_stats
WHERE camera_id = 'camera-uuid'
  AND timestamp > NOW() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', timestamp)
ORDER BY hour DESC;
```

### Active Unresolved Alerts
```sql
SELECT a.*, r.name as rule_name, c.name as camera_name
FROM alerts a
JOIN rules r ON a.rule_id = r.id
LEFT JOIN cameras c ON a.camera_id = c.id
WHERE a.resolved_at IS NULL
ORDER BY a.severity DESC, a.triggered_at DESC;
```

### Emotion Distribution by Camera
```sql
SELECT 
    c.name as camera,
    e.emotion,
    COUNT(*) as count,
    AVG(e.confidence) as avg_confidence
FROM emotions e
JOIN cameras c ON e.camera_id = c.id
WHERE e.timestamp > NOW() - INTERVAL '1 hour'
GROUP BY c.name, e.emotion
ORDER BY c.name, count DESC;
```

---

## Backup and Recovery

### Backup Commands
```bash
# Full database backup
docker exec vantage-postgres pg_dump -U vantage vantage_db > backup.sql

# Schema only
docker exec vantage-postgres pg_dump -U vantage --schema-only vantage_db > schema.sql

# Specific table
docker exec vantage-postgres pg_dump -U vantage -t emotions vantage_db > emotions.sql
```

### Restore Commands
```bash
# Restore full database
docker exec -i vantage-postgres psql -U vantage vantage_db < backup.sql

# Restore schema
docker exec -i vantage-postgres psql -U vantage vantage_db < schema.sql
```

---

## Monitoring Queries

### Table Sizes
```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Index Usage
```sql
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan as index_scans,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC;
```

### Partition Information
```sql
SELECT 
    parent.relname AS parent_table,
    child.relname AS partition_name,
    pg_get_expr(child.relpartbound, child.oid) AS partition_expression
FROM pg_inherits
JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
JOIN pg_class child ON pg_inherits.inhrelid = child.oid
WHERE parent.relname = 'emotions';
```

---

## Version History

| Version | Date       | Changes                                          |
|---------|------------|--------------------------------------------------|
| 2.0     | 2025-12-07 | VANTA-7: Complete schema redesign with partitioning, enhanced indexes, foreign keys |
| 1.0     | 2025-12-06 | Initial schema with basic tables                 |

---

## Contact & Support

For questions or issues with the database schema:
- Check the GitHub repository: https://github.com/7amo10/VantageNet
- Review VANTA-7 issue documentation
- Contact the development team
