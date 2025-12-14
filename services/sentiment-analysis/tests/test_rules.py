"""Unit tests for rules engine (VANTA-19)."""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.rules import (
    Rule, Alert, ThresholdRule, TrendRule, DurationRule
)
from app.rules_engine_v2 import RuleRegistry, RulesEngineV2
from app.models import CrowdSentiment, EmotionStats


@pytest.fixture
def sample_sentiment():
    """Create sample crowd sentiment for testing."""
    return CrowdSentiment(
        timestamp=datetime.now(),
        camera_id="cam_001",
        total_faces_observed=10,
        emotion_distribution={
            "happy": EmotionStats(count=5, avg_confidence=0.85, percentage=50.0),
            "neutral": EmotionStats(count=3, avg_confidence=0.75, percentage=30.0),
            "angry": EmotionStats(count=2, avg_confidence=0.80, percentage=20.0)
        },
        dominant_emotion="happy",
        mood_score=0.65,
        trend="stable",
        trend_magnitude=0.05
    )


@pytest.fixture
def sample_declining_sentiment():
    """Create sentiment with declining trend."""
    return CrowdSentiment(
        timestamp=datetime.now(),
        camera_id="cam_002",
        total_faces_observed=8,
        emotion_distribution={
            "sad": EmotionStats(count=4, avg_confidence=0.80, percentage=50.0),
            "angry": EmotionStats(count=3, avg_confidence=0.85, percentage=37.5),
            "neutral": EmotionStats(count=1, avg_confidence=0.70, percentage=12.5)
        },
        dominant_emotion="sad",
        mood_score=-0.45,
        trend="declining",
        trend_magnitude=0.25
    )


class TestThresholdRule:
    """Test ThresholdRule implementation."""
    
    def test_threshold_rule_triggers_above_threshold(self, sample_sentiment):
        """Test rule triggers when emotion exceeds threshold."""
        rule = ThresholdRule(
            rule_id="test_happy",
            name="High Happiness Test",
            emotion="happy",
            threshold=0.4,  # 40%
            action="test_action"
        )
        
        # happy is 50% in sample_sentiment
        alert = rule.evaluate(sample_sentiment)
        
        assert alert is not None
        assert alert.rule_id == "test_happy"
        assert alert.severity == "warning"
        assert "happy" in alert.message.lower()
        assert alert.camera_id == "cam_001"
    
    def test_threshold_rule_no_trigger_below_threshold(self, sample_sentiment):
        """Test rule does not trigger when below threshold."""
        rule = ThresholdRule(
            rule_id="test_angry",
            name="High Anger Test",
            emotion="angry",
            threshold=0.3,  # 30%
            action="test_action"
        )
        
        # angry is 20% in sample_sentiment
        alert = rule.evaluate(sample_sentiment)
        
        assert alert is None
    
    def test_threshold_rule_exact_threshold(self, sample_sentiment):
        """Test rule triggers at exact threshold."""
        rule = ThresholdRule(
            rule_id="test_exact",
            name="Exact Threshold Test",
            emotion="happy",
            threshold=0.5,  # exactly 50%
            action="test_action"
        )
        
        # happy is exactly 50%
        alert = rule.evaluate(sample_sentiment)
        
        # Should not trigger (needs to be ABOVE threshold)
        assert alert is None
    
    def test_threshold_rule_missing_emotion(self, sample_sentiment):
        """Test rule handles missing emotion gracefully."""
        rule = ThresholdRule(
            rule_id="test_missing",
            name="Missing Emotion Test",
            emotion="surprised",  # not in sample
            threshold=0.1,
            action="test_action"
        )
        
        alert = rule.evaluate(sample_sentiment)
        
        assert alert is None
    
    def test_threshold_rule_config(self):
        """Test get_config returns correct configuration."""
        rule = ThresholdRule(
            rule_id="test_config",
            name="Config Test",
            emotion="happy",
            threshold=0.75,
            action="show_promotion",
            priority=5
        )
        
        config = rule.get_config()
        
        assert config["type"] == "threshold"
        assert config["emotion"] == "happy"
        assert config["threshold"] == 0.75
        assert config["action"] == "show_promotion"


