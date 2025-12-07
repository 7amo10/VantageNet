"""API routers for rules management endpoints."""
import logging
from datetime import datetime
from typing import List
from fastapi import APIRouter, HTTPException, status

from ..models import (
    RuleCreate,
    RuleUpdate,
    RuleResponse,
    RuleAction,
    ErrorResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/rules", tags=["Rules"])

# In-memory storage for Sprint 1 (will use database in Sprint 2)
_rules_db: dict = {}


@router.post("/", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(rule: RuleCreate):
    """
    Create a new sentiment rule.
    
    For Sprint 1: Returns dummy data.
    Sprint 2: Will store in PostgreSQL and integrate with sentiment-analysis.
    """
    rule_id = f"rule_{len(_rules_db) + 1:03d}"
    
    rule_response = RuleResponse(
        rule_id=rule_id,
        name=rule.name,
        description=rule.description,
        condition=rule.condition,
        action=rule.action,
        priority=rule.priority,
        enabled=rule.enabled,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    _rules_db[rule_id] = rule_response
    
    logger.info(f"Rule created: {rule_id} - {rule.name}")
    
    return rule_response


@router.get("/", response_model=List[RuleResponse])
async def list_rules():
    """
    List all sentiment rules.
    
    For Sprint 1: Returns from in-memory storage.
    Sprint 2: Will query PostgreSQL.
    """
    return list(_rules_db.values())


@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule(rule_id: str):
    """
    Get rule details by ID.
    
    For Sprint 1: Returns from in-memory storage.
    Sprint 2: Will query PostgreSQL.
    """
    if rule_id not in _rules_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found"
        )
    
    return _rules_db[rule_id]


@router.put("/{rule_id}", response_model=RuleResponse)
async def update_rule(rule_id: str, rule_update: RuleUpdate):
    """
    Update rule configuration.
    
    For Sprint 1: Updates in-memory storage.
    Sprint 2: Will update PostgreSQL and notify sentiment-analysis.
    """
    if rule_id not in _rules_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found"
        )
    
    rule = _rules_db[rule_id]
    
    # Update fields
    if rule_update.name is not None:
        rule.name = rule_update.name
    if rule_update.description is not None:
        rule.description = rule_update.description
    if rule_update.condition is not None:
        rule.condition = rule_update.condition
    if rule_update.action is not None:
        rule.action = rule_update.action
    if rule_update.priority is not None:
        rule.priority = rule_update.priority
    if rule_update.enabled is not None:
        rule.enabled = rule_update.enabled
    
    rule.updated_at = datetime.now()
    
    logger.info(f"Rule updated: {rule_id}")
    
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(rule_id: str):
    """
    Delete rule.
    
    For Sprint 1: Removes from in-memory storage.
    Sprint 2: Will remove from PostgreSQL.
    """
    if rule_id not in _rules_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rule {rule_id} not found"
        )
    
    del _rules_db[rule_id]
    logger.info(f"Rule deleted: {rule_id}")
    
    return None
