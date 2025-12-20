"""
Analytics Router - VANTA-30
Comprehensive analytics and reporting endpoints matching frontend requirements
"""
import logging
import csv
import io
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import asyncpg

from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


# ============================================================================
# Database Helper
# ============================================================================

async def get_db_connection():
    """Create database connection."""
    return await asyncpg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password,
        database=settings.postgres_db
    )


# ============================================================================
# Pydantic Models
# ============================================================================

class TimelinePoint(BaseModel):
    """Single timeline data point."""
    timestamp: str
    detections: int
    emotions: int
    sentiments: int


class TimelineResponse(BaseModel):
    """Timeline data response."""
    timeline: List[TimelinePoint]


class DetectionStats(BaseModel):
    """Detection statistics."""
    total_detections: int
    unique_faces: int
    avg_confidence: float


class EmotionItem(BaseModel):
    """Emotion distribution item."""
    emotion: str
    count: int
    percentage: float


class EmotionResponse(BaseModel):
    """Emotion distribution response."""
    emotions: List[EmotionItem]


class SentimentItem(BaseModel):
    """Sentiment distribution item."""
    sentiment: str
    count: int
    percentage: float


class SentimentResponse(BaseModel):
    """Sentiment distribution response."""
    sentiments: List[SentimentItem]


class CameraStatsItem(BaseModel):
    """Camera statistics item."""
    camera_id: str
    camera_name: str
    detections: int
    active_time: int


class CameraStatsResponse(BaseModel):
    """Camera statistics response."""
    cameras: List[CameraStatsItem]


# ============================================================================
# Analytics Endpoints
# ============================================================================

@router.get("/stats/timeline", response_model=TimelineResponse)
async def get_timeline_stats(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    interval: str = Query("hour", regex="^(hour|day|week|month)$"),
    camera_id: Optional[str] = None
):
    """Get timeline data for detections, emotions, and sentiments."""
    conn = None
    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        
        conn = await get_db_connection()
        
        # Determine time truncation based on interval
        trunc_map = {"hour": "hour", "day": "day", "week": "week", "month": "month"}
        trunc = trunc_map[interval]
        
        camera_filter = "AND d.camera_id = $3" if camera_id else ""
        params = [start, end]
        if camera_id:
            params.append(camera_id)
        
        query = f"""
            SELECT 
                DATE_TRUNC('{trunc}', e.timestamp) as period,
                COUNT(DISTINCT e.id) as detections,
                COUNT(DISTINCT e.id) as emotions,
                COUNT(DISTINCT ss.id) as sentiments
            FROM emotions e
            LEFT JOIN sentiment_stats ss ON ss.camera_id = e.camera_id 
                AND DATE_TRUNC('hour', ss.timestamp) = DATE_TRUNC('hour', e.timestamp)
            WHERE e.timestamp BETWEEN $1 AND $2
            {camera_filter}
            GROUP BY DATE_TRUNC('{trunc}', e.timestamp)
            ORDER BY period ASC
        """
        
        results = await conn.fetch(query, *params)
        
        timeline = [
            TimelinePoint(
                timestamp=row['period'].isoformat() if row['period'] else "",
                detections=row['detections'] or 0,
                emotions=row['emotions'] or 0,
                sentiments=row['sentiments'] or 0
            )
            for row in results
        ]
        
        return TimelineResponse(timeline=timeline)
        
    except Exception as e:
        logger.error(f"Error fetching timeline stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch timeline: {str(e)}")
    finally:
        if conn:
            await conn.close()


@router.get("/stats/detections", response_model=DetectionStats)
async def get_detection_stats(
    start_date: str = Query(...),
    end_date: str = Query(...),
    camera_id: Optional[str] = None
):
    """Get detection statistics."""
    conn = None
    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        
        conn = await get_db_connection()
        
        camera_filter = "AND camera_id = $3" if camera_id else ""
        params = [start, end]
        if camera_id:
            params.append(camera_id)
        
        query = f"""
            SELECT 
                COUNT(id) as total_detections,
                COUNT(DISTINCT face_id) as unique_faces,
                AVG(confidence) as avg_confidence
            FROM emotions
            WHERE timestamp BETWEEN $1 AND $2
            {camera_filter}
        """
        
        result = await conn.fetchrow(query, *params)
        
        return DetectionStats(
            total_detections=result['total_detections'] or 0,
            unique_faces=result['unique_faces'] or 0,
            avg_confidence=float(result['avg_confidence']) if result['avg_confidence'] else 0.0
        )
        
    except Exception as e:
        logger.error(f"Error fetching detection stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch detections: {str(e)}")
    finally:
        if conn:
            await conn.close()


