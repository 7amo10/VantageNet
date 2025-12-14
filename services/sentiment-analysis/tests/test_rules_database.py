"""Integration tests for VANTA-20: Rules CRUD and database loading."""
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.rules import ThresholdRule, TrendRule, DurationRule
from app.rules_engine_v2 import RulesEngineV2


class MockDBRule:
    """Mock database rule record."""
    def __init__(self, rule_id, name, type, condition_json, enabled=True):
        self.id = rule_id
        self.name = name
        self.type = type
        self.condition_json = condition_json
        self.enabled = enabled
        self.created_at = datetime.now()
        self.updated_at = datetime.now()


class TestDatabaseRuleParsing:
    """Test parsing rules from database format."""
    
    def test_parse_threshold_rule_from_db(self):
        """Test parsing ThresholdRule from database JSON config."""
        engine = RulesEngineV2()
        
        db_rule = MockDBRule(
            rule_id="test-threshold-1",
            name="High Happiness Threshold",
            type="threshold",
            condition_json={
                "type": "threshold",
                "emotion": "happy",
                "threshold": 0.8,
                "action": "send_alert",
                "severity": "info"
            }
        )
        
        rule = engine._parse_rule(db_rule)
        
        assert rule is not None
        assert isinstance(rule, ThresholdRule)
        assert rule.rule_id == "test-threshold-1"
        assert rule.name == "High Happiness Threshold"
        assert rule.emotion == "happy"
        assert rule.threshold == 0.8
        assert rule.action == "send_alert"
    
    def test_parse_trend_rule_from_db(self):
        """Test parsing TrendRule from database JSON config."""
        engine = RulesEngineV2()
        
        db_rule = MockDBRule(
            rule_id="test-trend-1",
            name="Declining Mood Alert",
            type="trend",
            condition_json={
                "type": "trend",
                "direction": "declining",
                "min_magnitude": 0.25,
                "action": "send_alert",
                "severity": "warning"
            }
        )
        
        rule = engine._parse_rule(db_rule)
        
        assert rule is not None
        assert isinstance(rule, TrendRule)
        assert rule.rule_id == "test-trend-1"
        assert rule.name == "Declining Mood Alert"
        assert rule.direction == "declining"
        assert rule.min_magnitude == 0.25
    
    def test_parse_duration_rule_from_db(self):
        """Test parsing DurationRule from database JSON config."""
        engine = RulesEngineV2()
        
        db_rule = MockDBRule(
            rule_id="test-duration-1",
            name="Sustained Anger Alert",
            type="duration",
            condition_json={
                "type": "duration",
                "emotion": "angry",
                "threshold": 0.5,
                "duration_seconds": 60,
                "action": "send_alert",
                "severity": "critical"
            }
        )
        
        rule = engine._parse_rule(db_rule)
        
        assert rule is not None
        assert isinstance(rule, DurationRule)
        assert rule.rule_id == "test-duration-1"
        assert rule.name == "Sustained Anger Alert"
        assert rule.emotion == "angry"
        assert rule.threshold == 0.5
        assert rule.duration_seconds == 60
    
    def test_parse_rule_with_unknown_type(self):
        """Test parsing rule with unknown type."""
        engine = RulesEngineV2()
        
        db_rule = MockDBRule(
            rule_id="test-unknown",
            name="Unknown Rule",
            type="unknown_type",
            condition_json={
                "type": "unknown_type",
                "param": "value"
            }
        )
        
        rule = engine._parse_rule(db_rule)
        
        assert rule is None
    
    def test_parse_rule_with_missing_type(self):
        """Test parsing rule with missing type in config."""
        engine = RulesEngineV2()
        
        db_rule = MockDBRule(
            rule_id="test-no-type",
            name="No Type Rule",
            type="threshold",
            condition_json={
                "emotion": "happy",
                "threshold": 0.8
            }
        )
        
        rule = engine._parse_rule(db_rule)
        
        assert rule is None
    
    def test_parse_disabled_rule(self):
        """Test parsing disabled rule."""
        engine = RulesEngineV2()
        
        db_rule = MockDBRule(
            rule_id="test-disabled",
            name="Disabled Rule",
            type="threshold",
            condition_json={
                "type": "threshold",
                "emotion": "sad",
                "threshold": 0.6,
                "action": "log"
            },
            enabled=False
        )
        
        # Disabled rules should still parse correctly
        rule = engine._parse_rule(db_rule)
        
        assert rule is not None
        assert rule.enabled == False
    
    @pytest.mark.asyncio
    async def test_load_rules_from_mock_db(self):
        """Test loading multiple rules from mock database."""
        engine = RulesEngineV2()
        
        # Create mock database manager
        mock_db = AsyncMock()
        mock_db.get_rules = AsyncMock(return_value=[
            MockDBRule(
                rule_id="rule-1",
                name="Rule 1",
                type="threshold",
                condition_json={
                    "type": "threshold",
                    "emotion": "happy",
                    "threshold": 0.8,
                    "action": "alert"
                }
            ),
            MockDBRule(
                rule_id="rule-2",
                name="Rule 2",
                type="trend",
                condition_json={
                    "type": "trend",
                    "direction": "declining",
                    "min_magnitude": 0.2,
                    "action": "alert"
                }
            ),
            MockDBRule(
                rule_id="rule-3",
                name="Rule 3",
                type="threshold",
                condition_json={
                    "type": "threshold",
                    "emotion": "angry",
                    "threshold": 0.5,
                    "action": "alert"
                },
                enabled=False  # This one is disabled
            )
        ])
        
        engine.db_manager = mock_db
        await engine.load_rules()
        
        # Should load 2 enabled rules (rule-3 is disabled)
        assert len(engine.rules) == 2
        assert engine.rules[0].rule_id == "rule-1"
        assert engine.rules[1].rule_id == "rule-2"


