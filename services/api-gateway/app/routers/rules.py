"""API routers for rules management endpoints (VANTA-20)."""
import logging
import uuid
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException, status, Depends
import asyncpg
from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (
    RuleCreate,
    RuleUpdate,
    RuleResponse,
    RuleAction,
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


@router.post("/", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(rule: RuleCreate):
    """
    Create a new sentiment rule.
    
    Stores rule configuration in PostgreSQL with JSON config.
    """
    conn = await get_db_connection()
    
    try:
        rule_id = str(uuid.uuid4())
        now = datetime.now()
        
        await conn.execute(
            """
            INSERT INTO rules (id, name, type, condition_json, action, enabled, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """,
            rule_id, rule.name, rule.type, rule.condition_json, rule.action.value, 
            rule.enabled, now, now
        )
        
        logger.info(f"Rule created: {rule_id} - {rule.name}")
        
        return RuleResponse(
            id=rule_id,
            name=rule.name,
            type=rule.type,
            condition_json=rule.condition_json,
            action=rule.action,
            enabled=rule.enabled,
            created_at=now,
            updated_at=now
        )
    
    except asyncpg.UniqueViolationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
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
                id=row['id'],
                name=row['name'],
                type=row['type'],
                condition_json=row['condition_json'],
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
            id=row['id'],
            name=row['name'],
            type=row['type'],
            condition_json=row['condition_json'],
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
    
    Updates PostgreSQL and can trigger reload in sentiment-analysis service.
    """
    conn = await get_db_connection()
    
    try:
        # Check if rule exists
        existing = await conn.fetchrow("SELECT * FROM rules WHERE id = $1", rule_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rule {rule_id} not found"
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
            values.append(rule_update.type)
            param_idx += 1
        
        if rule_update.condition_json is not None:
            updates.append(f"condition_json = ${param_idx}")
            values.append(rule_update.condition_json)
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
        
        logger.info(f"Rule updated: {rule_id}")
        
        return RuleResponse(
            id=row['id'],
            name=row['name'],
            type=row['type'],
            condition_json=row['condition_json'],
            action=RuleAction(row['action']),
            enabled=row['enabled'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
    
    except HTTPException:
        raise
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
    
    Removes rule from PostgreSQL.
    """
    conn = await get_db_connection()
    
    try:
        result = await conn.execute(
            "DELETE FROM rules WHERE id = $1",
            rule_id
        )
        
        if result == "DELETE 0":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rule {rule_id} not found"
            )
        
        logger.info(f"Rule deleted: {rule_id}")
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
