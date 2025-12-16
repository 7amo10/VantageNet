# Alert Database Schema & Queries (VANTA-22)

## Overview
This document describes the alert storage and analytics system for VantageNet. The system provides:
- Enhanced alert storage with rich metadata
- Fast analytical queries for dashboard
- Automatic 30-day retention policy
- Hourly aggregation for performance

## Database Tables

### `alerts` Table (Enhanced)

Stores individual alert events triggered by rules engine.

**Schema:**
```sql
CREATE TABLE alerts (
    id UUID PRIMARY KEY,
    rule_id UUID NOT NULL,
    camera_id UUID,
    alert_type VARCHAR(50) NOT NULL DEFAULT 'rule_trigger',
    emotion VARCHAR(50),
    message TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('info', 'warning', 'critical')),
    triggered_at TIMESTAMPTZ NOT NULL,
    resolved_at TIMESTAMPTZ,
    action_taken VARCHAR(200),
    metadata_json JSONB,
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by VARCHAR(100),
    acknowledged_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Indexes:**
- `(camera_id, triggered_at)` - For camera-specific queries
- `(severity, triggered_at)` - For severity filtering
- `(emotion, triggered_at)` - For emotion-based analytics
- `(triggered_at DESC)` - For time-ordered queries
- `(rule_id, triggered_at)` - For rule performance tracking

**Retention:** Alerts older than 30 days are automatically deleted

**Fields:**
- `id`: UUID primary key
- `rule_id`: Reference to rule that triggered alert
- `camera_id`: Camera where alert was triggered (nullable)
- `alert_type`: Type of alert (default: 'rule_trigger')
- `emotion`: Dominant emotion that triggered alert
- `message`: Human-readable alert message
- `severity`: Alert severity level (info, warning, critical)
- `triggered_at`: When alert was triggered
- `resolved_at`: When alert was resolved (nullable)
- `action_taken`: Actions performed in response (nullable)
- `metadata_json`: Additional alert data as JSON
- `acknowledged`: Whether alert has been acknowledged
- `acknowledged_by`: User who acknowledged alert
- `acknowledged_at`: When alert was acknowledged
- `created_at`: Record creation timestamp

### `alert_metrics` Table (New)

Stores hourly aggregated alert metrics for fast analytics queries.

**Schema:**
```sql
CREATE TABLE alert_metrics (
    id UUID PRIMARY KEY,
    hour TIMESTAMPTZ NOT NULL,
    camera_id UUID NOT NULL,
    alert_count INTEGER DEFAULT 0,
    severity_breakdown JSONB NOT NULL,
    top_emotion VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT alert_metrics_unique UNIQUE (hour, camera_id)
);
```

**Indexes:**
- `(hour DESC)` - For time-series queries
- `(camera_id, hour DESC)` - For camera-specific time-series

**Fields:**
- `id`: UUID primary key
- `hour`: Hour timestamp (truncated to hour)
- `camera_id`: Camera for these metrics
- `alert_count`: Total alerts in this hour
- `severity_breakdown`: JSON with counts by severity
  ```json
  {"info": 5, "warning": 2, "critical": 1}
  ```
- `top_emotion`: Most common emotion in this hour
- `created_at`: Record creation timestamp

## Query Methods

### `get_alerts(camera_id, start_time, end_time, severity, limit)`

Get alerts within time range with optional filters.

**Parameters:**
- `camera_id` (Optional[str]): Filter by camera ID
- `start_time` (Optional[datetime]): Start of time range
- `end_time` (Optional[datetime]): End of time range
- `severity` (Optional[str]): Filter by severity ('info', 'warning', 'critical')
- `limit` (int): Maximum number of results (default: 100)

**Returns:** List of alert dictionaries

**Example:**
```python
# Get last 24 hours of critical alerts for camera-1
alerts = await db.get_alerts(
    camera_id="camera-1",
    start_time=datetime.utcnow() - timedelta(hours=24),
    severity="critical"
)
```

**Performance:** < 100ms for 30 days of data (with indexes)

### `get_severity_distribution(camera_id, period_hours)`

Get alert count breakdown by severity level.

**Parameters:**
- `camera_id` (Optional[str]): Filter by camera ID
- `period_hours` (int): Time period in hours (default: 24)

**Returns:** Dictionary with severity counts
```python
{
    "info": 150,
    "warning": 45,
    "critical": 12,
    "total": 207
}
```

**Example:**
```python
# Get severity distribution for last week
dist = await db.get_severity_distribution(period_hours=168)  # 7 days
```

**Performance:** < 100ms with severity index

### `get_top_rules(camera_id, limit, period_hours)`

Get most frequently triggered rules.

**Parameters:**
- `camera_id` (Optional[str]): Filter by camera ID
- `limit` (int): Maximum number of rules (default: 5)
- `period_hours` (int): Time period in hours (default: 24)

**Returns:** List of rules with trigger counts
```python
[
    {"rule_id": "uuid-1", "trigger_count": 45},
    {"rule_id": "uuid-2", "trigger_count": 32},
    ...
]
```

**Example:**
```python
# Get top 5 rules for last 24 hours
top_rules = await db.get_top_rules(limit=5, period_hours=24)
```

**Performance:** < 100ms with rule_id index

### `get_emotion_triggers(camera_id, period_hours)`

Get emotion-to-alert correlation data.

**Parameters:**
- `camera_id` (Optional[str]): Filter by camera ID
- `period_hours` (int): Time period in hours (default: 24)

**Returns:** Dictionary mapping emotions to alert counts
```python
{
    "angry": 67,
    "sad": 42,
    "happy": 12
}
```

**Example:**
```python
# Get emotion triggers for last 24 hours
emotions = await db.get_emotion_triggers(period_hours=24)
```

**Performance:** < 100ms with emotion index

### `cleanup_old_alerts(days)`

Delete alerts older than specified retention period.

**Parameters:**
- `days` (int): Number of days to retain (default: 30)

**Returns:** Number of deleted alerts (int)

**Example:**
```python
# Delete alerts older than 30 days
deleted_count = await db.cleanup_old_alerts(days=30)
```

**Usage:** Should be called periodically (e.g., daily cron job)

**Performance:** Uses PostgreSQL function for efficient bulk delete

### `aggregate_alert_metrics(hour)`

Aggregate alerts for a specific hour into metrics table.

**Parameters:**
- `hour` (datetime): Hour to aggregate (will be truncated to hour)

**Returns:** bool (True if successful)

**Example:**
```python
# Aggregate alerts for last hour
last_hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
success = await db.aggregate_alert_metrics(last_hour)
```

**Usage:** Should be called hourly (e.g., via scheduler)

**Performance:** Uses PostgreSQL function with upsert logic

## Stored Functions

### `cleanup_old_alerts()`

PostgreSQL function that deletes alerts older than 30 days.

**SQL:**
```sql
SELECT cleanup_old_alerts();
```

**Returns:** INTEGER (count of deleted records)

### `aggregate_alert_metrics(target_hour TIMESTAMPTZ)`

PostgreSQL function that aggregates alerts into hourly metrics.

**SQL:**
```sql
SELECT aggregate_alert_metrics('2025-12-16 14:00:00'::timestamptz);
```

**Returns:** VOID (inserts/updates alert_metrics table)

**Logic:**
- Groups alerts by hour and camera
- Counts total alerts
- Breaks down by severity
- Finds most common emotion (MODE)
- Upserts into alert_metrics table

## Usage Examples

### Dashboard Analytics

```python
from datetime import datetime, timedelta
from app.database import DatabaseManager