class TestRuleConfigFormats:
    """Test various rule configuration formats."""
    
    def test_threshold_rule_config_with_all_emotions(self):
        """Test ThresholdRule with different emotions."""
        engine = RulesEngineV2()
        
        emotions = ["happy", "sad", "angry", "fearful", "surprised", "disgusted", "neutral"]
        
        for emotion in emotions:
            db_rule = MockDBRule(
                rule_id=f"test-{emotion}",
                name=f"{emotion.capitalize()} Rule",
                type="threshold",
                condition_json={
                    "type": "threshold",
                    "emotion": emotion,
                    "threshold": 0.7,
                    "action": "alert"
                }
            )
            
            rule = engine._parse_rule(db_rule)
            assert rule is not None
            assert rule.emotion == emotion
    
    def test_trend_rule_all_directions(self):
        """Test TrendRule with all direction types."""
        engine = RulesEngineV2()
        
        directions = ["improving", "declining", "stable"]
        
        for direction in directions:
            db_rule = MockDBRule(
                rule_id=f"test-{direction}",
                name=f"{direction.capitalize()} Trend",
                type="trend",
                condition_json={
                    "type": "trend",
                    "direction": direction,
                    "min_magnitude": 0.15,
                    "action": "alert"
                }
            )
            
            rule = engine._parse_rule(db_rule)
            assert rule is not None
            assert rule.direction == direction
    
    def test_duration_rule_various_durations(self):
        """Test DurationRule with different duration values."""
        engine = RulesEngineV2()
        
        durations = [30, 60, 120, 300]
        
        for duration in durations:
            db_rule = MockDBRule(
                rule_id=f"test-{duration}s",
                name=f"Duration {duration}s",
                type="duration",
                condition_json={
                    "type": "duration",
                    "emotion": "angry",
                    "threshold": 0.5,
                    "duration_seconds": duration,
                    "action": "alert"
                }
            )
            
            rule = engine._parse_rule(db_rule)
            assert rule is not None
            assert rule.duration_seconds == duration
