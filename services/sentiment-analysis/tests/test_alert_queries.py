"""Tests for alert database queries and analytics (VANTA-22)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import asyncio
from datetime import datetime, timedelta
import uuid
from sqlalchemy import text

from app.database import DatabaseManager, Alert, AlertMetric
from app.config import settings

# Test UUID constants for consistent camera IDs across tests
CAMERA_1_UUID = "00000000-0000-0000-0000-000000000001"
CAMERA_2_UUID = "00000000-0000-0000-0000-000000000002"

# Global default rule ID for tests (created once per session)
_test_default_rule_id = None

def get_default_rule_id():
    """Get or create default rule ID for tests."""
    global _test_default_rule_id
    if _test_default_rule_id is None:
        _test_default_rule_id = str(uuid.uuid4())
    return _test_default_rule_id


@pytest.fixture(scope="session")
async def db_manager():
    """Create database manager for testing (session-scoped)."""
    manager = DatabaseManager()
    await manager.connect()
    
    # Create default test resources ONCE for all tests in this session
    global _test_default_rule_id
    _test_default_rule_id = str(uuid.uuid4())
    async with manager.get_session() as session:
        from app.database import Rule
        
        # Create default test rule
        rule = Rule(
            id=_test_default_rule_id,
            name="Default Test Rule",
            type="sentiment",
            condition_json={"test": True},
            action="log",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(rule)
        
        # Create default test cameras (used by most tests)
        await session.execute(text("""
            INSERT INTO cameras (id, name, rtsp_url, location, active, created_at, updated_at)
            VALUES 
                ('00000000-0000-0000-0000-000000000001', 'Test Camera 1', 'rtsp://test1', 'Test Location 1', true, NOW(), NOW()),
                ('00000000-0000-0000-0000-000000000002', 'Test Camera 2', 'rtsp://test2', 'Test Location 2', true, NOW(), NOW())
            ON CONFLICT (id) DO NOTHING
        """))
        
        await session.commit()
    
    yield manager
    await manager.disconnect()


@pytest.fixture
async def clean_alerts(db_manager):
    """Clean alerts and rules tables before each test."""
    async with db_manager.get_session() as session:
        await session.execute(text("DELETE FROM alerts"))
        await session.execute(text("DELETE FROM alert_metrics"))
        # Delete all test rules except the default one
        await session.execute(text("DELETE FROM rules WHERE name != 'Default Test Rule'"))
    yield
    # Cleanup after test
    async with db_manager.get_session() as session:
        await session.execute(text("DELETE FROM alerts"))
        await session.execute(text("DELETE FROM alert_metrics"))
        # Delete all test rules except the default one
        await session.execute(text("DELETE FROM rules WHERE name != 'Default Test Rule'"))


def create_test_alert(
    camera_id=CAMERA_1_UUID,
    emotion="happy",
    severity="info",
    triggered_at=None,
    rule_id=None,
    create_rule=False,
    session=None
):
    """Helper to create test alert data.
    
    Args:
        camera_id: Camera UUID
        emotion: Emotion string
        severity: Severity level
        triggered_at: Timestamp
        rule_id: Rule UUID (uses default test rule if None)
        create_rule: DEPRECATED - rule is created by db_manager fixture
        session: DEPRECATED - not needed anymore
    """
    if triggered_at is None:
        triggered_at = datetime.utcnow()
    if rule_id is None:
        rule_id = get_default_rule_id()
    
    return {
        "id": str(uuid.uuid4()),
        "rule_id": rule_id,
        "camera_id": camera_id,
        "alert_type": "rule_trigger",
        "emotion": emotion,
        "message": f"Test alert for {emotion}",
        "severity": severity,
        "triggered_at": triggered_at,
        "resolved_at": None,
        "action_taken": None,
        "metadata_json": {"test": True},
        "acknowledged": False
    }


async def create_test_rule(session, rule_id=None, name=None):
    """Helper to create a test rule in the database.
    
    Args:
        session: Database session
        rule_id: Optional rule UUID (generates new one if None)
        name: Optional rule name (uses UUID as name if None)
    
    Returns:
        str: The rule ID
    """
    from app.database import Rule
    
    if rule_id is None:
        rule_id = str(uuid.uuid4())
    if name is None:
        name = f"Test Rule {rule_id[:8]}"
    
    rule = Rule(
        id=rule_id,
        name=name,
        type="sentiment",
        condition_json={"test": True},
        action="log",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    session.add(rule)
    return rule_id


class TestAlertModel:
    """Test Alert model structure."""
    
    def test_alert_model_fields(self):
        """Test that Alert model has all required fields."""
        alert = Alert(
            id=str(uuid.uuid4()),
            rule_id=str(uuid.uuid4()),
            camera_id=CAMERA_1_UUID,
            alert_type="rule_trigger",
            emotion="happy",
            message="Test message",
            severity="info",
            triggered_at=datetime.utcnow()
        )
        
        assert alert.id is not None
        assert alert.rule_id is not None
        assert alert.camera_id == CAMERA_1_UUID
        assert alert.alert_type == "rule_trigger"
        assert alert.emotion == "happy"
        assert alert.severity == "info"
        assert alert.triggered_at is not None


class TestGetAlerts:
    """Test get_alerts query method."""
    
    @pytest.mark.asyncio
    async def test_get_alerts_empty(self, db_manager, clean_alerts):
        """Test get_alerts with no alerts."""
        alerts = await db_manager.get_alerts()
        assert alerts == []
    
    @pytest.mark.asyncio
    async def test_get_alerts_basic(self, db_manager, clean_alerts):
        """Test get_alerts returns inserted alerts."""
        # Insert test alert
        async with db_manager.get_session() as session:
            alert_data = create_test_alert(create_rule=True, session=session)
            alert = Alert(**alert_data)
            session.add(alert)
        
        # Query alerts
        alerts = await db_manager.get_alerts()
        assert len(alerts) == 1
        assert alerts[0]["camera_id"] == CAMERA_1_UUID
        assert alerts[0]["emotion"] == "happy"
    
    @pytest.mark.asyncio
    async def test_get_alerts_filter_by_camera(self, db_manager, clean_alerts):
        """Test get_alerts filtered by camera_id."""
        # Insert alerts for different cameras
        async with db_manager.get_session() as session:
            alert1 = Alert(**create_test_alert(camera_id=CAMERA_1_UUID, create_rule=True, session=session))
            alert2 = Alert(**create_test_alert(camera_id=CAMERA_2_UUID, create_rule=True, session=session))
            alert3 = Alert(**create_test_alert(camera_id=CAMERA_1_UUID, create_rule=True, session=session))
            session.add_all([alert1, alert2, alert3])
        
        # Query camera-1 only
        alerts = await db_manager.get_alerts(camera_id=CAMERA_1_UUID)
        assert len(alerts) == 2
        assert all(a["camera_id"] == CAMERA_1_UUID for a in alerts)
    
    @pytest.mark.asyncio
    async def test_get_alerts_filter_by_severity(self, db_manager, clean_alerts):
        """Test get_alerts filtered by severity."""
        # Insert alerts with different severities
        async with db_manager.get_session() as session:
            alert1 = Alert(**create_test_alert(severity="info", create_rule=True, session=session))
            alert2 = Alert(**create_test_alert(severity="warning", create_rule=True, session=session))
            alert3 = Alert(**create_test_alert(severity="critical", create_rule=True, session=session))
            session.add_all([alert1, alert2, alert3])
        
        # Query critical only
        alerts = await db_manager.get_alerts(severity="critical")
        assert len(alerts) == 1
        assert alerts[0]["severity"] == "critical"
    
    @pytest.mark.asyncio
    async def test_get_alerts_time_range(self, db_manager, clean_alerts):
        """Test get_alerts filtered by time range."""
        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)
        two_hours_ago = now - timedelta(hours=2)
        
        # Insert alerts at different times
        async with db_manager.get_session() as session:
            alert1 = Alert(**create_test_alert(triggered_at=two_hours_ago, create_rule=True, session=session))
            alert2 = Alert(**create_test_alert(triggered_at=one_hour_ago, create_rule=True, session=session))
            alert3 = Alert(**create_test_alert(triggered_at=now, create_rule=True, session=session))
            session.add_all([alert1, alert2, alert3])
        
        # Query last hour only
        alerts = await db_manager.get_alerts(
            start_time=one_hour_ago - timedelta(minutes=5),
            end_time=now + timedelta(minutes=5)
        )
        assert len(alerts) == 2
    
    @pytest.mark.asyncio
    async def test_get_alerts_limit(self, db_manager, clean_alerts):
        """Test get_alerts respects limit parameter."""
        # Insert 10 alerts
        async with db_manager.get_session() as session:
            for i in range(10):
                alert = Alert(**create_test_alert(create_rule=True, session=session))
                session.add(alert)
        
        # Query with limit=5
        alerts = await db_manager.get_alerts(limit=5)
        assert len(alerts) == 5
    
    @pytest.mark.asyncio
    async def test_get_alerts_ordered_by_time(self, db_manager, clean_alerts):
        """Test get_alerts returns alerts ordered by triggered_at DESC."""
        now = datetime.utcnow()
        
        # Insert alerts with increasing timestamps
        async with db_manager.get_session() as session:
            for i in range(3):
                alert = Alert(**create_test_alert(
                    triggered_at=now + timedelta(minutes=i),
                    create_rule=True,
                    session=session
                ))
                session.add(alert)
        
        alerts = await db_manager.get_alerts()
        assert len(alerts) == 3
        # Should be in descending order (newest first)
        for i in range(len(alerts) - 1):
            assert alerts[i]["triggered_at"] >= alerts[i+1]["triggered_at"]


class TestSeverityDistribution:
    """Test get_severity_distribution query method."""
    
    @pytest.mark.asyncio
    async def test_severity_distribution_empty(self, db_manager, clean_alerts):
        """Test severity distribution with no alerts."""
        dist = await db_manager.get_severity_distribution()
        assert dist == {"info": 0, "warning": 0, "critical": 0, "total": 0}
    
    @pytest.mark.asyncio
    async def test_severity_distribution_basic(self, db_manager, clean_alerts):
        """Test severity distribution with various severities."""
        # Insert alerts with different severities
        async with db_manager.get_session() as session:
            for _ in range(3):
                session.add(Alert(**create_test_alert(severity="info", create_rule=True, session=session)))
            for _ in range(2):
                session.add(Alert(**create_test_alert(severity="warning", create_rule=True, session=session)))
            for _ in range(1):
                session.add(Alert(**create_test_alert(severity="critical", create_rule=True, session=session)))
        
        dist = await db_manager.get_severity_distribution()
        assert dist["info"] == 3
        assert dist["warning"] == 2
        assert dist["critical"] == 1
        assert dist["total"] == 6
    
    @pytest.mark.asyncio
    async def test_severity_distribution_filter_camera(self, db_manager, clean_alerts):
        """Test severity distribution filtered by camera."""
        # Insert alerts for different cameras
        async with db_manager.get_session() as session:
            for _ in range(5):
                session.add(Alert(**create_test_alert(camera_id=CAMERA_1_UUID, severity="info", create_rule=True, session=session)))
            for _ in range(3):
                session.add(Alert(**create_test_alert(camera_id=CAMERA_2_UUID, severity="warning", create_rule=True, session=session)))
        
        # Query camera-1 only
        dist = await db_manager.get_severity_distribution(camera_id=CAMERA_1_UUID)
        assert dist["info"] == 5
        assert dist["warning"] == 0
        assert dist["total"] == 5
    
    @pytest.mark.asyncio
    async def test_severity_distribution_time_period(self, db_manager, clean_alerts):
        """Test severity distribution within time period."""
        now = datetime.utcnow()
        two_days_ago = now - timedelta(days=2)
        
        # Insert old and recent alerts
        async with db_manager.get_session() as session:
            session.add(Alert(**create_test_alert(
                severity="info",
                triggered_at=two_days_ago,
                create_rule=True,
                session=session
            )))
            session.add(Alert(**create_test_alert(
                severity="warning",
                triggered_at=now,
                create_rule=True,
                session=session
            )))
        
        # Query last 24 hours only
        dist = await db_manager.get_severity_distribution(period_hours=24)
        assert dist["info"] == 0  # Old alert not included
        assert dist["warning"] == 1
        assert dist["total"] == 1


class TestTopRules:
    """Test get_top_rules query method."""
    
    @pytest.mark.asyncio
    async def test_top_rules_empty(self, db_manager, clean_alerts):
        """Test top rules with no alerts."""
        rules = await db_manager.get_top_rules()
        assert rules == []
    
    @pytest.mark.asyncio
    async def test_top_rules_basic(self, db_manager, clean_alerts):
        """Test top rules returns most triggered rules."""
        rule1 = str(uuid.uuid4())
        rule2 = str(uuid.uuid4())
        rule3 = str(uuid.uuid4())
        
        # Insert alerts with different rule IDs
        async with db_manager.get_session() as session:
            # Create the rules first
            await create_test_rule(session, rule1, "Test Rule 1")
            await create_test_rule(session, rule2, "Test Rule 2")
            await create_test_rule(session, rule3, "Test Rule 3")
            await session.commit()  # Commit rules before creating alerts
            
            # Rule 1: 5 triggers
            for _ in range(5):
                session.add(Alert(**create_test_alert(rule_id=rule1)))
            # Rule 2: 3 triggers
            for _ in range(3):
                session.add(Alert(**create_test_alert(rule_id=rule2)))
            # Rule 3: 1 trigger
            session.add(Alert(**create_test_alert(rule_id=rule3)))
        
        rules = await db_manager.get_top_rules(limit=3)
        assert len(rules) == 3
        assert rules[0]["rule_id"] == rule1
        assert rules[0]["trigger_count"] == 5
        assert rules[1]["rule_id"] == rule2
        assert rules[1]["trigger_count"] == 3
        assert rules[2]["rule_id"] == rule3
        assert rules[2]["trigger_count"] == 1
    
    @pytest.mark.asyncio
    async def test_top_rules_limit(self, db_manager, clean_alerts):
        """Test top rules respects limit parameter."""
        # Insert alerts for 5 different rules
        async with db_manager.get_session() as session:
            for i in range(5):
                rule_id = str(uuid.uuid4())
                await create_test_rule(session, rule_id, f"Test Rule {i+1}")
                await session.commit()  # Commit each rule before creating alerts
                for _ in range(i + 1):
                    session.add(Alert(**create_test_alert(rule_id=rule_id)))
        
        # Query top 2 only
        rules = await db_manager.get_top_rules(limit=2)
        assert len(rules) == 2
    
    @pytest.mark.asyncio
    async def test_top_rules_filter_camera(self, db_manager, clean_alerts):
        """Test top rules filtered by camera."""
        rule1 = str(uuid.uuid4())
        rule2 = str(uuid.uuid4())
        
        # Insert alerts for different cameras
        async with db_manager.get_session() as session:
            await create_test_rule(session, rule1, "Test Rule 1")
            await create_test_rule(session, rule2, "Test Rule 2")
            await session.commit()  # Commit rules before creating alerts
            for _ in range(5):
                session.add(Alert(**create_test_alert(rule_id=rule1, camera_id=CAMERA_1_UUID)))
            for _ in range(3):
                session.add(Alert(**create_test_alert(rule_id=rule2, camera_id=CAMERA_2_UUID)))
        
        # Query camera-1 only
        rules = await db_manager.get_top_rules(camera_id=CAMERA_1_UUID)
        assert len(rules) == 1
        assert rules[0]["rule_id"] == rule1
        assert rules[0]["trigger_count"] == 5


class TestEmotionTriggers:
    """Test get_emotion_triggers query method."""
    
    @pytest.mark.asyncio
    async def test_emotion_triggers_empty(self, db_manager, clean_alerts):
        """Test emotion triggers with no alerts."""
        emotions = await db_manager.get_emotion_triggers()
        assert emotions == {}
    
    @pytest.mark.asyncio
    async def test_emotion_triggers_basic(self, db_manager, clean_alerts):
        """Test emotion triggers returns emotion counts."""
        # Insert alerts with different emotions
        async with db_manager.get_session() as session:
            for _ in range(5):
                session.add(Alert(**create_test_alert(emotion="angry", create_rule=True, session=session)))
            for _ in range(3):
                session.add(Alert(**create_test_alert(emotion="sad", create_rule=True, session=session)))
            for _ in range(2):
                session.add(Alert(**create_test_alert(emotion="happy", create_rule=True, session=session)))
        
        emotions = await db_manager.get_emotion_triggers()
        assert emotions["angry"] == 5
        assert emotions["sad"] == 3
        assert emotions["happy"] == 2
    
    @pytest.mark.asyncio
    async def test_emotion_triggers_filter_camera(self, db_manager, clean_alerts):
        """Test emotion triggers filtered by camera."""
        # Insert alerts for different cameras
        async with db_manager.get_session() as session:
            for _ in range(4):
                session.add(Alert(**create_test_alert(emotion="angry", camera_id=CAMERA_1_UUID, create_rule=True, session=session)))
            for _ in range(2):
                session.add(Alert(**create_test_alert(emotion="happy", camera_id=CAMERA_2_UUID, create_rule=True, session=session)))
        
        # Query camera-1 only
        emotions = await db_manager.get_emotion_triggers(camera_id=CAMERA_1_UUID)
        assert emotions.get("angry", 0) == 4
        assert emotions.get("happy", 0) == 0
    
    @pytest.mark.asyncio
    async def test_emotion_triggers_ignores_null(self, db_manager, clean_alerts):
        """Test emotion triggers ignores null emotions."""
        # Insert alerts with and without emotions
        async with db_manager.get_session() as session:
            for _ in range(3):
                alert_data = create_test_alert(emotion="angry", create_rule=True, session=session)
                session.add(Alert(**alert_data))
            
            # Alert with null emotion
            alert_data = create_test_alert(create_rule=True, session=session)
            alert_data["emotion"] = None
            session.add(Alert(**alert_data))
        
        emotions = await db_manager.get_emotion_triggers()
        assert emotions["angry"] == 3
        assert len(emotions) == 1  # Only one emotion type


class TestRetentionCleanup:
    """Test cleanup_old_alerts retention policy."""
    
    @pytest.mark.asyncio
    async def test_cleanup_no_old_alerts(self, db_manager, clean_alerts):
        """Test cleanup with no old alerts."""
        # Insert recent alert
        async with db_manager.get_session() as session:
            session.add(Alert(**create_test_alert(create_rule=True, session=session)))
        
        # Cleanup should delete nothing
        deleted = await db_manager.cleanup_old_alerts(days=30)
        assert deleted == 0
        
        # Alert should still exist
        alerts = await db_manager.get_alerts()
        assert len(alerts) == 1
    
    @pytest.mark.asyncio
    async def test_cleanup_old_alerts(self, db_manager, clean_alerts):
        """Test cleanup deletes alerts older than retention period."""
        now = datetime.utcnow()
        old_date = now - timedelta(days=31)
        
        # Insert old and recent alerts
        async with db_manager.get_session() as session:
            session.add(Alert(**create_test_alert(triggered_at=old_date, create_rule=True, session=session)))
            session.add(Alert(**create_test_alert(triggered_at=now, create_rule=True, session=session)))
        
        # Cleanup 30-day retention
        deleted = await db_manager.cleanup_old_alerts(days=30)
        assert deleted == 1
        
        # Only recent alert should remain
        alerts = await db_manager.get_alerts()
        assert len(alerts) == 1


class TestPerformance:
    """Test query performance with large dataset."""
    
    @pytest.mark.asyncio
    async def test_query_performance_100_alerts(self, db_manager, clean_alerts):
        """Test query performance with 100+ alerts."""
        import time
        
        # Use the standard camera UUIDs from fixture
        camera_uuids = [CAMERA_1_UUID, CAMERA_2_UUID, CAMERA_1_UUID]  # Reuse existing cameras
        
        # Insert 150 test alerts
        async with db_manager.get_session() as session:
            for i in range(150):
                alert = Alert(**create_test_alert(
                    camera_id=camera_uuids[i % 3],
                    emotion=["happy", "sad", "angry"][i % 3],
                    severity=["info", "warning", "critical"][i % 3],
                    create_rule=True,
                    session=session
                ))
                session.add(alert)
        
        # Test get_alerts performance
        start = time.time()
        alerts = await db_manager.get_alerts(limit=100)
        duration_ms = (time.time() - start) * 1000
        
        assert len(alerts) == 100
        assert duration_ms < 100  # Should complete in < 100ms
        
        # Test severity_distribution performance
        start = time.time()
        dist = await db_manager.get_severity_distribution()
        duration_ms = (time.time() - start) * 1000
        
        assert dist["total"] == 150
        assert duration_ms < 100
        
        # Test top_rules performance
        start = time.time()
        rules = await db_manager.get_top_rules()
        duration_ms = (time.time() - start) * 1000
        
        assert len(rules) > 0
        assert duration_ms < 100
        
        # Test emotion_triggers performance
        start = time.time()
        emotions = await db_manager.get_emotion_triggers()
        duration_ms = (time.time() - start) * 1000
        
        assert len(emotions) == 3
        assert duration_ms < 100


class TestAggregation:
    """Test alert metrics aggregation."""
    
    @pytest.mark.skip(reason="Database function aggregate_alert_metrics() not implemented yet")
    @pytest.mark.asyncio
    async def test_aggregate_alert_metrics(self, db_manager, clean_alerts):
        """Test aggregating alerts into metrics table."""
        now = datetime.utcnow()
        target_hour = now.replace(minute=0, second=0, microsecond=0)
        
        # Insert alerts for this hour
        async with db_manager.get_session() as session:
            for _ in range(3):
                session.add(Alert(**create_test_alert(
                    triggered_at=target_hour + timedelta(minutes=10),
                    severity="info",
                    emotion="happy",
                    create_rule=True,
                    session=session
                )))
            for _ in range(2):
                session.add(Alert(**create_test_alert(
                    triggered_at=target_hour + timedelta(minutes=20),
                    severity="warning",
                    emotion="angry",
                    create_rule=True,
                    session=session
                )))
        
        # Aggregate
        success = await db_manager.aggregate_alert_metrics(target_hour)
        assert success is True