db = DatabaseManager()
await db.connect()

# Get current alert status
severity_dist = await db.get_severity_distribution(period_hours=24)
print(f"Critical alerts in last 24h: {severity_dist['critical']}")

# Find problematic cameras
for camera_id in ["camera-1", "camera-2", "camera-3"]:
    alerts = await db.get_alerts(
        camera_id=camera_id,
        severity="critical",
        start_time=datetime.utcnow() - timedelta(hours=24)
    )
    print(f"{camera_id}: {len(alerts)} critical alerts")

# Analyze emotion patterns
emotions = await db.get_emotion_triggers(period_hours=168)  # Last week
print(f"Most triggering emotion: {max(emotions, key=emotions.get)}")

# Find frequently triggering rules
top_rules = await db.get_top_rules(limit=5, period_hours=24)
for rule in top_rules:
    print(f"Rule {rule['rule_id']}: {rule['trigger_count']} triggers")
```

### Scheduled Maintenance

```python
import schedule

async def hourly_aggregation():
    """Run every hour to aggregate metrics."""
    last_hour = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    await db.aggregate_alert_metrics(last_hour)

async def daily_cleanup():
    """Run daily to cleanup old alerts."""
    deleted = await db.cleanup_old_alerts(days=30)
    print(f"Deleted {deleted} old alerts")

