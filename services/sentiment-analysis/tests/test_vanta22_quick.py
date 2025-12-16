"""Quick validation test for VANTA-22 core functionality."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import asyncio
from datetime import datetime
import uuid
from sqlalchemy import text

from app.database import DatabaseManager, Alert, Rule


@pytest.fixture
async def db_manager():
    """Create database manager for testing."""
    manager = DatabaseManager()
    await manager.connect()
    yield manager
    await manager.disconnect()


@pytest.mark.asyncio
async def test_vanta22_basic_workflow(db_manager):
    """Test complete VANTA-22 workflow: create rule, create alerts, query."""
    # Clean up
    async with db_manager.get_session() as session:
        await session.execute(text("DELETE FROM alerts"))
        await session.execute(text("DELETE FROM rules"))
    
    # Create test rule
    test_rule_id = str(uuid.uuid4())
    async with db_manager.get_session() as session:
        rule = Rule(
            id=test_rule_id,
            name="Test Rule",
            type="sentiment",
            condition_json={"test": True},
            action="log",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        session.add(rule)
    
    # Create test alerts
    async with db_manager.get_session() as session:
        for i, severity in enumerate(["info", "warning", "critical"]):
            alert = Alert(
                id=str(uuid.uuid4()),
                rule_id=test_rule_id,
                alert_type="rule_trigger",
                emotion="happy",
                message=f"Test alert {i}",
                severity=severity,
                triggered_at=datetime.utcnow()
            )
            session.add(alert)
    
    # Test get_alerts
    alerts = await db_manager.get_alerts(limit=10)
    assert len(alerts) == 3, f"Expected 3 alerts, got {len(alerts)}"
    
    # Test get_severity_distribution
    distribution = await db_manager.get_severity_distribution()
    assert "info" in distribution
    assert "warning" in distribution
    assert "critical" in distribution
    assert distribution["info"] == 1
    assert distribution["warning"] == 1
    assert distribution["critical"] == 1
    
    print("✅ VANTA-22 Core Functionality Verified!")
    print(f"✅ Alerts Created: {len(alerts)}")
    print(f"✅ Severity Distribution: {distribution}")
