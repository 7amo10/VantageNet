-- VantageNet Database Initialization Script
-- VANTA-7: Enhanced Database Schema for Emotion Analytics Platform
-- Optimized for batch inserts and time-series analytics
-- Version: 2.0 (Sprint 1)

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- ============================================
-- CAMERAS TABLE
-- Stores camera configuration and metadata
-- ============================================
CREATE TABLE IF NOT EXISTS cameras (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    rtsp_url VARCHAR(500),
    location VARCHAR(500),
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT cameras_name_unique UNIQUE (name)
);

CREATE INDEX idx_cameras_active ON cameras(active) WHERE active = TRUE;
CREATE INDEX idx_cameras_created_at ON cameras(created_at);

-- ============================================
-- EMOTIONS TABLE (Partitioned by Date)
-- Stores individual emotion detection events
-- Optimized for high-volume batch inserts
-- ============================================
CREATE TABLE IF NOT EXISTS emotions (
    id UUID DEFAULT uuid_generate_v4(),
    frame_id VARCHAR(100) NOT NULL,
    face_id VARCHAR(100),
    emotion VARCHAR(50) NOT NULL,
    confidence DECIMAL(5,4) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    camera_id UUID NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    bounding_box JSONB,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (id, timestamp)
) PARTITION BY RANGE (timestamp);

-- Create partitions for current and next months
CREATE TABLE IF NOT EXISTS emotions_2025_12 PARTITION OF emotions
    FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');

CREATE TABLE IF NOT EXISTS emotions_2026_01 PARTITION OF emotions
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

-- Indexes on emotions table (applied to all partitions)
CREATE INDEX idx_emotions_timestamp ON emotions(timestamp DESC);
CREATE INDEX idx_emotions_camera_id ON emotions(camera_id, timestamp DESC);
CREATE INDEX idx_emotions_emotion ON emotions(emotion, timestamp DESC);
CREATE INDEX idx_emotions_frame_id ON emotions(frame_id);
CREATE INDEX idx_emotions_face_id ON emotions(face_id) WHERE face_id IS NOT NULL;

-- Foreign key constraint
ALTER TABLE emotions ADD CONSTRAINT fk_emotions_camera
    FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE CASCADE;

-- ============================================
-- RULES TABLE
-- Stores sentiment-based alert rules
-- ============================================
CREATE TABLE IF NOT EXISTS rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    type VARCHAR(50) NOT NULL DEFAULT 'sentiment',
    condition_json JSONB NOT NULL,
    action VARCHAR(100) NOT NULL CHECK (action IN ('alert', 'log', 'webhook', 'email')),
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT rules_name_unique UNIQUE (name)
);

CREATE INDEX idx_rules_enabled ON rules(enabled) WHERE enabled = TRUE;
CREATE INDEX idx_rules_type ON rules(type);
CREATE INDEX idx_rules_created_at ON rules(created_at DESC);

-- ============================================
-- ALERTS TABLE (VANTA-22 Enhanced)
-- Stores triggered alerts from rules
-- Auto-deletes records older than 30 days
-- ============================================
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_id UUID NOT NULL,
    camera_id UUID,
    alert_type VARCHAR(50) NOT NULL DEFAULT 'rule_trigger',
    emotion VARCHAR(50),
    message TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('info', 'warning', 'critical')),
    triggered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    action_taken VARCHAR(200),
    metadata_json JSONB,
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by VARCHAR(100),
    acknowledged_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for VANTA-22 queries (camera_id, triggered_at), (severity, triggered_at)
CREATE INDEX idx_alerts_triggered_at ON alerts(triggered_at DESC);
CREATE INDEX idx_alerts_rule_id ON alerts(rule_id, triggered_at DESC);
CREATE INDEX idx_alerts_camera_triggered ON alerts(camera_id, triggered_at DESC) WHERE camera_id IS NOT NULL;
CREATE INDEX idx_alerts_severity_triggered ON alerts(severity, triggered_at DESC);
CREATE INDEX idx_alerts_emotion ON alerts(emotion, triggered_at DESC) WHERE emotion IS NOT NULL;
CREATE INDEX idx_alerts_unresolved ON alerts(triggered_at DESC) WHERE resolved_at IS NULL;

-- Foreign key constraints
ALTER TABLE alerts ADD CONSTRAINT fk_alerts_rule
    FOREIGN KEY (rule_id) REFERENCES rules(id) ON DELETE CASCADE;
    
ALTER TABLE alerts ADD CONSTRAINT fk_alerts_camera
    FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE SET NULL;

