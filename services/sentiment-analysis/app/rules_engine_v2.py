"""Rules engine with registry and evaluation pipeline for VANTA-19."""
import logging
import time
from typing import Dict, List, Optional, Type
from datetime import datetime

from .rules import Rule, Alert, ThresholdRule, TrendRule, DurationRule
from .models import CrowdSentiment
from .database import DatabaseManager

logger = logging.getLogger(__name__)


class RuleRegistry:
    """Registry for rule types supporting extensibility."""
    
    def __init__(self):
        """Initialize rule registry."""
        self._rule_types: Dict[str, Type[Rule]] = {}
        
        # Register built-in rule types
        self.register("threshold", ThresholdRule)
        self.register("trend", TrendRule)
        self.register("duration", DurationRule)
    
    def register(self, rule_type: str, rule_class: Type[Rule]) -> None:
        """
        Register a new rule type.
        
        Args:
            rule_type: Type identifier (e.g., "threshold")
            rule_class: Rule class that extends Rule ABC
        """
        self._rule_types[rule_type] = rule_class
        logger.info(f"Registered rule type: {rule_type} -> {rule_class.__name__}")
    
    def get(self, rule_type: str) -> Optional[Type[Rule]]:
        """
        Get rule class by type.
        
        Args:
            rule_type: Type identifier
            
        Returns:
            Rule class or None if not found
        """
        return self._rule_types.get(rule_type)
    
    def list_types(self) -> List[str]:
        """
        List all registered rule types.
        
        Returns:
            List of rule type identifiers
        """
        return list(self._rule_types.keys())


