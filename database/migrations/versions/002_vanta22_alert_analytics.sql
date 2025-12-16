-- VANTA-22: Alert Database & Analytics Schema Migration
-- Adds alert analytics fields, metrics table, and stored procedures

-- Add new columns for VANTA-22
ALTER TABLE alerts 
  ADD COLUMN IF NOT EXISTS alert_type VARCHAR(50) NOT NULL DEFAULT 'rule_trigger',
  ADD COLUMN IF NOT EXISTS emotion VARCHAR(50),
  ADD COLUMN IF NOT EXISTS action_taken VARCHAR(200),
  ADD COLUMN IF NOT EXISTS metadata_json JSONB;

-- Update severity check constraint
ALTER TABLE alerts DROP CONSTRAINT IF EXISTS alerts_severity_check;
ALTER TABLE alerts ADD CONSTRAINT alerts_severity_check 
  CHECK (severity IN ('info', 'warning', 'critical'));

-- Add new indexes for performance
CREATE INDEX IF NOT EXISTS idx_alerts_camera_triggered ON alerts (camera_id, triggered_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_severity_triggered ON alerts (severity, triggered_at DESC);
CREATE INDEX IF NOT EXISTS idx_alerts_emotion ON alerts (emotion, triggered_at DESC) WHERE emotion IS NOT NULL;

-- Create alert_metrics table for hourly aggregation
CREATE TABLE IF NOT EXISTS alert_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    hour TIMESTAMPTZ NOT NULL,
    camera_id UUID NOT NULL,
    alert_count INTEGER DEFAULT 0,
    severity_breakdown JSONB NOT NULL,
    top_emotion VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT alert_metrics_unique UNIQUE (hour, camera_id)
);

CREATE INDEX IF NOT EXISTS idx_alert_metrics_hour ON alert_metrics (hour DESC);
CREATE INDEX IF NOT EXISTS idx_alert_metrics_camera_hour ON alert_metrics (camera_id, hour DESC);

-- Create cleanup function for 30-day retention
CREATE OR REPLACE FUNCTION cleanup_old_alerts(days_to_keep INTEGER DEFAULT 30)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM alerts 
    WHERE triggered_at < NOW() - (days_to_keep || ' days')::INTERVAL;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create aggregation function for hourly metrics
CREATE OR REPLACE FUNCTION aggregate_alert_metrics(target_hour TIMESTAMPTZ)
RETURNS VOID AS $$
BEGIN
    INSERT INTO alert_metrics (hour, camera_id, alert_count, severity_breakdown, top_emotion)
    SELECT 
        DATE_TRUNC('hour', triggered_at) AS hour,
        camera_id,
        COUNT(*) AS alert_count,
        jsonb_build_object(
            'info', COUNT(*) FILTER (WHERE severity = 'info'),
            'warning', COUNT(*) FILTER (WHERE severity = 'warning'),
            'critical', COUNT(*) FILTER (WHERE severity = 'critical')
        ) AS severity_breakdown,
        MODE() WITHIN GROUP (ORDER BY emotion) AS top_emotion
    FROM alerts
    WHERE DATE_TRUNC('hour', triggered_at) = DATE_TRUNC('hour', target_hour)
      AND camera_id IS NOT NULL
    GROUP BY DATE_TRUNC('hour', triggered_at), camera_id
    ON CONFLICT (hour, camera_id) 
    DO UPDATE SET
        alert_count = EXCLUDED.alert_count,
        severity_breakdown = EXCLUDED.severity_breakdown,
        top_emotion = EXCLUDED.top_emotion;
END;
$$ LANGUAGE plpgsql;