# Schedule tasks
schedule.every().hour.at(":05").do(hourly_aggregation)  # 5 minutes past hour
schedule.every().day.at("02:00").do(daily_cleanup)  # 2 AM daily
```

### Real-time Monitoring

```python
async def monitor_critical_alerts():
    """Check for new critical alerts every minute."""
    while True:
        one_minute_ago = datetime.utcnow() - timedelta(minutes=1)
        
        alerts = await db.get_alerts(
            severity="critical",
            start_time=one_minute_ago,
            limit=10
        )
        
        if alerts:
            for alert in alerts:
                print(f"⚠️  CRITICAL: {alert['message']}")
                print(f"   Camera: {alert['camera_id']}")
                print(f"   Emotion: {alert['emotion']}")
        
        await asyncio.sleep(60)
```

## Performance Considerations

### Index Usage
All queries are optimized to use indexes:
- Time-range queries use `triggered_at` indexes
- Camera filters use `camera_id, triggered_at` composite index
- Severity filters use `severity, triggered_at` composite index
- Emotion analytics use `emotion, triggered_at` index

### Query Optimization
- Severity distribution uses COUNT FILTER for efficiency
- Top rules uses GROUP BY with ORDER BY count
- Emotion triggers excludes NULL emotions
- All queries have LIMIT to prevent large result sets

### Retention Policy
- 30-day retention keeps table size manageable
- Automatic cleanup via PostgreSQL function
- Historical data preserved in alert_metrics table

### Aggregation Strategy
- Hourly pre-aggregation for fast dashboard queries
- alert_metrics table provides O(hours) instead of O(alerts) complexity
- Upsert logic handles re-aggregation gracefully

## Testing

Comprehensive test suite in `tests/test_alert_queries.py`:
- 100+ test alerts for performance validation
- All query methods tested with various filters
- Retention cleanup verification
- Performance benchmarks (< 100ms requirement)
- Edge cases and error handling

**Run tests:**
```bash
cd services/sentiment-analysis
pytest tests/test_alert_queries.py -v
```

## Migration Notes

### From Previous Schema
The alerts table has been enhanced with new fields:
- Added: `alert_type`, `emotion`, `metadata_json`, `action_taken`
- Changed: `severity` values now 'info'/'warning'/'critical' (was 'low'/'medium'/'high'/'critical')
- Changed: `id` is now UUID string (was autoincrement integer)
- Removed: `trigger_data` (replaced by `metadata_json`)

### Backward Compatibility
Existing code using `save_alert()` continues to work with enhanced fields.

## Future Enhancements

Potential improvements for future sprints:
- Partition alerts table by month for better performance
- Add alert_trends table for pattern detection
- Implement alert correlation analysis
- Add machine learning for anomaly detection
- Support custom aggregation periods (15min, 6h, etc.)
