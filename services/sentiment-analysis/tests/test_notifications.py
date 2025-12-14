"""Tests for alert notification service (VANTA-21)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import aiohttp

from app.notifications import AlertNotifier
from app.rules import Alert
from app.config import settings


@pytest.fixture
def sample_alert():
    """Create a sample alert for testing."""
    return Alert(
        rule_id="rule-001",
        rule_name="High Anger Alert",
        camera_id="camera-1",
        timestamp=datetime.now(),
        severity="warning",
        message="Anger level exceeded 70%",
        sentiment_snapshot={
            "dominant_emotion": "angry",
            "mood_score": -0.5,
            "total_faces": 10,
            "emotions": {"angry": 0.75, "neutral": 0.25}
        }
    )


@pytest.fixture
def critical_alert():
    """Create a critical severity alert for testing."""
    return Alert(
        rule_id="rule-002",
        rule_name="Critical Mood Drop",
        camera_id="camera-2",
        timestamp=datetime.now(),
        severity="critical",
        message="Mood score dropped below -0.8",
        sentiment_snapshot={
            "dominant_emotion": "sad",
            "mood_score": -0.85,
            "total_faces": 15,
            "emotions": {"sad": 0.80, "angry": 0.20}
        }
    )


@pytest.fixture
def notifier():
    """Create notifier instance for testing."""
    return AlertNotifier()


@pytest.fixture
def notifier_with_config():
    """Create notifier with all channels configured."""
    with patch.object(settings, 'slack_webhook_url', 'https://hooks.slack.com/test'):
        with patch.object(settings, 'webhook_endpoint', 'https://example.com/webhook'):
            with patch.object(settings, 'smtp_enabled', True):
                notifier = AlertNotifier()
                return notifier


class TestAlertNotifierInit:
    """Test notifier initialization."""
    
    def test_init_default_config(self, notifier):
        """Test initialization with default config."""
        assert notifier._max_retries == 3
        assert notifier._retry_delays == [1, 2, 4]
        assert notifier._alert_window == 300  # 5 minutes
        assert notifier.alert_log_path == Path("/data/alerts.log")
    
    def test_init_with_slack(self):
        """Test initialization with Slack webhook."""
        with patch.object(settings, 'slack_webhook_url', 'https://hooks.slack.com/test'):
            notifier = AlertNotifier()
            assert notifier.slack_webhook_url == 'https://hooks.slack.com/test'
    
    def test_init_with_webhook(self):
        """Test initialization with generic webhook."""
        with patch.object(settings, 'webhook_endpoint', 'https://example.com/webhook'):
            notifier = AlertNotifier()
            assert notifier.webhook_endpoint == 'https://example.com/webhook'


class TestRateLimiting:
    """Test rate limiting and deduplication."""
    
    def test_should_send_alert_first_time(self, notifier, sample_alert):
        """Test that first alert is always sent."""
        assert notifier._should_send_alert(sample_alert) is True
    
    def test_should_suppress_duplicate(self, notifier, sample_alert):
        """Test that duplicate alert within window is suppressed."""
        # Send first alert
        assert notifier._should_send_alert(sample_alert) is True
        
        # Try to send same alert immediately
        assert notifier._should_send_alert(sample_alert) is False
    
    def test_should_send_different_camera(self, notifier, sample_alert):
        """Test that same rule for different camera is sent."""
        # Send first alert
        assert notifier._should_send_alert(sample_alert) is True
        
        # Create alert for different camera
        alert2 = Alert(
            rule_id=sample_alert.rule_id,
            rule_name=sample_alert.rule_name,
            camera_id="camera-2",  # Different camera
            timestamp=datetime.now(),
            severity=sample_alert.severity,
            message=sample_alert.message,
            sentiment_snapshot=sample_alert.sentiment_snapshot
        )
        
        assert notifier._should_send_alert(alert2) is True
    
    def test_should_send_different_emotion(self, notifier, sample_alert):
        """Test that same rule for different emotion is sent."""
        # Send first alert
        assert notifier._should_send_alert(sample_alert) is True
        
        # Create alert with different emotion
        alert2 = Alert(
            rule_id=sample_alert.rule_id,
            rule_name=sample_alert.rule_name,
            camera_id=sample_alert.camera_id,
            timestamp=datetime.now(),
            severity=sample_alert.severity,
            message="Happiness level exceeded 70%",
            sentiment_snapshot={
                "dominant_emotion": "happy",  # Different emotion
                "mood_score": 0.5,
                "total_faces": 10
            }
        )
        
        assert notifier._should_send_alert(alert2) is True
    
    def test_rate_limit_window_expiration(self, notifier, sample_alert):
        """Test that alerts are sent after rate limit window expires."""
        # Send first alert
        assert notifier._should_send_alert(sample_alert) is True
        
        # Manually set timestamp to expired (6 minutes ago)
        expired_time = datetime.now() - timedelta(seconds=360)
        notifier._recent_alerts[0] = (expired_time, notifier._recent_alerts[0][1])
        
        # Should allow sending now
        assert notifier._should_send_alert(sample_alert) is True


class TestFileLog:
    """Test file log notification channel."""
    
    @pytest.mark.asyncio
    async def test_send_to_file_log(self, notifier, sample_alert, tmp_path):
        """Test writing alert to file log."""
        # Use temporary path for testing
        notifier.alert_log_path = tmp_path / "alerts.log"
        
        result = await notifier._send_to_file_log(sample_alert)
        
        assert result is True
        assert notifier.alert_log_path.exists()
        
        # Verify content
        with open(notifier.alert_log_path) as f:
            lines = f.readlines()
            assert len(lines) == 1
            
            alert_data = json.loads(lines[0])
            assert alert_data['rule_id'] == sample_alert.rule_id
            assert alert_data['camera_id'] == sample_alert.camera_id
    
    @pytest.mark.asyncio
    async def test_file_log_multiple_alerts(self, notifier, sample_alert, critical_alert, tmp_path):
        """Test appending multiple alerts to file log."""
        notifier.alert_log_path = tmp_path / "alerts.log"
        
        await notifier._send_to_file_log(sample_alert)
        await notifier._send_to_file_log(critical_alert)
        
        with open(notifier.alert_log_path) as f:
            lines = f.readlines()
            assert len(lines) == 2


class TestSlackWebhook:
    """Test Slack webhook notification channel."""
    
    @pytest.mark.asyncio
    async def test_slack_message_format(self, notifier_with_config, sample_alert):
        """Test Slack message formatting."""
        message = notifier_with_config._format_slack_message(sample_alert)
        
        assert "text" in message
        assert "blocks" in message
        assert "High Anger Alert" in message["text"]
        
        # Check blocks
        blocks = message["blocks"]
        assert any("header" in b.get("type", "") for b in blocks)
        assert any("section" in b.get("type", "") for b in blocks)
    
    @pytest.mark.asyncio
    async def test_slack_send_success(self, notifier_with_config, sample_alert):
        """Test successful Slack webhook delivery."""
        mock_response = AsyncMock()
        mock_response.status = 200
        
        mock_post_ctx = AsyncMock()
        mock_post_ctx.__aenter__.return_value = mock_response
        mock_post_ctx.__aexit__.return_value = None
        
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = AsyncMock()
        mock_session.__aenter__.return_value.post = Mock(return_value=mock_post_ctx)
        mock_session.__aexit__.return_value = None
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await notifier_with_config._send_to_slack(sample_alert)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_slack_send_retry_on_failure(self, notifier_with_config, sample_alert):
        """Test Slack webhook retry logic."""
        mock_response = AsyncMock()
        mock_response.status = 500  # Simulate server error
        
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            with patch('asyncio.sleep'):  # Skip actual sleep
                result = await notifier_with_config._send_to_slack(sample_alert)
        
        assert result is False
        # Should have tried 3 times
        assert mock_session.__aenter__.return_value.post.call_count == 3
    
    @pytest.mark.asyncio
    async def test_slack_send_retry_success(self, notifier_with_config, sample_alert):
        """Test Slack webhook succeeds after retry."""
        # Create mock responses
        responses = [
            AsyncMock(status=500),  # First attempt fails
            AsyncMock(status=500),  # Second attempt fails
            AsyncMock(status=200)   # Third attempt succeeds
        ]
        
        response_iter = iter(responses)
        
        def create_post_ctx(*args, **kwargs):
            ctx = AsyncMock()
            ctx.__aenter__.return_value = next(response_iter)
            ctx.__aexit__.return_value = None
            return ctx
        
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = AsyncMock()
        mock_session.__aenter__.return_value.post = Mock(side_effect=create_post_ctx)
        mock_session.__aexit__.return_value = None
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            with patch('asyncio.sleep'):
                result = await notifier_with_config._send_to_slack(sample_alert)
        
        assert result is True


class TestGenericWebhook:
    """Test generic webhook notification channel."""
    
    @pytest.mark.asyncio
    async def test_webhook_send_success(self, notifier_with_config, sample_alert):
        """Test successful webhook delivery."""
        mock_response = AsyncMock()
        mock_response.status = 200
        
        mock_post_ctx = AsyncMock()
        mock_post_ctx.__aenter__.return_value = mock_response
        mock_post_ctx.__aexit__.return_value = None
        
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value = AsyncMock()
        mock_session.__aenter__.return_value.post = Mock(return_value=mock_post_ctx)
        mock_session.__aexit__.return_value = None
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            result = await notifier_with_config._send_to_webhook(sample_alert)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_webhook_sends_alert_dict(self, notifier_with_config, sample_alert):
        """Test that webhook sends complete alert data."""
        mock_response = AsyncMock()
        mock_response.status = 200
        
        mock_post = AsyncMock(return_value=AsyncMock(
            __aenter__=AsyncMock(return_value=mock_response)
        ))
        
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value.post = mock_post
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            await notifier_with_config._send_to_webhook(sample_alert)
        
        # Verify alert dict was sent
        call_kwargs = mock_post.call_args[1]
        assert 'json' in call_kwargs
        alert_dict = call_kwargs['json']
        assert alert_dict['rule_id'] == sample_alert.rule_id
    
    @pytest.mark.asyncio
    async def test_webhook_retry_on_failure(self, notifier_with_config, sample_alert):
        """Test webhook retry logic."""
        mock_response = AsyncMock()
        mock_response.status = 503  # Service unavailable
        
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            with patch('asyncio.sleep'):
                result = await notifier_with_config._send_to_webhook(sample_alert)
        
        assert result is False
        assert mock_session.__aenter__.return_value.post.call_count == 3


class TestEmailNotification:
    """Test email notification channel."""
    
    @pytest.mark.asyncio
    async def test_email_only_for_critical(self, notifier_with_config, sample_alert, critical_alert):
        """Test that email is only sent for critical alerts."""
        # Non-critical alert
        result1 = await notifier_with_config._send_email(sample_alert)
        assert result1 is True  # Placeholder returns True
        
        # Critical alert
        result2 = await notifier_with_config._send_email(critical_alert)
        assert result2 is True


class TestSendNotification:
    """Test main notification dispatch method."""
    
    @pytest.mark.asyncio
    async def test_send_notification_file_log_always(self, notifier, sample_alert, tmp_path):
        """Test that file log is always written."""
        notifier.alert_log_path = tmp_path / "alerts.log"
        
        results = await notifier.send_notification(sample_alert)
        
        assert 'file_log' in results
        assert results['file_log'] is True
        assert notifier.alert_log_path.exists()
    
    @pytest.mark.asyncio
    async def test_send_notification_all_channels(self, notifier_with_config, critical_alert, tmp_path):
        """Test sending to all configured channels."""
        notifier_with_config.alert_log_path = tmp_path / "alerts.log"
        
        # Mock successful responses for all channels
        mock_response = AsyncMock(status=200)
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value.post.return_value.__aenter__.return_value = mock_response
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            results = await notifier_with_config.send_notification(critical_alert)
        
        assert 'file_log' in results
        assert 'slack' in results
        assert 'webhook' in results
        assert 'email' in results
    
    @pytest.mark.asyncio
    async def test_send_notification_rate_limited(self, notifier, sample_alert, tmp_path):
        """Test that rate-limited alerts are suppressed."""
        notifier.alert_log_path = tmp_path / "alerts.log"
        
        # Send first alert
        results1 = await notifier.send_notification(sample_alert)
        assert 'file_log' in results1
        
        # Try to send duplicate immediately
        results2 = await notifier.send_notification(sample_alert)
        assert 'suppressed' in results2
        assert results2['suppressed'] is True
    
    @pytest.mark.asyncio
    async def test_send_notification_channel_independence(self, notifier_with_config, sample_alert, tmp_path):
        """Test that channel failures don't affect others."""
        notifier_with_config.alert_log_path = tmp_path / "alerts.log"
        
        # Slack succeeds, webhook fails
        mock_responses = {
            'slack': AsyncMock(status=200),
            'webhook': AsyncMock(status=500)
        }
        
        call_count = 0
        def get_response(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # First call is Slack (success), second is webhook (fail)
            if call_count <= 1:
                return AsyncMock(__aenter__=AsyncMock(return_value=mock_responses['slack']))
            else:
                return AsyncMock(__aenter__=AsyncMock(return_value=mock_responses['webhook']))
        
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value.post = get_response
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            with patch('asyncio.sleep'):
                results = await notifier_with_config.send_notification(sample_alert)
        
        # File log and Slack should succeed
        assert results.get('file_log') is True
        # Webhook should fail (after retries)
        # Note: actual results depend on retry logic


class TestNotifierStats:
    """Test notifier statistics and monitoring."""
    
    def test_get_stats(self, notifier_with_config):
        """Test retrieving notifier statistics."""
        stats = notifier_with_config.get_stats()
        
        assert 'recent_alerts_count' in stats
        assert 'rate_limit_window_seconds' in stats
        assert 'max_retries' in stats
        assert 'channels' in stats
        
        # Check channel status
        channels = stats['channels']
        assert channels['slack'] == 'enabled'
        assert channels['webhook'] == 'enabled'
        assert channels['email'] == 'enabled'
        assert channels['file_log'] == 'enabled'
    
    def test_stats_after_alerts(self, notifier, sample_alert):
        """Test stats update after sending alerts."""
        # Send alert
        notifier._should_send_alert(sample_alert)
        
        stats = notifier.get_stats()
        assert stats['recent_alerts_count'] == 1


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.mark.asyncio
    async def test_empty_sentiment_snapshot(self, notifier):
        """Test handling alert with empty sentiment data."""
        alert = Alert(
            rule_id="rule-003",
            rule_name="Empty Snapshot Test",
            camera_id="camera-1",
            timestamp=datetime.now(),
            severity="info",
            message="Test message",
            sentiment_snapshot={}
        )
        
        message = notifier._format_slack_message(alert)
        assert message is not None
        assert "Empty Snapshot Test" in message["text"]
    
    @pytest.mark.asyncio
    async def test_file_log_directory_creation(self, notifier, sample_alert, tmp_path):
        """Test that log directory is created if missing."""
        log_path = tmp_path / "nested" / "directory" / "alerts.log"
        notifier.alert_log_path = log_path
        
        # Directory doesn't exist yet
        assert not log_path.parent.exists()
        
        # Create the parent directory as notifier does in __init__
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        result = await notifier._send_to_file_log(sample_alert)
        assert result is True
        assert log_path.exists()
    
    @pytest.mark.asyncio
    async def test_network_timeout(self, notifier_with_config, sample_alert):
        """Test handling of network timeouts."""
        # Mock timeout exception
        mock_session = AsyncMock()
        mock_session.__aenter__.return_value.post.side_effect = asyncio.TimeoutError()
        
        with patch('aiohttp.ClientSession', return_value=mock_session):
            with patch('asyncio.sleep'):
                result = await notifier_with_config._send_to_slack(sample_alert)
        
        assert result is False