class RulesEngineV2:
    """Rules engine with strategy pattern and extensibility (VANTA-19)."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize rules engine.
        
        Args:
            db_manager: Database manager for loading rules
        """
        self.db_manager = db_manager
        self.registry = RuleRegistry()
        
        # Active rules
        self.rules: List[Rule] = []
        
        # Metrics
        self.rules_evaluated_total = 0
        self.rules_triggered_total = 0
        self.evaluation_errors = 0
        
        # Alert queue (in-memory backup if DB fails)
        self._alert_queue: List[Alert] = []
        self._max_queue_size = 1000
    
    async def load_rules(self) -> None:
        """
        Load all enabled rules from database.
        
        Parses rule configs and instantiates appropriate rule objects.
        """
        if not self.db_manager:
            logger.warning("No database manager, loading default rules")
            self._load_default_rules()
            return
        
        try:
            # Get rules from database
            db_rules = await self.db_manager.get_rules()
            
            loaded_rules = []
            for db_rule in db_rules:
                if not db_rule.enabled:
                    continue
                
                try:
                    # Parse rule config
                    rule = self._parse_rule(db_rule)
                    if rule:
                        loaded_rules.append(rule)
                except Exception as e:
                    logger.error(
                        f"Invalid rule config for {db_rule.rule_id}: {e}. Skipping."
                    )
            
            self.rules = loaded_rules
            logger.info(f"Loaded {len(self.rules)} rules from database")
            
        except Exception as e:
            logger.error(f"Error loading rules from database: {e}")
            self._load_default_rules()
    
    def _parse_rule(self, db_rule) -> Optional[Rule]:
        """
        Parse database rule into Rule object.
        
        Args:
            db_rule: Database rule record
            
        Returns:
            Rule instance or None if parsing fails
        """
        # Parse condition as rule type and config
        # Expected format: "type:config_json" or just condition string
        condition = db_rule.condition
        
        # Try to parse as "type:config" format
        if ":" in condition:
            rule_type, config_str = condition.split(":", 1)
            rule_class = self.registry.get(rule_type)
            
            if not rule_class:
                logger.warning(f"Unknown rule type: {rule_type}")
                return None
            
            # Parse config (JSON-like format)
            import json
            try:
                config = json.loads(config_str)
            except json.JSONDecodeError:
                logger.error(f"Invalid rule config JSON: {config_str}")
                return None
            
            # Instantiate rule
            return rule_class(
                rule_id=db_rule.rule_id,
                name=db_rule.name,
                enabled=db_rule.enabled,
                priority=db_rule.priority,
                **config
            )
        
        # Fallback: try to infer rule type from condition
        logger.debug(f"Could not parse rule type from condition: {condition}")
        return None
    
    def _load_default_rules(self) -> None:
        """Load default rules for testing."""
        self.rules = [
            ThresholdRule(
                rule_id="high_happy_threshold",
                name="High Happiness Alert",
                emotion="happy",
                threshold=0.8,
                action="show_promotional_content",
                priority=5
            ),
            TrendRule(
                rule_id="declining_mood_alert",
                name="Declining Mood Alert",
                direction="declining",
                min_magnitude=0.15,
                action="alert_staff",
                priority=10
            ),
            DurationRule(
                rule_id="sustained_anger_alert",
                name="Sustained Anger Alert",
                emotion="angry",
                threshold=0.5,
                duration_seconds=60,
                action="escalate_to_manager",
                priority=15
            )
        ]
        
        logger.info(f"Loaded {len(self.rules)} default rules")
    
    async def evaluate_all(self, sentiment: CrowdSentiment) -> List[Alert]:
        """
        Evaluate sentiment against all rules.
        
        Args:
            sentiment: Crowd sentiment to evaluate
            
        Returns:
            List of triggered alerts
        """
        alerts = []
        
        # Sort rules by priority (highest first)
        sorted_rules = sorted(self.rules, key=lambda r: r.priority, reverse=True)
        
        for rule in sorted_rules:
            try:
                start_time = time.time()
                
                # Evaluate rule
                alert = rule.evaluate(sentiment)
                
                evaluation_time_ms = (time.time() - start_time) * 1000
                self.rules_evaluated_total += 1
                
                if alert:
                    self.rules_triggered_total += 1
                    alerts.append(alert)
                    
                    logger.info(
                        f"Rule triggered: {rule.rule_id} | "
                        f"Camera: {sentiment.camera_id} | "
                        f"Severity: {alert.severity} | "
                        f"Eval time: {evaluation_time_ms:.2f}ms"
                    )
                else:
                    logger.debug(
                        f"Rule evaluated: {rule.rule_id} | "
                        f"Result: not triggered | "
                        f"Eval time: {evaluation_time_ms:.2f}ms"
                    )
            
            except Exception as e:
                self.evaluation_errors += 1
                logger.error(
                    f"Error evaluating rule {rule.rule_id}: {e}",
                    exc_info=True
                )
        
        return alerts
    
    async def store_alerts(self, alerts: List[Alert]) -> bool:
        """
        Store alerts to database.
        
        If database fails, queues alerts in memory.
        
        Args:
            alerts: List of alerts to store
            
        Returns:
            True if stored successfully
        """
        if not alerts:
            return True
        
        if not self.db_manager:
            logger.warning("No database manager, queueing alerts in memory")
            self._queue_alerts(alerts)
            return False
        
        try:
            # Store each alert
            for alert in alerts:
                await self.db_manager.save_alert(alert)
            
            logger.info(f"Stored {len(alerts)} alerts to database")
            return True
            
        except Exception as e:
            logger.error(f"Database connection failure, queueing alerts: {e}")
            self._queue_alerts(alerts)
            return False
    
    def _queue_alerts(self, alerts: List[Alert]) -> None:
        """
        Queue alerts in memory when database fails.
        
        Args:
            alerts: Alerts to queue
        """
        for alert in alerts:
            if len(self._alert_queue) >= self._max_queue_size:
                # Remove oldest alert
                self._alert_queue.pop(0)
                logger.warning("Alert queue full, dropping oldest alert")
            
            self._alert_queue.append(alert)
        
        logger.info(
            f"Queued {len(alerts)} alerts in memory. "
            f"Queue size: {len(self._alert_queue)}"
        )
    
    async def flush_alert_queue(self) -> int:
        """
        Attempt to flush queued alerts to database.
        
        Returns:
            Number of alerts flushed
        """
        if not self._alert_queue or not self.db_manager:
            return 0
        
        try:
            flushed = 0
            while self._alert_queue:
                alert = self._alert_queue.pop(0)
                await self.db_manager.save_alert(alert)
                flushed += 1
            
            logger.info(f"Flushed {flushed} queued alerts to database")
            return flushed
            
        except Exception as e:
            logger.error(f"Error flushing alert queue: {e}")
            return 0
    
    async def publish_alerts(self, alerts: List[Alert]) -> bool:
        """
        Publish alerts to notification service (placeholder).
        
        Args:
            alerts: Alerts to publish
            
        Returns:
            True if published successfully
        """
        # TODO: Implement Redis stream publishing in future sprint
        for alert in alerts:
            logger.info(
                f"[PUBLISH] Alert: {alert.rule_name} | "
                f"Camera: {alert.camera_id} | "
                f"Severity: {alert.severity}"
            )
        
        return True
    
    async def reload_rules(self) -> None:
        """Reload rules from database (event-driven)."""
        logger.info("Reloading rules...")
        await self.load_rules()
        logger.info(f"Rules reloaded. Active rules: {len(self.rules)}")
    
    def get_metrics(self) -> Dict[str, int]:
        """
        Get engine metrics.
        
        Returns:
            Dictionary with metrics
        """
        return {
            "total_rules": len(self.rules),
            "enabled_rules": len([r for r in self.rules if r.enabled]),
            "rules_evaluated_total": self.rules_evaluated_total,
            "rules_triggered_total": self.rules_triggered_total,
            "evaluation_errors": self.evaluation_errors,
            "queued_alerts": len(self._alert_queue),
            "registered_rule_types": len(self.registry.list_types())
        }
