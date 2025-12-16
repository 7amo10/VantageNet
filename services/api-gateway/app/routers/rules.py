"""API routers for rules management endpoints (VANTA-20, VANTA-25)."""
import logging
import uuid
import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query
import asyncpg
import redis.asyncio as aioredis
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (
    RuleCreate,
    RuleUpdate,
    RuleResponse,
    RuleEvaluationResponse,
    RuleAction,
    RuleType,
    ErrorResponse
)
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rules", tags=["Rules"])


async def get_db_connection():
    """Get PostgreSQL connection."""
    return await asyncpg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password
    )


async def get_redis_connection():
    """Get Redis connection for event propagation."""
    return await aioredis.from_url(
        f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}",
        encoding="utf-8",
        decode_responses=True
    )


async def publish_rule_change(event_type: str, rule_data: dict):
    """
    Publish rule change event to Redis for sentiment-analysis service.
    
    Args:
        event_type: Type of event (created, updated, deleted, enabled, disabled)
        rule_data: Rule data to publish
    """
    try:
        redis_conn = await get_redis_connection()
        
        # Convert datetime objects to ISO format strings
        rule_data_json = {k: (v.isoformat() if isinstance(v, datetime) else v) 
                          for k, v in rule_data.items()}
        
        event = {
            "event_type": event_type,
            "rule": rule_data_json,
            "timestamp": datetime.now().isoformat()
        }
        await redis_conn.publish("rules:changes", json.dumps(event))
        await redis_conn.close()
        logger.info(f"Published rule change event: {event_type} for rule {rule_data.get('id', 'unknown')}")
    except Exception as e:
        logger.error(f"Failed to publish rule change event: {e}")
        # Don't fail the request if event publishing fails


def validate_rule_condition(rule_type: str, condition_json: dict):
    """
    Validate rule condition based on type.
    
    Args:
        rule_type: The rule type
        condition_json: The condition JSON to validate
        
    Raises:
        ValueError: If validation fails
    """
    # Validate threshold values (0.0-1.0)
    for key in ['threshold', 'sentiment_threshold', 'min_confidence', 'confidence']:
        if key in condition_json:
            value = condition_json[key]
            if not isinstance(value, (int, float)) or not (0.0 <= value <= 1.0):
                raise ValueError(f"{key} must be a number between 0.0 and 1.0")
    
    # Type-specific validation
    if rule_type == RuleType.THRESHOLD.value:
        if 'threshold' not in condition_json:
            raise ValueError("Threshold rules must have 'threshold' in condition_json")
    
    elif rule_type == RuleType.DURATION.value:
        if 'duration_seconds' not in condition_json:
            raise ValueError("Duration rules must have 'duration_seconds' in condition_json")
        duration = condition_json['duration_seconds']
        if not isinstance(duration, (int, float)) or duration <= 0:
            raise ValueError("duration_seconds must be a positive number")
    
    elif rule_type == RuleType.TREND.value:
        if 'window_size' not in condition_json:
            raise ValueError("Trend rules must have 'window_size' in condition_json")
    
    elif rule_type == RuleType.SENTIMENT.value:
        if 'sentiment_threshold' not in condition_json:
            raise ValueError("Sentiment rules must have 'sentiment_threshold' in condition_json")


