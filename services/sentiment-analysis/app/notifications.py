"""Alert notification service with multi-channel support (VANTA-21)."""
import logging
import json
import time
import asyncio
from typing import Optional, Dict, Set, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import aiohttp
from collections import deque

from .rules import Alert
from .config import settings

logger = logging.getLogger(__name__)


class AlertNotifier:
    """Multi-channel alert notification service with retry and rate limiting."""
    
    def __init__(self):
        """Initialize notification service."""
        # Rate limiting: track recent alerts to prevent duplicates
        self._recent_alerts: deque = deque(maxlen=1000)
        self._alert_window = 300  # 5 minutes in seconds
        
        # Retry configuration
        self._max_retries = 3
        self._retry_delays = [1, 2, 4]  # Exponential backoff: 1s, 2s, 4s
        
        # Notification channels config
        self.slack_webhook_url = getattr(settings, 'slack_webhook_url', None)
        self.webhook_endpoint = getattr(settings, 'webhook_endpoint', None)
        self.smtp_enabled = getattr(settings, 'smtp_enabled', False)
        
        # File log path
        self.alert_log_path = Path("/data/alerts.log")
        self.alert_log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            f"AlertNotifier initialized: "
            f"Slack={'enabled' if self.slack_webhook_url else 'disabled'}, "
            f"Webhook={'enabled' if self.webhook_endpoint else 'disabled'}, "
            f"SMTP={'enabled' if self.smtp_enabled else 'disabled'}"
        )
    
    def _should_send_alert(self, alert: Alert) -> bool:
        """
        Check if alert should be sent (rate limiting).
        
        Prevents duplicate alerts within 5 minutes based on:
        (rule_id, camera_id, emotion)
        
        Args:
            alert: Alert to check
            
        Returns:
            True if alert should be sent
        """
        # Create deduplication key
        emotion = alert.sentiment_snapshot.get('dominant_emotion', 'unknown')
        dedup_key = (alert.rule_id, alert.camera_id, emotion)
        
        # Clean old entries (older than 5 minutes)
        now = datetime.now()
        cutoff = now - timedelta(seconds=self._alert_window)
        
        # Remove expired entries
        while self._recent_alerts and self._recent_alerts[0][0] < cutoff:
            self._recent_alerts.popleft()
        
        # Check if this alert key exists in recent window
        for timestamp, key in self._recent_alerts:
            if key == dedup_key:
                logger.debug(
                    f"Alert suppressed (rate limit): {alert.rule_name} "
                    f"for {alert.camera_id}, {emotion}"
                )
                return False
        
        # Add to recent alerts
        self._recent_alerts.append((now, dedup_key))
        return True
    
    async def send_notification(self, alert: Alert) -> Dict[str, bool]:
        """
        Send alert to all configured channels.
        
        Args:
            alert: Alert to send
            
        Returns:
            Dict mapping channel name to success status
        """
        # Rate limiting check
        if not self._should_send_alert(alert):
            return {"suppressed": True}
        
        results = {}
        
        # Always log to file (development/testing)
        results['file_log'] = await self._send_to_file_log(alert)
        
        # Slack webhook
        if self.slack_webhook_url:
            results['slack'] = await self._send_to_slack(alert)
        
        # Generic webhook
        if self.webhook_endpoint:
            results['webhook'] = await self._send_to_webhook(alert)
        
        # Email (only for critical alerts)
        if self.smtp_enabled and alert.severity == "critical":
            results['email'] = await self._send_email(alert)
        
        # Log results
        success_count = sum(1 for v in results.values() if v)
        logger.info(
            f"Alert notification sent: {alert.rule_name} | "
            f"Camera: {alert.camera_id} | "
            f"Severity: {alert.severity} | "
            f"Channels: {success_count}/{len(results)} successful"
        )
        
        return results
    
    async def _send_to_file_log(self, alert: Alert) -> bool:
        """
        Write alert to local file log.
        
        Args:
            alert: Alert to log
            
        Returns:
            True if successful
        """
        try:
            alert_json = json.dumps(alert.to_dict())
            
            with open(self.alert_log_path, 'a') as f:
                f.write(alert_json + '\n')
            
            logger.debug(f"Alert logged to {self.alert_log_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write alert to file: {e}")
            return False
    
    async def _send_to_slack(self, alert: Alert) -> bool:
        """
        Send alert to Slack webhook with retry.
        
        Args:
            alert: Alert to send
            
        Returns:
            True if successful
        """
        # Format Slack message
        message = self._format_slack_message(alert)
        
        # Retry logic
        for attempt in range(self._max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.slack_webhook_url,
                        json=message,
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            logger.debug(f"Slack notification sent: {alert.rule_name}")
                            return True
                        else:
                            logger.warning(
                                f"Slack webhook returned {response.status}, "
                                f"attempt {attempt + 1}/{self._max_retries}"
                            )
            
            except Exception as e:
                logger.error(
                    f"Slack notification failed (attempt {attempt + 1}/{self._max_retries}): {e}"
                )
            
            # Exponential backoff
            if attempt < self._max_retries - 1:
                await asyncio.sleep(self._retry_delays[attempt])
        
        logger.error(f"Slack notification failed after {self._max_retries} attempts")
        return False
    
    def _format_slack_message(self, alert: Alert) -> dict:
        """
        Format alert as Slack message.
        
        Args:
            alert: Alert to format
            
        Returns:
            Slack message payload
        """
        # Emoji for severity
        severity_emoji = {
            "info": "ℹ️",
            "warning": "⚠️",
            "critical": "🚨"
        }
        
        emoji = severity_emoji.get(alert.severity, "📢")
        
        # Format emotion data
        emotion_data = alert.sentiment_snapshot
        mood_score = emotion_data.get('mood_score', 0)
        dominant_emotion = emotion_data.get('dominant_emotion', 'unknown')
        total_faces = emotion_data.get('total_faces', 0)
        
        return {
            "text": f"{emoji} *{alert.rule_name}*",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": f"{emoji} {alert.rule_name}"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Camera:*\n{alert.camera_id}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Severity:*\n{alert.severity.upper()}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Emotion:*\n{dominant_emotion}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Mood Score:*\n{mood_score:.2f}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Faces:*\n{total_faces}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Time:*\n{alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*Message:*\n{alert.message}"
                    }
                }
            ]
        }
    
    async def _send_to_webhook(self, alert: Alert) -> bool:
        """
        Send alert to generic webhook with retry.
        
        Args:
            alert: Alert to send
            
        Returns:
            True if successful
        """
        # Retry logic
        for attempt in range(self._max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.webhook_endpoint,
                        json=alert.to_dict(),
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if 200 <= response.status < 300:
                            logger.debug(f"Webhook notification sent: {alert.rule_name}")
                            return True
                        else:
                            logger.warning(
                                f"Webhook returned {response.status}, "
                                f"attempt {attempt + 1}/{self._max_retries}"
                            )
            
            except Exception as e:
                logger.error(
                    f"Webhook notification failed (attempt {attempt + 1}/{self._max_retries}): {e}"
                )
            
            # Exponential backoff
            if attempt < self._max_retries - 1:
                await asyncio.sleep(self._retry_delays[attempt])
        
        logger.error(f"Webhook notification failed after {self._max_retries} attempts")
        return False
    
    async def _send_email(self, alert: Alert) -> bool:
        """
        Send alert via email (placeholder for future implementation).
        
        Args:
            alert: Alert to send
            
        Returns:
            True if successful
        """
        # TODO: Implement SMTP email sending
        # For now, just log that it would be sent
        logger.info(f"Email notification (not implemented): {alert.rule_name}")
        return True
    
    def get_stats(self) -> dict:
        """
        Get notification service statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            "recent_alerts_count": len(self._recent_alerts),
            "rate_limit_window_seconds": self._alert_window,
            "max_retries": self._max_retries,
            "channels": {
                "slack": "enabled" if self.slack_webhook_url else "disabled",
                "webhook": "enabled" if self.webhook_endpoint else "disabled",
                "email": "enabled" if self.smtp_enabled else "disabled",
                "file_log": "enabled"
            }
        }
