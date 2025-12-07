-- VantageNet Database Initialization Script
-- Creates necessary tables for emotion analytics platform

-- Create extension for UUID support
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- Emotion Events Table
-- ============================================
CREATE TABLE IF NOT EXISTS emotion_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    camera_id VARCHAR(100) NOT NULL,
    frame_number BIGINT,
    face_id VARCHAR(100),
    emotion VARCHAR(50) NOT NULL,
    confidence DECIMAL(5,4) NOT NULL,
    bounding_box JSONB,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for faster queries by timestamp and camera
CREATE INDEX idx_emotion_events_timestamp ON emotion_events(timestamp);
CREATE INDEX idx_emotion_events_camera ON emotion_events(camera_id);
CREATE INDEX idx_emotion_events_emotion ON emotion_events(emotion);

-- ============================================
-- Sentiment Analytics Table
-- ============================================
CREATE TABLE IF NOT EXISTS sentiment_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    camera_id VARCHAR(100) NOT NULL,
    time_window_start TIMESTAMPTZ NOT NULL,
    time_window_end TIMESTAMPTZ NOT NULL,
    total_faces INTEGER DEFAULT 0,
    emotion_distribution JSONB,
    dominant_emotion VARCHAR(50),
    average_confidence DECIMAL(5,4),
    sentiment_score DECIMAL(5,4),
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for faster analytics queries
CREATE INDEX idx_sentiment_analytics_timestamp ON sentiment_analytics(timestamp);
CREATE INDEX idx_sentiment_analytics_camera ON sentiment_analytics(camera_id);

-- ============================================
-- Alert Rules Table
-- ============================================
CREATE TABLE IF NOT EXISTS alert_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(200) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    rule_type VARCHAR(50) NOT NULL,
    conditions JSONB NOT NULL,
    actions JSONB NOT NULL,
    camera_ids JSONB,
    created_by VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- Alert History Table
-- ============================================
CREATE TABLE IF NOT EXISTS alert_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_id UUID REFERENCES alert_rules(id),
    triggered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    camera_id VARCHAR(100),
    trigger_data JSONB,
    action_taken JSONB,
    status VARCHAR(50) DEFAULT 'pending',
    acknowledged_at TIMESTAMPTZ,
    acknowledged_by VARCHAR(100),
    notes TEXT
);

-- Index for alert history queries
CREATE INDEX idx_alert_history_triggered ON alert_history(triggered_at);
CREATE INDEX idx_alert_history_rule ON alert_history(rule_id);

-- ============================================
-- Camera Configuration Table
-- ============================================
CREATE TABLE IF NOT EXISTS cameras (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    camera_id VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    location VARCHAR(500),
    rtsp_url VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE,
    configuration JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE emotion_events IS 'Stores individual emotion detection events from video frames';
COMMENT ON TABLE sentiment_analytics IS 'Stores aggregated sentiment analytics over time windows';
COMMENT ON TABLE alert_rules IS 'Stores configured alert rules for emotion-based triggers';
COMMENT ON TABLE alert_history IS 'Stores history of triggered alerts';
COMMENT ON TABLE cameras IS 'Stores camera configuration and metadata';