class TestTrendRule:
    """Test TrendRule implementation."""
    
    def test_trend_rule_declining_triggers(self, sample_declining_sentiment):
        """Test rule triggers on declining trend with sufficient magnitude."""
        rule = TrendRule(
            rule_id="test_declining",
            name="Declining Mood Test",
            direction="declining",
            min_magnitude=0.15,
            action="alert_staff"
        )
        
        # sentiment has declining trend with magnitude 0.25
        alert = rule.evaluate(sample_declining_sentiment)
        
        assert alert is not None
        assert alert.severity == "critical"
        assert "declining" in alert.message.lower()
    
    def test_trend_rule_magnitude_too_small(self, sample_sentiment):
        """Test rule does not trigger when magnitude is too small."""
        rule = TrendRule(
            rule_id="test_small",
            name="Small Magnitude Test",
            direction="stable",
            min_magnitude=0.1,  # sample has 0.05 magnitude
            action="test_action"
        )
        
        alert = rule.evaluate(sample_sentiment)
        
        assert alert is None
    
    def test_trend_rule_improving_triggers(self):
        """Test rule triggers on improving trend."""
        improving_sentiment = CrowdSentiment(
            timestamp=datetime.now(),
            camera_id="cam_003",
            total_faces_observed=12,
            emotion_distribution={
                "happy": EmotionStats(count=8, avg_confidence=0.90, percentage=66.7)
            },
            dominant_emotion="happy",
            mood_score=0.75,
            trend="improving",
            trend_magnitude=0.20
        )
        
        rule = TrendRule(
            rule_id="test_improving",
            name="Improving Mood Test",
            direction="improving",
            min_magnitude=0.15,
            action="celebrate"
        )
        
        alert = rule.evaluate(improving_sentiment)
        
        assert alert is not None
        assert alert.severity == "info"
        assert "improving" in alert.message.lower()
    
    def test_trend_rule_wrong_direction(self, sample_declining_sentiment):
        """Test rule does not trigger with wrong trend direction."""
        rule = TrendRule(
            rule_id="test_wrong",
            name="Wrong Direction Test",
            direction="improving",  # sentiment is declining
            min_magnitude=0.1,
            action="test_action"
        )
        
        alert = rule.evaluate(sample_declining_sentiment)
        
        assert alert is None


class TestDurationRule:
    """Test DurationRule implementation."""
    
    def test_duration_rule_persistence_tracking(self, sample_sentiment):
        """Test rule tracks condition persistence over time."""
        rule = DurationRule(
            rule_id="test_duration",
            name="Sustained Anger Test",
            emotion="angry",
            threshold=0.15,  # 15%
            duration_seconds=10,
            action="escalate"
        )
        
        # Create sentiment with 20% angry
        high_anger_sentiment = CrowdSentiment(
            timestamp=datetime.now(),
            camera_id="cam_001",
            total_faces_observed=10,
            emotion_distribution={
                "angry": EmotionStats(count=2, avg_confidence=0.85, percentage=20.0),
                "neutral": EmotionStats(count=8, avg_confidence=0.75, percentage=80.0)
            },
            dominant_emotion="neutral",
            mood_score=0.3,
            trend="stable",
            trend_magnitude=0.05
        )
        
        # First evaluation - condition starts
        alert = rule.evaluate(high_anger_sentiment)
        assert alert is None  # Not enough time passed
        
        # Check that tracking started
        assert "cam_001" in rule._condition_start
    
    def test_duration_rule_resets_on_break(self):
        """Test rule resets tracking when condition breaks."""
        rule = DurationRule(
            rule_id="test_reset",
            name="Reset Test",
            emotion="angry",
            threshold=0.5,
            duration_seconds=5,
            action="test_action"
        )
        
        # First: condition met
        high_anger = CrowdSentiment(
            timestamp=datetime.now(),
            camera_id="cam_001",
            total_faces_observed=10,
            emotion_distribution={
                "angry": EmotionStats(count=6, avg_confidence=0.85, percentage=60.0)
            },
            dominant_emotion="angry",
            mood_score=-0.3,
            trend="stable",
            trend_magnitude=0.05
        )
        
        rule.evaluate(high_anger)
        assert "cam_001" in rule._condition_start
        
        # Second: condition breaks
        low_anger = CrowdSentiment(
            timestamp=datetime.now(),
            camera_id="cam_001",
            total_faces_observed=10,
            emotion_distribution={
                "angry": EmotionStats(count=1, avg_confidence=0.80, percentage=10.0),
                "neutral": EmotionStats(count=9, avg_confidence=0.75, percentage=90.0)
            },
            dominant_emotion="neutral",
            mood_score=0.5,
            trend="stable",
            trend_magnitude=0.05
        )
        
        rule.evaluate(low_anger)
        assert "cam_001" not in rule._condition_start  # Tracking reset
    
    def test_duration_rule_multiple_cameras(self):
        """Test rule tracks multiple cameras independently."""
        rule = DurationRule(
            rule_id="test_multi",
            name="Multi Camera Test",
            emotion="sad",
            threshold=0.3,
            duration_seconds=5,
            action="test_action"
        )
        
        # Camera 1
        sentiment_cam1 = CrowdSentiment(
            timestamp=datetime.now(),
            camera_id="cam_001",
            total_faces_observed=10,
            emotion_distribution={
                "sad": EmotionStats(count=4, avg_confidence=0.80, percentage=40.0)
            },
            dominant_emotion="sad",
            mood_score=-0.2,
            trend="stable",
            trend_magnitude=0.05
        )
        
        # Camera 2
        sentiment_cam2 = CrowdSentiment(
            timestamp=datetime.now(),
            camera_id="cam_002",
            total_faces_observed=8,
            emotion_distribution={
                "sad": EmotionStats(count=3, avg_confidence=0.85, percentage=37.5)
            },
            dominant_emotion="sad",
            mood_score=-0.15,
            trend="stable",
            trend_magnitude=0.05
        )
        
        # Evaluate both
        rule.evaluate(sentiment_cam1)
        rule.evaluate(sentiment_cam2)
        
        # Both should be tracked
        assert "cam_001" in rule._condition_start
        assert "cam_002" in rule._condition_start