@router.get("/stats/emotions", response_model=EmotionResponse)
async def get_emotion_stats(
    start_date: str = Query(...),
    end_date: str = Query(...),
    camera_id: Optional[str] = None
):
    """Get emotion distribution statistics."""
    conn = None
    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        
        conn = await get_db_connection()
        
        camera_filter = "AND camera_id = $3" if camera_id else ""
        params = [start, end]
        if camera_id:
            params.append(camera_id)
        
        query = f"""
            SELECT 
                emotion,
                COUNT(*) as count
            FROM emotions
            WHERE timestamp BETWEEN $1 AND $2
            {camera_filter}
            GROUP BY emotion
            ORDER BY count DESC
        """
        
        results = await conn.fetch(query, *params)
        total = sum(r['count'] for r in results)
        
        emotions = [
            EmotionItem(
                emotion=row['emotion'],
                count=row['count'],
                percentage=(row['count'] / total * 100) if total > 0 else 0
            )
            for row in results
        ]
        
        return EmotionResponse(emotions=emotions)
        
    except Exception as e:
        logger.error(f"Error fetching emotion stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch emotions: {str(e)}")
    finally:
        if conn:
            await conn.close()


@router.get("/stats/sentiments", response_model=SentimentResponse)
async def get_sentiment_stats(
    start_date: str = Query(...),
    end_date: str = Query(...),
    camera_id: Optional[str] = None
):
    """Get sentiment distribution statistics."""
    conn = None
    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        
        conn = await get_db_connection()
        
        camera_filter = "AND d.camera_id = $3" if camera_id else ""
        params = [start, end]
        if camera_id:
            params.append(camera_id)
        
        query = f"""
            SELECT 
                CASE 
                    WHEN sentiment_score > 0.2 THEN 'positive'
                    WHEN sentiment_score < -0.2 THEN 'negative'
                    ELSE 'neutral'
                END as sentiment,
                COUNT(*) as count
            FROM sentiment_stats
            WHERE timestamp BETWEEN $1 AND $2
            {camera_filter}
            GROUP BY sentiment
            ORDER BY count DESC
        """
        
        results = await conn.fetch(query, *params)
        total = sum(r['count'] for r in results)
        
        sentiments = [
            SentimentItem(
                sentiment=row['sentiment'],
                count=row['count'],
                percentage=(row['count'] / total * 100) if total > 0 else 0
            )
            for row in results
        ]
        
        return SentimentResponse(sentiments=sentiments)
        
    except Exception as e:
        logger.error(f"Error fetching sentiment stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch sentiments: {str(e)}")
    finally:
        if conn:
            await conn.close()


@router.get("/stats/cameras", response_model=CameraStatsResponse)
async def get_camera_stats(
    start_date: str = Query(...),
    end_date: str = Query(...)
):
    """Get camera performance statistics."""
    conn = None
    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        
        conn = await get_db_connection()
        
        query = """
            SELECT 
                c.id as camera_id,
                c.name as camera_name,
                COUNT(e.id) as detections,
                EXTRACT(EPOCH FROM (MAX(e.timestamp) - MIN(e.timestamp)))/3600 as active_time
            FROM cameras c
            LEFT JOIN emotions e ON e.camera_id = c.id 
                AND e.timestamp BETWEEN $1 AND $2
            GROUP BY c.id, c.name
            ORDER BY detections DESC
        """
        
        results = await conn.fetch(query, start, end)
        
        cameras = [
            CameraStatsItem(
                camera_id=str(row['camera_id']),
                camera_name=row['camera_name'],
                detections=row['detections'] or 0,
                active_time=int(row['active_time']) if row['active_time'] else 0
            )
            for row in results
        ]
        
        return CameraStatsResponse(cameras=cameras)
        
    except Exception as e:
        logger.error(f"Error fetching camera stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch camera stats: {str(e)}")
    finally:
        if conn:
            await conn.close()


@router.get("/stats/export")
async def export_analytics(
    start_date: str = Query(...),
    end_date: str = Query(...),
    camera_id: Optional[str] = None
):
    """Export analytics data as CSV."""
    conn = None
    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
        
        conn = await get_db_connection()
        
        camera_filter = "AND d.camera_id = $3" if camera_id else ""
        params = [start, end]
        if camera_id:
            params.append(camera_id)
        
        query = f"""
            SELECT 
                e.timestamp,
                c.name as camera,
                e.confidence,
                e.emotion,
                ss.sentiment_score
            FROM emotions e
            JOIN cameras c ON e.camera_id = c.id
            LEFT JOIN sentiment_stats ss ON ss.camera_id = e.camera_id 
                AND DATE_TRUNC('hour', ss.timestamp) = DATE_TRUNC('hour', e.timestamp)
            WHERE e.timestamp BETWEEN $1 AND $2
            {camera_filter}
            ORDER BY e.timestamp DESC
            LIMIT 10000
        """
        
        results = await conn.fetch(query, *params)
        
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Timestamp", "Camera", "Detection Confidence", "Emotion", "Sentiment Score"])
        
        for row in results:
            writer.writerow([
                row['timestamp'].isoformat(),
                row['camera'],
                f"{row['confidence']:.4f}" if row['confidence'] else "",
                row['emotion'] or "",
                f"{row['sentiment_score']:.4f}" if row['sentiment_score'] else ""
            ])
        
        output.seek(0)
        filename = f"analytics_{start_date}_to_{end_date}.csv"
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting analytics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to export: {str(e)}")
    finally:
        if conn:
            await conn.close()
