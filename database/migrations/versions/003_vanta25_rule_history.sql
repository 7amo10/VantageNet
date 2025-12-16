-- VANTA-25: Rule Management API - Add rule_evaluations table for history
-- Migration: 003_vanta25_rule_history.sql
-- Author: VantageNet Development Team
-- Created: 2025-12-16

-- ============================================
-- RULE_EVALUATIONS TABLE
-- Stores history of rule evaluations
-- ============================================
CREATE TABLE IF NOT EXISTS rule_evaluations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    rule_id UUID NOT NULL,
    camera_id UUID,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    matched BOOLEAN NOT NULL,
    emotion VARCHAR(50),
    sentiment_score FLOAT,
    threshold_value FLOAT,
    evaluation_result JSONB,
    action_taken VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for fast history queries
CREATE INDEX idx_rule_evaluations_rule_id ON rule_evaluations(rule_id, evaluated_at DESC);
CREATE INDEX idx_rule_evaluations_camera_id ON rule_evaluations(camera_id, evaluated_at DESC) WHERE camera_id IS NOT NULL;
CREATE INDEX idx_rule_evaluations_matched ON rule_evaluations(matched, evaluated_at DESC);
CREATE INDEX idx_rule_evaluations_evaluated_at ON rule_evaluations(evaluated_at DESC);

-- Foreign key constraints
ALTER TABLE rule_evaluations ADD CONSTRAINT fk_rule_evaluations_rule
    FOREIGN KEY (rule_id) REFERENCES rules(id) ON DELETE CASCADE;

ALTER TABLE rule_evaluations ADD CONSTRAINT fk_rule_evaluations_camera
    FOREIGN KEY (camera_id) REFERENCES cameras(id) ON DELETE SET NULL;

-- Index for cleanup queries (evaluations older than 90 days)
CREATE INDEX idx_rule_evaluations_created_at ON rule_evaluations(created_at);

COMMENT ON TABLE rule_evaluations IS 'Stores history of rule evaluations for analytics and debugging (VANTA-25)';
COMMENT ON COLUMN rule_evaluations.matched IS 'Whether the rule condition was matched (true) or not (false)';
COMMENT ON COLUMN rule_evaluations.evaluation_result IS 'Detailed evaluation result including all intermediate values';
