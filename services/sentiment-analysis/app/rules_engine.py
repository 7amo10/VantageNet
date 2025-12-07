"""Rules engine scaffold for sentiment evaluation."""
import logging
import json
from typing import List, Optional
from pathlib import Path

from .config import settings
from .models import RuleDefinition, SentimentResult

logger = logging.getLogger(__name__)


class RulesEngine:
    """Rules engine for evaluating sentiment against defined rules."""
    
    def __init__(self):
        """Initialize rules engine."""
        self.rules: List[RuleDefinition] = []
        self._evaluations_count = 0
        
    async def load_rules_from_file(self) -> None:
        """
        Load rules from configuration file.
        
        For Sprint 1, this is a scaffold - actual rules loading will be
        implemented in Sprint 2.
        """
        config_path = Path(settings.rules_config_path)
        
        if not config_path.exists():
            logger.info(f"Rules config file not found at {config_path}, using defaults")
            self._load_default_rules()
            return
        
        try:
            with open(config_path, 'r') as f:
                rules_data = json.load(f)
            
            self.rules = [RuleDefinition(**rule) for rule in rules_data.get("rules", [])]
            logger.info(f"Loaded {len(self.rules)} rules from {config_path}")
            
        except Exception as e:
            logger.error(f"Error loading rules from file: {e}")
            self._load_default_rules()
    
    async def load_rules_from_database(self, db_manager) -> None:
        """
        Load rules from PostgreSQL database.
        
        Args:
            db_manager: DatabaseManager instance
        """
        try:
            db_rules = await db_manager.get_rules()
            
            self.rules = [
                RuleDefinition(
                    rule_id=rule.rule_id,
                    name=rule.name,
                    description=rule.description,
                    condition=rule.condition,
                    action=rule.action,
                    priority=rule.priority,
                    enabled=rule.enabled
                )
                for rule in db_rules
            ]
            
            logger.info(f"Loaded {len(self.rules)} rules from database")
            
        except Exception as e:
            logger.error(f"Error loading rules from database: {e}")
            self._load_default_rules()
    
    def _load_default_rules(self) -> None:
        """Load default rules for Sprint 1 scaffold."""
        self.rules = [
            RuleDefinition(
                rule_id="high_negative_sentiment",
                name="High Negative Sentiment Alert",
                description="Trigger when sentiment is very negative",
                condition="sentiment_score < -0.5 and confidence > 0.7",
                action="log_alert",
                priority=10,
                enabled=True
            ),
            RuleDefinition(
                rule_id="high_positive_sentiment",
                name="High Positive Sentiment",
                description="Trigger when sentiment is very positive",
                condition="sentiment_score > 0.6 and confidence > 0.7",
                action="log_info",
                priority=5,
                enabled=True
            ),
            RuleDefinition(
                rule_id="anger_detected",
                name="Anger Emotion Detected",
                description="Trigger when anger is dominant emotion",
                condition="dominant_emotion == 'angry'",
                action="log_warning",
                priority=8,
                enabled=True
            )
        ]
        
        logger.info(f"Loaded {len(self.rules)} default rules")
    
    async def evaluate(self, sentiment: SentimentResult) -> List[RuleDefinition]:
        """
        Evaluate sentiment against all rules.
        
        For Sprint 1, this is a scaffold that logs rule evaluations.
        Actual rule execution will be implemented in Sprint 2.
        
        Args:
            sentiment: Sentiment result to evaluate
            
        Returns:
            List[RuleDefinition]: Triggered rules
        """
        triggered_rules = []
        self._evaluations_count += 1
        
        # Create evaluation context
        context = {
            "sentiment_score": sentiment.sentiment_score,
            "dominant_emotion": sentiment.dominant_emotion,
            "confidence": sentiment.confidence,
            "total_faces": sentiment.total_faces
        }
        
        # Evaluate each rule
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            try:
                # Simple expression evaluation (Sprint 1 scaffold)
                if self._evaluate_condition(rule.condition, context):
                    triggered_rules.append(rule)
                    logger.info(
                        f"Rule triggered: {rule.name} | "
                        f"Action: {rule.action} | "
                        f"Sentiment: {sentiment.sentiment_score:.2f}"
                    )
                    
                    # Execute action (Sprint 1: log only)
                    await self._execute_action(rule, sentiment)
            
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.rule_id}: {e}")
        
        return triggered_rules
    
    def _evaluate_condition(self, condition: str, context: dict) -> bool:
        """
        Evaluate rule condition.
        
        For Sprint 1, this uses simple eval() for demonstration.
        Sprint 2 will implement a proper expression parser.
        
        Args:
            condition: Condition expression
            context: Evaluation context with variables
            
        Returns:
            bool: True if condition is met
        """
        try:
            # Replace variables in condition
            eval_expr = condition
            for var, value in context.items():
                if isinstance(value, str):
                    eval_expr = eval_expr.replace(var, f"'{value}'")
                else:
                    eval_expr = eval_expr.replace(var, str(value))
            
            # Evaluate (safe for Sprint 1 scaffold)
            result = eval(eval_expr)
            return bool(result)
            
        except Exception as e:
            logger.error(f"Error evaluating condition '{condition}': {e}")
            return False
    
    async def _execute_action(self, rule: RuleDefinition, sentiment: SentimentResult) -> None:
        """
        Execute rule action.
        
        For Sprint 1, actions are logged only.
        Sprint 2 will implement actual actions (alerts, notifications, etc.).
        
        Args:
            rule: Triggered rule
            sentiment: Sentiment that triggered the rule
        """
        action_map = {
            "log_alert": lambda: logger.warning(
                f"ALERT: {rule.name} - Sentiment: {sentiment.sentiment_score:.2f}, "
                f"Dominant: {sentiment.dominant_emotion}"
            ),
            "log_warning": lambda: logger.warning(
                f"WARNING: {rule.name} - {sentiment.dominant_emotion} detected"
            ),
            "log_info": lambda: logger.info(
                f"INFO: {rule.name} - Positive sentiment: {sentiment.sentiment_score:.2f}"
            )
        }
        
        action_fn = action_map.get(rule.action)
        if action_fn:
            action_fn()
        else:
            logger.debug(f"Action '{rule.action}' not implemented (Sprint 1 scaffold)")
    
    def get_stats(self) -> dict:
        """
        Get rules engine statistics.
        
        Returns:
            dict: Statistics about rules and evaluations
        """
        return {
            "total_rules": len(self.rules),
            "enabled_rules": len([r for r in self.rules if r.enabled]),
            "evaluations_count": self._evaluations_count
        }