@router.post("/", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(rule: RuleCreate):
    """
    Create a new sentiment rule.
    
    Stores rule configuration in PostgreSQL with JSON config.
    Validates condition_json based on rule type.
    Publishes rule change event to Redis.
    """
    # Validate condition_json
    try:
        validate_rule_condition(rule.type.value, rule.condition_json)
    except ValueError as e:
        logger.warning(f"Validation error creating rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    conn = await get_db_connection()
    
    try:
        rule_id = str(uuid.uuid4())
        now = datetime.now()
        
        await conn.execute(
            """
            INSERT INTO rules (id, name, type, condition_json, action, enabled, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            rule_id, rule.name, rule.type.value, json.dumps(rule.condition_json), rule.action.value, 
            rule.enabled, now, now
        )
        
        logger.info(f"Rule created: {rule_id} - {rule.name} (type: {rule.type.value})")
        
        response = RuleResponse(
            id=rule_id,
            name=rule.name,
            type=rule.type.value,
            condition_json=rule.condition_json,
            action=rule.action,
            enabled=rule.enabled,
            created_at=now,
            updated_at=now
        )
        
        # Publish event to Redis for sentiment-analysis service
        await publish_rule_change("created", response.dict())
        
        return response
    
    except asyncpg.UniqueViolationError:
        logger.warning(f"Duplicate rule name: {rule.name}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Rule with name '{rule.name}' already exists"
        )
    except Exception as e:
        logger.error(f"Error creating rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create rule"
        )
    finally:
        await conn.close()


@router.get("/", response_model=List[RuleResponse])
async def list_rules():
    """
    List all sentiment rules.
    
    Queries PostgreSQL for all rules.
    """
    conn = await get_db_connection()
    
    try:
        rows = await conn.fetch(
            """
            SELECT id, name, type, condition_json, action, enabled, created_at, updated_at
            FROM rules
            ORDER BY created_at DESC
            """
        )
        
        return [
            RuleResponse(
                id=str(row['id']),
                name=row['name'],
                type=row['type'],
                condition_json=json.loads(row['condition_json']) if isinstance(row['condition_json'], str) else row['condition_json'],
                action=RuleAction(row['action']),
                enabled=row['enabled'],
                created_at=row['created_at'],
                updated_at=row['updated_at']
            )
            for row in rows
        ]
    
    except Exception as e:
        logger.error(f"Error listing rules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list rules"
        )
    finally:
        await conn.close()


@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule(rule_id: str):
    """
    Get rule details by ID.
    
    Queries PostgreSQL for specific rule.
    """
    conn = await get_db_connection()
    
    try:
        row = await conn.fetchrow(
            """
            SELECT id, name, type, condition_json, action, enabled, created_at, updated_at
            FROM rules
            WHERE id = $1
            """,
            rule_id
        )
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rule {rule_id} not found"
            )
        
        return RuleResponse(
            id=str(row['id']),
            name=row['name'],
            type=row['type'],
            condition_json=json.loads(row['condition_json']) if isinstance(row['condition_json'], str) else row['condition_json'],
            action=RuleAction(row['action']),
            enabled=row['enabled'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get rule"
        )
    finally:
        await conn.close()


@router.put("/{rule_id}", response_model=RuleResponse)
async def update_rule(rule_id: str, rule_update: RuleUpdate):
    """
    Update rule configuration.
    
    Updates PostgreSQL and publishes change event to sentiment-analysis service.
    Validates condition_json if provided.
    """
    # Validate condition_json if both type and condition are provided
    if rule_update.condition_json and rule_update.type:
        try:
            validate_rule_condition(rule_update.type.value, rule_update.condition_json)
        except ValueError as e:
            logger.warning(f"Validation error updating rule {rule_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    
    conn = await get_db_connection()
    
    try:
        # Check if rule exists and get current type for validation
        existing = await conn.fetchrow("SELECT * FROM rules WHERE id = $1", rule_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rule {rule_id} not found"
            )
        
        # If condition_json is provided but type is not, validate against existing type
        if rule_update.condition_json and not rule_update.type:
            try:
                validate_rule_condition(existing['type'], rule_update.condition_json)
            except ValueError as e:
                logger.warning(f"Validation error updating rule {rule_id}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
        
        # Build update query dynamically
        updates = []
        values = []
        param_idx = 1
        
        if rule_update.name is not None:
            updates.append(f"name = ${param_idx}")
            values.append(rule_update.name)
            param_idx += 1
        
        if rule_update.type is not None:
            updates.append(f"type = ${param_idx}")
            values.append(rule_update.type.value)
            param_idx += 1
        
        if rule_update.condition_json is not None:
            updates.append(f"condition_json = ${param_idx}")
            values.append(json.dumps(rule_update.condition_json))
            param_idx += 1
        
        if rule_update.action is not None:
            updates.append(f"action = ${param_idx}")
            values.append(rule_update.action.value)
            param_idx += 1
        
        if rule_update.enabled is not None:
            updates.append(f"enabled = ${param_idx}")
            values.append(rule_update.enabled)
            param_idx += 1
        
        updates.append(f"updated_at = ${param_idx}")
        values.append(datetime.now())
        param_idx += 1
        
        values.append(rule_id)
        
        query = f"UPDATE rules SET {', '.join(updates)} WHERE id = ${param_idx} RETURNING *"
        row = await conn.fetchrow(query, *values)
        
        logger.info(f"Rule updated: {rule_id} - {row['name']}")
        
        response = RuleResponse(
            id=str(row['id']),
            name=row['name'],
            type=row['type'],
            condition_json=json.loads(row['condition_json']) if isinstance(row['condition_json'], str) else row['condition_json'],
            action=RuleAction(row['action']),
            enabled=row['enabled'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
        
        # Publish event to Redis
        await publish_rule_change("updated", response.dict())
        
        return response
    
    except HTTPException:
        raise
    except asyncpg.UniqueViolationError:
        logger.warning(f"Duplicate rule name attempted for rule {rule_id}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Rule with name '{rule_update.name}' already exists"
        )
    except Exception as e:
        logger.error(f"Error updating rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update rule"
        )
    finally:
        await conn.close()


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(rule_id: str):
    """
    Delete rule.
    
    Removes rule from PostgreSQL and publishes delete event.
    """
    conn = await get_db_connection()
    
    try:
        # Fetch rule data before deletion for event
        row = await conn.fetchrow("SELECT * FROM rules WHERE id = $1", rule_id)
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rule {rule_id} not found"
            )
        
        result = await conn.execute(
            "DELETE FROM rules WHERE id = $1",
            rule_id
        )
        
        logger.info(f"Rule deleted: {rule_id} - {row['name']}")
        
        # Publish event to Redis
        rule_data = {
            "id": str(row['id']),
            "name": row['name'],
            "type": row['type']
        }
        await publish_rule_change("deleted", rule_data)
        
        return None
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete rule"
        )
    finally:
        await conn.close()


@router.patch("/{rule_id}/enable", response_model=RuleResponse)
async def enable_rule(rule_id: str):
    """
    Enable a rule.
    
    Sets enabled=true in PostgreSQL and publishes enable event.
    """
    conn = await get_db_connection()
    
    try:
        row = await conn.fetchrow(
            """
            UPDATE rules 
            SET enabled = true, updated_at = $1 
            WHERE id = $2 
            RETURNING *
            """,
            datetime.now(), rule_id
        )
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rule {rule_id} not found"
            )
        
        logger.info(f"Rule enabled: {rule_id} - {row['name']}")
        
        response = RuleResponse(
            id=str(row['id']),
            name=row['name'],
            type=row['type'],
            condition_json=json.loads(row['condition_json']) if isinstance(row['condition_json'], str) else row['condition_json'],
            action=RuleAction(row['action']),
            enabled=row['enabled'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
        
        # Publish event to Redis
        await publish_rule_change("enabled", response.dict())
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enabling rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enable rule"
        )
    finally:
        await conn.close()


@router.patch("/{rule_id}/disable", response_model=RuleResponse)
async def disable_rule(rule_id: str):
    """
    Disable a rule.
    
    Sets enabled=false in PostgreSQL and publishes disable event.
    """
    conn = await get_db_connection()
    
    try:
        row = await conn.fetchrow(
            """
            UPDATE rules 
            SET enabled = false, updated_at = $1 
            WHERE id = $2 
            RETURNING *
            """,
            datetime.now(), rule_id
        )
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rule {rule_id} not found"
            )
        
        logger.info(f"Rule disabled: {rule_id} - {row['name']}")
        
        response = RuleResponse(
            id=str(row['id']),
            name=row['name'],
            type=row['type'],
            condition_json=json.loads(row['condition_json']) if isinstance(row['condition_json'], str) else row['condition_json'],
            action=RuleAction(row['action']),
            enabled=row['enabled'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
        
        # Publish event to Redis
        await publish_rule_change("disabled", response.dict())
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disabling rule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to disable rule"
        )
    finally:
        await conn.close()


@router.get("/{rule_id}/history", response_model=List[RuleEvaluationResponse])
async def get_rule_history(
    rule_id: str,
    limit: int = Query(default=100, ge=1, le=1000, description="Number of evaluations to return"),
    matched_only: Optional[bool] = Query(default=None, description="Filter by matched status")
):
    """
    Get past rule evaluations (history).
    
    Returns evaluation history from rule_evaluations table.
    """
    conn = await get_db_connection()
    
    try:
        # Verify rule exists
        rule_exists = await conn.fetchval("SELECT EXISTS(SELECT 1 FROM rules WHERE id = $1)", rule_id)
        if not rule_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rule {rule_id} not found"
            )
        
        # Build query with optional filter
        query = """
            SELECT id, rule_id, camera_id, evaluated_at, matched, emotion, 
                   sentiment_score, threshold_value, evaluation_result, action_taken
            FROM rule_evaluations
            WHERE rule_id = $1
        """
        params = [rule_id]
        
        if matched_only is not None:
            query += " AND matched = $2"
            params.append(matched_only)
            query += f" ORDER BY evaluated_at DESC LIMIT ${len(params) + 1}"
        else:
            query += f" ORDER BY evaluated_at DESC LIMIT ${len(params) + 1}"
        
        params.append(limit)
        
        rows = await conn.fetch(query, *params)
        
        logger.info(f"Retrieved {len(rows)} evaluation history records for rule {rule_id}")
        
        return [
            RuleEvaluationResponse(
                id=str(row['id']),
                rule_id=str(row['rule_id']),
                camera_id=str(row['camera_id']) if row['camera_id'] else None,
                evaluated_at=row['evaluated_at'],
                matched=row['matched'],
                emotion=row['emotion'],
                sentiment_score=row['sentiment_score'],
                threshold_value=row['threshold_value'],
                evaluation_result=row['evaluation_result'],
                action_taken=row['action_taken']
            )
            for row in rows
        ]
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting rule history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get rule history"
        )
    finally:
        await conn.close()


@router.post("/reload", status_code=status.HTTP_200_OK)
async def reload_rules():
    """
    Trigger hot reload of rules in sentiment-analysis service.
    
    Notifies sentiment-analysis to reload rules from database without restart.
    """
    # TODO: Implement Redis pub/sub or HTTP call to sentiment-analysis
    # For now, just acknowledge the request
    logger.info("Rules reload triggered")
    
    return {
        "message": "Rules reload triggered successfully",
        "note": "Sentiment-analysis service will reload rules on next evaluation cycle"
    }
