"""
Alerts Router - VANTA-29
Alert management endpoints for viewing, filtering, and resolving alerts
"""
import logging
import csv
import io
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import asyncpg

from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/alerts", tags=["alerts"])

# ============================================================================
# Pydantic Models for Alerts
# ============================================================================

class AlertSeverity(str):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str):
    """Alert status types."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class AlertResponse(BaseModel):
    """Alert response model."""
    id: str
    rule_id: str
    rule_name: Optional[str] = None
    camera_id: Optional[str] = None
    camera_name: Optional[str] = None
    alert_type: str
    emotion: Optional[str] = None
    message: str
    severity: str
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    action_taken: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None
    status: str  # Computed: active/acknowledged/resolved
    
    class Config:
        from_attributes = True


class AlertUpdate(BaseModel):
    """Alert update request."""
    acknowledged: Optional[bool] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None


class AlertStatsResponse(BaseModel):
    """Alert statistics response."""
    total: int
    active: int
    resolved: int
    acknowledged: int
    severity_breakdown: Dict[str, int] = Field(
        default_factory=lambda: {"info": 0, "warning": 0, "critical": 0}
    )
    top_emotions: List[Dict[str, Any]] = Field(default_factory=list)
    top_rules: List[Dict[str, Any]] = Field(default_factory=list)


class AlertListResponse(BaseModel):
    """Paginated alert list response."""
    alerts: List[AlertResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# Helper Functions
# ============================================================================

async def get_db_connection():
    """Get PostgreSQL connection."""
    return await asyncpg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        database=settings.postgres_db,
        user=settings.postgres_user,
        password=settings.postgres_password
    )


def compute_alert_status(alert: Dict[str, Any]) -> str:
    """Compute alert status from fields."""
    if alert.get('resolved_at'):
        return "resolved"
    elif alert.get('acknowledged'):
        return "acknowledged"
    else:
        return "active"


async def enrich_alert_with_names(conn: asyncpg.Connection, alert: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich alert with rule and camera names."""
    # Get rule name
    if alert.get('rule_id'):
        try:
            rule = await conn.fetchrow(
                "SELECT name FROM rules WHERE id = $1",
                UUID(alert['rule_id'])
            )
            if rule:
                alert['rule_name'] = rule['name']
        except Exception as e:
            logger.warning(f"Failed to fetch rule name: {e}")
    
    # Get camera name
    if alert.get('camera_id'):
        try:
            camera = await conn.fetchrow(
                "SELECT name FROM cameras WHERE camera_id = $1",
                UUID(alert['camera_id'])
            )
            if camera:
                alert['camera_name'] = camera['name']
        except Exception as e:
            logger.warning(f"Failed to fetch camera name: {e}")
    
    # Compute status
    alert['status'] = compute_alert_status(alert)
    
    return alert


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/", response_model=AlertListResponse)
async def list_alerts(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    severity: Optional[str] = Query(None, description="Filter by severity: info, warning, critical"),
    status: Optional[str] = Query(None, description="Filter by status: active, acknowledged, resolved"),
    camera_id: Optional[str] = Query(None, description="Filter by camera ID"),
    search: Optional[str] = Query(None, description="Search in message or rule name"),
    start_time: Optional[datetime] = Query(None, description="Start time filter"),
    end_time: Optional[datetime] = Query(None, description="End time filter"),
):
    """
    List alerts with filtering, search, and pagination.
    
    - **page**: Page number (1-indexed)
    - **page_size**: Number of alerts per page (max 100)
    - **severity**: Filter by severity level
    - **status**: Filter by alert status
    - **camera_id**: Filter by specific camera
    - **search**: Search term for message or rule name
    - **start_time**: Filter alerts after this time
    - **end_time**: Filter alerts before this time
    """
    conn = await get_db_connection()
    
    try:
        # Build WHERE conditions
        conditions = []
        params = []
        param_idx = 1
        
        # Severity filter
        if severity:
            if severity not in ["info", "warning", "critical"]:
                raise HTTPException(status_code=400, detail="Invalid severity value")
            conditions.append(f"severity = ${param_idx}")
            params.append(severity)
            param_idx += 1
        
        # Status filter
        status_condition = None
        if status == "active":
            status_condition = "resolved_at IS NULL AND acknowledged = FALSE"
        elif status == "acknowledged":
            status_condition = "acknowledged = TRUE AND resolved_at IS NULL"
        elif status == "resolved":
            status_condition = "resolved_at IS NOT NULL"
        
        if status_condition:
            conditions.append(f"({status_condition})")
        
        # Camera filter
        if camera_id:
            conditions.append(f"camera_id = ${param_idx}")
            params.append(UUID(camera_id))
            param_idx += 1
        
        # Time range filters
        if start_time:
            conditions.append(f"triggered_at >= ${param_idx}")
            params.append(start_time)
            param_idx += 1
        
        if end_time:
            conditions.append(f"triggered_at <= ${param_idx}")
            params.append(end_time)
            param_idx += 1
        
        # Build WHERE clause
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        # Get total count
        count_query = f"SELECT COUNT(*) FROM alerts {where_clause}"
        total = await conn.fetchval(count_query, *params)
        
        # Calculate pagination
        offset = (page - 1) * page_size
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        
        # Get alerts
        query = f"""
            SELECT 
                id, rule_id, camera_id, alert_type, emotion, message,
                severity, triggered_at, resolved_at, action_taken,
                metadata_json, acknowledged, acknowledged_by, acknowledged_at
            FROM alerts
            {where_clause}
            ORDER BY triggered_at DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        params.extend([page_size, offset])
        
        rows = await conn.fetch(query, *params)
        
        # Convert to dictionaries and enrich
        alerts = []
        for row in rows:
            alert = dict(row)
            alert = await enrich_alert_with_names(conn, alert)
            
            # Convert UUIDs to strings
            alert['id'] = str(alert['id'])
            alert['rule_id'] = str(alert['rule_id'])
            if alert.get('camera_id'):
                alert['camera_id'] = str(alert['camera_id'])
            
            # Parse metadata_json if it's a string
            if alert.get('metadata_json') and isinstance(alert['metadata_json'], str):
                import json
                try:
                    alert['metadata_json'] = json.loads(alert['metadata_json'])
                except:
                    alert['metadata_json'] = None
            
            alerts.append(AlertResponse(**alert))
        
        # Apply search filter in-memory if provided
        if search:
            search_lower = search.lower()
            alerts = [
                a for a in alerts 
                if (search_lower in a.message.lower() or 
                    (a.rule_name and search_lower in a.rule_name.lower()))
            ]
            total = len(alerts)
            total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        
        logger.info(f"Retrieved {len(alerts)} alerts (page {page}, total {total})")
        
        return AlertListResponse(
            alerts=alerts,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing alerts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list alerts: {str(e)}")
    finally:
        await conn.close()


@router.get("/stats/", response_model=AlertStatsResponse)
async def get_alert_stats(
    hours: int = Query(24, ge=1, le=720, description="Time period in hours"),
    camera_id: Optional[str] = Query(None, description="Filter by camera ID"),
):
    """
    Get alert statistics for the specified time period.
    
    - **hours**: Number of hours to look back (max 30 days)
    - **camera_id**: Optional camera ID filter
    """
    conn = await get_db_connection()
    
    try:
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Build WHERE clause
        conditions = ["triggered_at >= $1"]
        params = [start_time]
        
        if camera_id:
            conditions.append("camera_id = $2")
            params.append(UUID(camera_id))
        
        where_clause = " AND ".join(conditions)
        
        # Get total counts
        total_query = f"SELECT COUNT(*) FROM alerts WHERE {where_clause}"
        total = await conn.fetchval(total_query, *params)
        
        # Get status counts
        active_query = f"""
            SELECT COUNT(*) FROM alerts 
            WHERE {where_clause} AND resolved_at IS NULL AND acknowledged = FALSE
        """
        active = await conn.fetchval(active_query, *params)
        
        resolved_query = f"""
            SELECT COUNT(*) FROM alerts 
            WHERE {where_clause} AND resolved_at IS NOT NULL
        """
        resolved = await conn.fetchval(resolved_query, *params)
        
        acknowledged_query = f"""
            SELECT COUNT(*) FROM alerts 
            WHERE {where_clause} AND acknowledged = TRUE AND resolved_at IS NULL
        """
        acknowledged = await conn.fetchval(acknowledged_query, *params)
        
        # Get severity breakdown
        severity_query = f"""
            SELECT severity, COUNT(*) as count
            FROM alerts
            WHERE {where_clause}
            GROUP BY severity
        """
        severity_rows = await conn.fetch(severity_query, *params)
        severity_breakdown = {row['severity']: row['count'] for row in severity_rows}
        
        # Ensure all severities are present
        for sev in ['info', 'warning', 'critical']:
            if sev not in severity_breakdown:
                severity_breakdown[sev] = 0
        
        # Get top emotions
        emotion_query = f"""
            SELECT emotion, COUNT(*) as count
            FROM alerts
            WHERE {where_clause} AND emotion IS NOT NULL
            GROUP BY emotion
            ORDER BY count DESC
            LIMIT 5
        """
        emotion_rows = await conn.fetch(emotion_query, *params)
        top_emotions = [
            {"emotion": row['emotion'], "count": row['count']}
            for row in emotion_rows
        ]
        
        # Get top rules
        rule_query = f"""
            SELECT r.id, r.name, COUNT(a.id) as trigger_count
            FROM alerts a
            JOIN rules r ON a.rule_id = r.id
            WHERE {where_clause}
            GROUP BY r.id, r.name
            ORDER BY trigger_count DESC
            LIMIT 5
        """
        rule_rows = await conn.fetch(rule_query, *params)
        top_rules = [
            {"rule_id": str(row['id']), "rule_name": row['name'], "trigger_count": row['trigger_count']}
            for row in rule_rows
        ]
        
        logger.info(f"Retrieved alert stats: total={total}, active={active}, hours={hours}")
        
        return AlertStatsResponse(
            total=total,
            active=active,
            resolved=resolved,
            acknowledged=acknowledged,
            severity_breakdown=severity_breakdown,
            top_emotions=top_emotions,
            top_rules=top_rules
        )
        
    except Exception as e:
        logger.error(f"Error getting alert stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get alert stats: {str(e)}")
    finally:
        await conn.close()


@router.get("/{alert_id}/", response_model=AlertResponse)
async def get_alert_detail(alert_id: str):
    """
    Get detailed information for a specific alert.
    
    - **alert_id**: UUID of the alert
    """
    conn = await get_db_connection()
    
    try:
        alert_uuid = UUID(alert_id)
        
        row = await conn.fetchrow(
            """
            SELECT 
                id, rule_id, camera_id, alert_type, emotion, message,
                severity, triggered_at, resolved_at, action_taken,
                metadata_json, acknowledged, acknowledged_by, acknowledged_at
            FROM alerts
            WHERE id = $1
            """,
            alert_uuid
        )
        
        if not row:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        alert = dict(row)
        alert = await enrich_alert_with_names(conn, alert)
        
        # Convert UUIDs to strings
        alert['id'] = str(alert['id'])
        alert['rule_id'] = str(alert['rule_id'])
        if alert.get('camera_id'):
            alert['camera_id'] = str(alert['camera_id'])
        
        # Parse metadata_json if it's a string
        if alert.get('metadata_json') and isinstance(alert['metadata_json'], str):
            import json
            try:
                alert['metadata_json'] = json.loads(alert['metadata_json'])
            except:
                alert['metadata_json'] = None
        
        return AlertResponse(**alert)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid alert ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting alert detail: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get alert: {str(e)}")
    finally:
        await conn.close()


@router.put("/{alert_id}/", response_model=AlertResponse)
async def update_alert(alert_id: str, update: AlertUpdate):
    """
    Update alert status (acknowledge or resolve).
    
    - **alert_id**: UUID of the alert
    - **acknowledged**: Set to true to acknowledge the alert
    - **acknowledged_by**: Username who acknowledged (required if acknowledged=true)
    - **resolved_at**: Set to current time to resolve the alert
    """
    conn = await get_db_connection()
    
    try:
        alert_uuid = UUID(alert_id)
        
        # Check if alert exists
        exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM alerts WHERE id = $1)",
            alert_uuid
        )
        
        if not exists:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        # Build update query
        update_fields = []
        params = []
        param_idx = 1
        
        if update.acknowledged is not None:
            update_fields.append(f"acknowledged = ${param_idx}")
            params.append(update.acknowledged)
            param_idx += 1
            
            if update.acknowledged:
                # Set acknowledged_at to now if acknowledging
                update_fields.append(f"acknowledged_at = ${param_idx}")
                params.append(datetime.utcnow())
                param_idx += 1
                
                if update.acknowledged_by:
                    update_fields.append(f"acknowledged_by = ${param_idx}")
                    params.append(update.acknowledged_by)
                    param_idx += 1
        
        if update.resolved_at is not None:
            update_fields.append(f"resolved_at = ${param_idx}")
            params.append(update.resolved_at)
            param_idx += 1
        
        if not update_fields:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        # Execute update
        query = f"""
            UPDATE alerts
            SET {', '.join(update_fields)}
            WHERE id = ${param_idx}
            RETURNING 
                id, rule_id, camera_id, alert_type, emotion, message,
                severity, triggered_at, resolved_at, action_taken,
                metadata_json, acknowledged, acknowledged_by, acknowledged_at
        """
        params.append(alert_uuid)
        
        row = await conn.fetchrow(query, *params)
        
        if not row:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        alert = dict(row)
        alert = await enrich_alert_with_names(conn, alert)
        
        # Convert UUIDs to strings
        alert['id'] = str(alert['id'])
        alert['rule_id'] = str(alert['rule_id'])
        if alert.get('camera_id'):
            alert['camera_id'] = str(alert['camera_id'])
        
        # Parse metadata_json if it's a string
        if alert.get('metadata_json') and isinstance(alert['metadata_json'], str):
            import json
            try:
                alert['metadata_json'] = json.loads(alert['metadata_json'])
            except:
                alert['metadata_json'] = None
        
        logger.info(f"Updated alert {alert_id}: {update_fields}")
        
        return AlertResponse(**alert)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid alert ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating alert: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update alert: {str(e)}")
    finally:
        await conn.close()


@router.delete("/{alert_id}/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(alert_id: str):
    """
    Delete an alert (soft delete by setting resolved_at).
    
    - **alert_id**: UUID of the alert to delete
    """
    conn = await get_db_connection()
    
    try:
        alert_uuid = UUID(alert_id)
        
        # Soft delete by setting resolved_at
        result = await conn.execute(
            """
            UPDATE alerts
            SET resolved_at = NOW()
            WHERE id = $1 AND resolved_at IS NULL
            """,
            alert_uuid
        )
        
        if result == "UPDATE 0":
            # Check if alert exists
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM alerts WHERE id = $1)",
                alert_uuid
            )
            
            if not exists:
                raise HTTPException(status_code=404, detail="Alert not found")
            else:
                # Already resolved
                logger.info(f"Alert {alert_id} already resolved")
        
        logger.info(f"Deleted (resolved) alert {alert_id}")
        return None
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid alert ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting alert: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete alert: {str(e)}")
    finally:
        await conn.close()


@router.post("/export/")
async def export_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity"),
    status: Optional[str] = Query(None, description="Filter by status"),
    camera_id: Optional[str] = Query(None, description="Filter by camera ID"),
    start_time: Optional[datetime] = Query(None, description="Start time filter"),
    end_time: Optional[datetime] = Query(None, description="End time filter"),
):
    """
    Export alerts to CSV with optional filters.
    
    Returns a CSV file with alert data matching the specified filters.
    """
    conn = await get_db_connection()
    
    try:
        # Build WHERE conditions (same as list_alerts)
        conditions = []
        params = []
        param_idx = 1
        
        if severity:
            if severity not in ["info", "warning", "critical"]:
                raise HTTPException(status_code=400, detail="Invalid severity value")
            conditions.append(f"severity = ${param_idx}")
            params.append(severity)
            param_idx += 1
        
        status_condition = None
        if status == "active":
            status_condition = "resolved_at IS NULL AND acknowledged = FALSE"
        elif status == "acknowledged":
            status_condition = "acknowledged = TRUE AND resolved_at IS NULL"
        elif status == "resolved":
            status_condition = "resolved_at IS NOT NULL"
        
        if status_condition:
            conditions.append(f"({status_condition})")
        
        if camera_id:
            conditions.append(f"camera_id = ${param_idx}")
            params.append(UUID(camera_id))
            param_idx += 1
        
        if start_time:
            conditions.append(f"triggered_at >= ${param_idx}")
            params.append(start_time)
            param_idx += 1
        
        if end_time:
            conditions.append(f"triggered_at <= ${param_idx}")
            params.append(end_time)
            param_idx += 1
        
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        # Get alerts
        query = f"""
            SELECT 
                a.id, a.rule_id, r.name as rule_name, 
                a.camera_id, c.name as camera_name,
                a.alert_type, a.emotion, a.message,
                a.severity, a.triggered_at, a.resolved_at, 
                a.action_taken, a.acknowledged, 
                a.acknowledged_by, a.acknowledged_at
            FROM alerts a
            LEFT JOIN rules r ON a.rule_id = r.id
            LEFT JOIN cameras c ON a.camera_id = c.camera_id
            {where_clause}
            ORDER BY a.triggered_at DESC
        """
        
        rows = await conn.fetch(query, *params)
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'ID', 'Triggered At', 'Severity', 'Status', 'Rule Name', 
            'Camera Name', 'Emotion', 'Message', 'Action Taken',
            'Acknowledged', 'Acknowledged By', 'Acknowledged At', 'Resolved At'
        ])
        
        # Write data
        for row in rows:
            status_value = compute_alert_status(dict(row))
            writer.writerow([
                str(row['id']),
                row['triggered_at'].isoformat() if row['triggered_at'] else '',
                row['severity'],
                status_value,
                row['rule_name'] or '',
                row['camera_name'] or '',
                row['emotion'] or '',
                row['message'],
                row['action_taken'] or '',
                'Yes' if row['acknowledged'] else 'No',
                row['acknowledged_by'] or '',
                row['acknowledged_at'].isoformat() if row['acknowledged_at'] else '',
                row['resolved_at'].isoformat() if row['resolved_at'] else '',
            ])
        
        # Create filename with timestamp
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"alerts_export_{timestamp}.csv"
        
        # Return as streaming response
        output.seek(0)
        
        logger.info(f"Exported {len(rows)} alerts to CSV")
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error exporting alerts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to export alerts: {str(e)}")
    finally:
        await conn.close()