class TestRuleRegistry:
    """Test RuleRegistry implementation."""
    
    def test_registry_has_builtin_types(self):
        """Test registry registers built-in rule types."""
        registry = RuleRegistry()
        
        assert "threshold" in registry.list_types()
        assert "trend" in registry.list_types()
        assert "duration" in registry.list_types()
    
    def test_registry_get_rule_class(self):
        """Test registry returns correct rule class."""
        registry = RuleRegistry()
        
        threshold_class = registry.get("threshold")
        assert threshold_class == ThresholdRule
        
        trend_class = registry.get("trend")
        assert trend_class == TrendRule
    
    def test_registry_unknown_type(self):
        """Test registry returns None for unknown type."""
        registry = RuleRegistry()
        
        unknown = registry.get("nonexistent")
        assert unknown is None
    
    def test_registry_custom_registration(self):
        """Test registering custom rule type."""
        registry = RuleRegistry()
        
        # Create mock rule class
        class CustomRule(Rule):
            def evaluate(self, sentiment):
                return None
            
            def get_config(self):
                return {"type": "custom"}
        
        registry.register("custom", CustomRule)
        
        assert "custom" in registry.list_types()
        assert registry.get("custom") == CustomRule


class TestRulesEngineV2:
    """Test RulesEngineV2 implementation."""
    
    @pytest.mark.asyncio
    async def test_engine_load_default_rules(self):
        """Test engine loads default rules without database."""
        engine = RulesEngineV2()
        await engine.load_rules()
        
        assert len(engine.rules) == 3  # 3 default rules
        assert engine.rules[0].rule_id == "high_happy_threshold"
    
    @pytest.mark.asyncio
    async def test_engine_evaluate_all(self, sample_sentiment):
        """Test engine evaluates all rules."""
        engine = RulesEngineV2()
        await engine.load_rules()
        
        alerts = await engine.evaluate_all(sample_sentiment)
        
        # All rules should be evaluated
        assert engine.rules_evaluated_total == 3
        # Alerts may or may not trigger depending on threshold
        # Just verify no crashes and metrics are updated
        assert engine.rules_triggered_total >= 0
    
    @pytest.mark.asyncio
    async def test_engine_error_handling(self, sample_sentiment):
        """Test engine handles evaluation errors gracefully."""
        engine = RulesEngineV2()
        
        # Create rule that raises error
        class BrokenRule(Rule):
            def __init__(self):
                super().__init__(
                    rule_id="broken",
                    name="Broken Rule",
                    enabled=True,
                    priority=5
                )
            
            def evaluate(self, sentiment):
                raise ValueError("Test error")
            
            def get_config(self):
                return {}
        
        engine.rules = [BrokenRule()]
        
        # Should not crash
        alerts = await engine.evaluate_all(sample_sentiment)
        
        assert len(alerts) == 0
        assert engine.evaluation_errors == 1
    
    @pytest.mark.asyncio
    async def test_engine_alert_queue(self):
        """Test engine queues alerts when database fails."""
        engine = RulesEngineV2()  # No database
        
        alert = Alert(
            rule_id="test",
            rule_name="Test Rule",
            camera_id="cam_001",
            timestamp=datetime.now(),
            severity="warning",
            message="Test alert",
            sentiment_snapshot={}
        )
        
        # Should queue alerts in memory
        success = await engine.store_alerts([alert])
        
        assert not success  # No database
        assert len(engine._alert_queue) == 1
    
    @pytest.mark.asyncio
    async def test_engine_reload_rules(self):
        """Test engine reloads rules on demand."""
        engine = RulesEngineV2()
        await engine.load_rules()
        
        initial_count = len(engine.rules)
        
        # Reload
        await engine.reload_rules()
        
        assert len(engine.rules) == initial_count
    
    def test_engine_metrics(self):
        """Test engine returns metrics."""
        engine = RulesEngineV2()
        
        metrics = engine.get_metrics()
        
        assert "total_rules" in metrics
        assert "rules_evaluated_total" in metrics
        assert "rules_triggered_total" in metrics
        assert "evaluation_errors" in metrics


class TestAlert:
    """Test Alert data class."""
    
    def test_alert_to_dict(self):
        """Test alert serialization to dict."""
        alert = Alert(
            rule_id="test_rule",
            rule_name="Test Rule",
            camera_id="cam_001",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            severity="critical",
            message="Test message",
            sentiment_snapshot={"mood_score": 0.5}
        )
        
        alert_dict = alert.to_dict()
        
        assert alert_dict["rule_id"] == "test_rule"
        assert alert_dict["severity"] == "critical"
        assert alert_dict["camera_id"] == "cam_001"
        assert "sentiment_snapshot" in alert_dict