-- ============================================
-- ALERT_METRICS TABLE (VANTA-22 New)
-- Stores hourly aggregated alert metrics
-- For fast analytics queries
-- ============================================
CREATE TABLE IF NOT EXISTS alert_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hour TIMESTAMPTZ NOT NULL,
    camera_id UUID NOT NULL,
    alert_count INTEGER DEFAULT 0 CHECK (alert_count >= 0),
    severity_breakdown JSONB NOT NULL DEFAULT '{"info": 0, "warning": 0, "critical": 0}'::jsonb,
    top_emotion VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT alert_metrics_unique UNIQUE (hour, camera_id)
);

CREATE INDEX idx_alert_metrics_hour ON alert_metrics(hour DESC);
CREATE INDEX idx_alert_metrics_camera_hour ON alert_metrics(camera_id, hour DESC);

-- Foreign key constraint
ALTER TABLE alert_metrics ADD CONSTRAINT fk_alert_metrics_camera
    FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE CASCADE;

-- ============================================
-- SENTIMENT_STATS TABLE
-- Stores aggregated sentiment statistics per camera
-- ============================================
CREATE TABLE IF NOT EXISTS sentiment_stats (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    camera_id VARCHAR(100) NOT NULL,
    total_faces_observed INTEGER NOT NULL DEFAULT 0,
    emotion_distribution JSONB NOT NULL,
    dominant_emotion VARCHAR(50),
    mood_score FLOAT NOT NULL DEFAULT 0.0,
    trend VARCHAR(20),
    trend_magnitude FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sentiment_stats_timestamp ON sentiment_stats(timestamp DESC);
CREATE INDEX idx_sentiment_stats_camera_id ON sentiment_stats(camera_id, timestamp DESC);
CREATE INDEX idx_sentiment_stats_dominant_emotion ON sentiment_stats(dominant_emotion, timestamp DESC);

-- ============================================
-- UTILITY FUNCTIONS
-- ============================================

-- Function to create future partitions automatically
CREATE OR REPLACE FUNCTION create_emotions_partition()
RETURNS void AS $$
DECLARE
    partition_date DATE;
    partition_name TEXT;
    start_date TEXT;
    end_date TEXT;
BEGIN
    -- Create partition for next month
    partition_date := DATE_TRUNC('month', CURRENT_DATE + INTERVAL '1 month');
    partition_name := 'emotions_' || TO_CHAR(partition_date, 'YYYY_MM');
    start_date := TO_CHAR(partition_date, 'YYYY-MM-DD');
    end_date := TO_CHAR(partition_date + INTERVAL '1 month', 'YYYY-MM-DD');
    
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF emotions FOR VALUES FROM (%L) TO (%L)',
        partition_name, start_date, end_date
    );
END;
$$ LANGUAGE plpgsql;

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE TRIGGER update_cameras_updated_at
    BEFORE UPDATE ON cameras
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_rules_updated_at
    BEFORE UPDATE ON rules
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- TABLE COMMENTS
-- ============================================
COMMENT ON TABLE cameras IS 'Camera configuration and metadata';
COMMENT ON TABLE emotions IS 'Individual emotion detection events (partitioned by timestamp)';
COMMENT ON TABLE rules IS 'Sentiment-based alert rules configuration';
COMMENT ON TABLE alerts IS 'Triggered alerts from rules';
COMMENT ON TABLE sentiment_stats IS 'Aggregated sentiment statistics per camera over time windows';

COMMENT ON COLUMN emotions.frame_id IS 'Unique identifier for the video frame';
COMMENT ON COLUMN emotions.face_id IS 'Unique identifier for detected face in frame';
COMMENT ON COLUMN emotions.confidence IS 'Model confidence score (0-1)';
COMMENT ON COLUMN emotions.bounding_box IS 'Face bounding box coordinates';
COMMENT ON COLUMN rules.condition_json IS 'JSON condition definition for rule evaluation';
COMMENT ON COLUMN rules.action IS 'Action to take when rule is triggered';
COMMENT ON COLUMN sentiment_stats.sentiment_score IS 'Overall sentiment score (-1 to 1, negative to positive)';
COMMENT ON COLUMN sentiment_stats.emotion_distribution IS 'JSON distribution of all emotions';

-- ============================================
-- INITIAL DATA (Optional)
-- ============================================

-- Insert default camera for testing
INSERT INTO cameras (id, name, rtsp_url, location, active)
VALUES 
    (uuid_generate_v4(), 'Test Camera 1', 'rtsp://localhost:8554/test1', 'Main Entrance', TRUE)
