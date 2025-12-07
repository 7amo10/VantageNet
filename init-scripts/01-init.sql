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
-- ALERTS TABLE
-- Stores triggered alerts from rules
-- ============================================
CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_id UUID NOT NULL,
    message TEXT NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    triggered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    camera_id UUID,
    trigger_data JSONB,
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by VARCHAR(100),
    acknowledged_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_alerts_triggered_at ON alerts(triggered_at DESC);
CREATE INDEX idx_alerts_rule_id ON alerts(rule_id, triggered_at DESC);
CREATE INDEX idx_alerts_severity ON alerts(severity, triggered_at DESC) WHERE resolved_at IS NULL;
CREATE INDEX idx_alerts_camera_id ON alerts(camera_id, triggered_at DESC) WHERE camera_id IS NOT NULL;
CREATE INDEX idx_alerts_unresolved ON alerts(triggered_at DESC) WHERE resolved_at IS NULL;

-- Foreign key constraints
ALTER TABLE alerts ADD CONSTRAINT fk_alerts_rule
    FOREIGN KEY (rule_id) REFERENCES rules(id) ON DELETE CASCADE;
    
ALTER TABLE alerts ADD CONSTRAINT fk_alerts_camera
    FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE SET NULL;

-- ============================================
-- SENTIMENT_STATS TABLE
-- Stores aggregated sentiment statistics per camera
-- ============================================
CREATE TABLE IF NOT EXISTS sentiment_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    camera_id UUID NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    time_window_start TIMESTAMPTZ NOT NULL,
    time_window_end TIMESTAMPTZ NOT NULL,
    total_faces INTEGER DEFAULT 0 CHECK (total_faces >= 0),
    avg_happy DECIMAL(5,4) CHECK (avg_happy >= 0 AND avg_happy <= 1),
    avg_sad DECIMAL(5,4) CHECK (avg_sad >= 0 AND avg_sad <= 1),
    avg_angry DECIMAL(5,4) CHECK (avg_angry >= 0 AND avg_angry <= 1),
    avg_neutral DECIMAL(5,4) CHECK (avg_neutral >= 0 AND avg_neutral <= 1),
    avg_surprised DECIMAL(5,4) CHECK (avg_surprised >= 0 AND avg_surprised <= 1),
    avg_fear DECIMAL(5,4) CHECK (avg_fear >= 0 AND avg_fear <= 1),
    avg_disgust DECIMAL(5,4) CHECK (avg_disgust >= 0 AND avg_disgust <= 1),
    dominant_emotion VARCHAR(50),
    sentiment_score DECIMAL(5,4) CHECK (sentiment_score >= -1 AND sentiment_score <= 1),
    average_confidence DECIMAL(5,4) CHECK (average_confidence >= 0 AND average_confidence <= 1),
    emotion_distribution JSONB,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sentiment_stats_timestamp ON sentiment_stats(timestamp DESC);
CREATE INDEX idx_sentiment_stats_camera_id ON sentiment_stats(camera_id, timestamp DESC);
CREATE INDEX idx_sentiment_stats_time_window ON sentiment_stats(time_window_start, time_window_end);
CREATE INDEX idx_sentiment_stats_dominant_emotion ON sentiment_stats(dominant_emotion, timestamp DESC);

-- Foreign key constraint
ALTER TABLE sentiment_stats ADD CONSTRAINT fk_sentiment_stats_camera
    FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE CASCADE;

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

-- Insert default rule for testing
INSERT INTO rules (name, type, condition_json, action, enabled)
VALUES 
    ('High Negative Sentiment Alert', 'sentiment', 
     '{"metric": "sentiment_score", "operator": "<", "threshold": -0.5}'::jsonb,
     'alert', TRUE)
ON CONFLICT (name) DO NOTHING;

-- Grant permissions (if needed for specific user)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO vantage;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO vantage;