ON CONFLICT (name) DO NOTHING;

-- ============================================
-- SAMPLE RULES (VANTA-20)
-- Demonstrates ThresholdRule, TrendRule, DurationRule
-- ============================================

-- ThresholdRule: High happiness detected
INSERT INTO rules (name, type, condition_json, action, enabled)
VALUES 
    ('High Happiness Threshold', 'threshold', 
     '{"type": "threshold", "emotion": "happy", "threshold": 0.8, "action": "send_alert", "severity": "info"}'::jsonb,
     'alert', TRUE)
ON CONFLICT (name) DO NOTHING;

-- ThresholdRule: High anger detected
INSERT INTO rules (name, type, condition_json, action, enabled)
VALUES 
    ('High Anger Threshold', 'threshold', 
     '{"type": "threshold", "emotion": "angry", "threshold": 0.6, "action": "send_alert", "severity": "warning"}'::jsonb,
     'alert', TRUE)
ON CONFLICT (name) DO NOTHING;

-- TrendRule: Declining mood alert
INSERT INTO rules (name, type, condition_json, action, enabled)
VALUES 
    ('Declining Mood Alert', 'trend', 
     '{"type": "trend", "direction": "declining", "min_magnitude": 0.25, "action": "send_alert", "severity": "warning"}'::jsonb,
     'alert', TRUE)
ON CONFLICT (name) DO NOTHING;

-- TrendRule: Improving mood notification
INSERT INTO rules (name, type, condition_json, action, enabled)
VALUES 
    ('Improving Mood Notification', 'trend', 
     '{"type": "trend", "direction": "improving", "min_magnitude": 0.2, "action": "log", "severity": "info"}'::jsonb,
     'log', TRUE)
ON CONFLICT (name) DO NOTHING;

-- DurationRule: Sustained anger alert
INSERT INTO rules (name, type, condition_json, action, enabled)
VALUES 
    ('Sustained Anger Alert', 'duration', 
     '{"type": "duration", "emotion": "angry", "threshold": 0.5, "duration_seconds": 60, "action": "send_alert", "severity": "critical"}'::jsonb,
     'alert', TRUE)
ON CONFLICT (name) DO NOTHING;

-- DurationRule: Prolonged sadness alert
INSERT INTO rules (name, type, condition_json, action, enabled)
VALUES 
    ('Prolonged Sadness Alert', 'duration', 
     '{"type": "duration", "emotion": "sad", "threshold": 0.4, "duration_seconds": 120, "action": "send_alert", "severity": "warning"}'::jsonb,
     'alert', TRUE)
ON CONFLICT (name) DO NOTHING;

-- Grant permissions (if needed for specific user)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO vantage;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO vantage;

-- ============================================
-- STORED FUNCTIONS (VANTA-22)
-- ============================================

-- Function: Cleanup alerts older than 30 days
CREATE OR REPLACE FUNCTION cleanup_old_alerts()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM alerts
    WHERE triggered_at < NOW() - INTERVAL '30 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION cleanup_old_alerts() IS 'Deletes alerts older than 30 days. Returns count of deleted records.';

-- Function: Aggregate alerts into hourly metrics
CREATE OR REPLACE FUNCTION aggregate_alert_metrics(target_hour TIMESTAMPTZ)
RETURNS VOID AS $$
BEGIN
    INSERT INTO alert_metrics (hour, camera_id, alert_count, severity_breakdown, top_emotion)
    SELECT 
        DATE_TRUNC('hour', triggered_at) as hour,
        camera_id,
        COUNT(*) as alert_count,
        jsonb_build_object(
            'info', COUNT(*) FILTER (WHERE severity = 'info'),
            'warning', COUNT(*) FILTER (WHERE severity = 'warning'),
            'critical', COUNT(*) FILTER (WHERE severity = 'critical')
        ) as severity_breakdown,
        MODE() WITHIN GROUP (ORDER BY emotion) as top_emotion
    FROM alerts
    WHERE DATE_TRUNC('hour', triggered_at) = target_hour
        AND camera_id IS NOT NULL
    GROUP BY DATE_TRUNC('hour', triggered_at), camera_id
    ON CONFLICT (hour, camera_id) 
    DO UPDATE SET
        alert_count = EXCLUDED.alert_count,
        severity_breakdown = EXCLUDED.severity_breakdown,
        top_emotion = EXCLUDED.top_emotion;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION aggregate_alert_metrics(TIMESTAMPTZ) IS 'Aggregates alerts for a specific hour into alert_metrics table.';
