"""PostgreSQL database connection and management."""
import logging
from typing import Optional, List
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
import uuid

from sqlalchemy import create_engine, text, Column, Integer, String, Float, Boolean, DateTime, JSON, Text, select, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from .config import settings

logger = logging.getLogger(__name__)

# SQLAlchemy Base
Base = declarative_base()


class Rule(Base):
    """Rule definitions table."""
    
    __tablename__ = "rules"
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False, unique=True)
    type = Column(String(50), nullable=False, default='sentiment')
    condition_json = Column(JSON, nullable=False)  # Store rule config as JSON
    action = Column(String(100), nullable=False)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class SentimentHistory(Base):
    """Historical sentiment records."""
    
    __tablename__ = "sentiment_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    window_start = Column(DateTime, nullable=False)
    window_end = Column(DateTime, nullable=False)
    camera_ids = Column(JSON)
    total_faces = Column(Integer)
    emotion_distribution = Column(JSON)
    dominant_emotion = Column(String(50))
    sentiment_score = Column(Float)
    confidence = Column(Float)


class SentimentStats(Base):
    """Sentiment statistics table - matches actual database schema."""
    
    __tablename__ = "sentiment_stats"
    
    # Primary key is UUID in actual schema
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    camera_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    # Required NOT NULL columns from actual schema
    time_window_start = Column(DateTime, nullable=False)
    time_window_end = Column(DateTime, nullable=False)
    # Optional columns
    total_faces = Column(Integer, default=0)
    total_faces_observed = Column(Integer, default=0)
    # Emotion averages
    avg_happy = Column(Float)
    avg_sad = Column(Float)
    avg_angry = Column(Float)
    avg_neutral = Column(Float)
    avg_surprised = Column(Float)
    avg_fear = Column(Float)
    avg_disgust = Column(Float)
    # Aggregated data
    dominant_emotion = Column(String(50))
    sentiment_score = Column(Float)
    average_confidence = Column(Float)
    emotion_distribution = Column(JSON)
    mood_score = Column(Float, default=0.0)
    trend = Column(String(20))
    trend_magnitude = Column(Float)
    metadata_json = Column("metadata", JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class Alert(Base):
    """Triggered alerts from rules engine (VANTA-22 Enhanced)."""
    
    __tablename__ = "alerts"
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    rule_id = Column(UUID(as_uuid=False), nullable=False, index=True)
    camera_id = Column(UUID(as_uuid=False), index=True)
    alert_type = Column(String(50), nullable=False, default='rule_trigger')
    emotion = Column(String(50), index=True)
    message = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False, index=True)
    triggered_at = Column(DateTime, nullable=False, index=True)
    resolved_at = Column(DateTime)
    action_taken = Column(String(200))
    metadata_json = Column(JSON)
    acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(String(100))
    acknowledged_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)


class AlertMetric(Base):
    """Hourly aggregated alert metrics for analytics (VANTA-22)."""
    
    __tablename__ = "alert_metrics"
    
    id = Column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    hour = Column(DateTime, nullable=False, index=True)
    camera_id = Column(UUID(as_uuid=False), nullable=False, index=True)
    alert_count = Column(Integer, default=0)
    severity_breakdown = Column(JSON, nullable=False)
    top_emotion = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)


    created_at = Column(DateTime, default=datetime.utcnow)


class EmotionRecord(Base):
    """Raw emotion detection event (partitioned)."""
    
    __tablename__ = "emotions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    frame_id = Column(String(100), nullable=False)
    face_id = Column(String(100))
    emotion = Column(String(50), nullable=False)
    confidence = Column(Float, nullable=False)
    camera_id = Column(UUID(as_uuid=True), nullable=False)
    timestamp = Column(DateTime, nullable=False, primary_key=True)
    bounding_box = Column(JSON)
    meta_data = Column("metadata", JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class DatabaseManager:
    """PostgreSQL database connection manager."""
    
    def __init__(self):
        """Initialize database manager."""
        self.engine: Optional[create_async_engine] = None
        self.session_factory: Optional[async_sessionmaker] = None
        
    async def connect(self) -> None:
        """Establish database connection and create tables."""
        try:
            # Create async engine
            database_url = settings.database_url.replace(
                "postgresql://", "postgresql+asyncpg://"
            )
            
            self.engine = create_async_engine(
                database_url,
                echo=settings.log_level == "DEBUG",
                poolclass=NullPool,  # Use NullPool for simplicity in Sprint 1
                pool_pre_ping=True
            )
            
            # Create session factory
            self.session_factory = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Test connection
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            logger.info(
                f"Connected to PostgreSQL at {settings.postgres_host}:{settings.postgres_port}"
            )
            
            # Create tables if they don't exist
            await self._create_tables()
            
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    async def disconnect(self) -> None:
        """Close database connection."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Disconnected from PostgreSQL")
    
    async def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created/verified")
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise
    
    @asynccontextmanager
    async def get_session(self):
        """
        Get database session context manager.
        
        Usage:
            async with db_manager.get_session() as session:
                result = await session.execute(query)
        """
        if not self.session_factory:
            raise RuntimeError("Database not connected")
        
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    async def get_status(self) -> dict:
        """
        Get database connection status.
        
        Returns:
            dict: Connection status information
        """
        if not self.engine:
            return {
                "connected": False,
                "connection_pool_size": None
            }
        
        try:
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            return {
                "connected": True,
                "connection_pool_size": None  # NullPool has no size
            }
        except Exception as e:
            return {
                "connected": False,
                "connection_pool_size": None,
                "error": str(e)
            }
    
    async def save_sentiment(self, sentiment_result) -> bool:
        """
        Save sentiment result to history.
        
        Args:
            sentiment_result: SentimentResult model
            
        Returns:
            bool: True if saved successfully
        """
        try:
            async with self.get_session() as session:
                history = SentimentHistory(
                    timestamp=sentiment_result.timestamp,
                    window_start=sentiment_result.window_start,
                    window_end=sentiment_result.window_end,
                    camera_ids=sentiment_result.camera_ids,
                    total_faces=sentiment_result.total_faces,
                    emotion_distribution=sentiment_result.emotion_distribution,
                    dominant_emotion=sentiment_result.dominant_emotion,
                    sentiment_score=sentiment_result.sentiment_score,
                    confidence=sentiment_result.confidence
                )
                session.add(history)
            
            logger.debug("Saved sentiment to history")
            return True
            
        except Exception as e:
            logger.error(f"Error saving sentiment: {e}")
            return False
    
    async def save_crowd_sentiment(self, crowd_sentiment) -> bool:
        """
        Save crowd sentiment to sentiment_stats table (VANTA-18).
        
        Args:
            crowd_sentiment: CrowdSentiment model
            
        Returns:
            bool: True if saved successfully
        """
        try:
            # Convert emotion distribution to dict
            emotion_dist_dict = {
                emotion: {
                    "count": stats.count,
                    "avg_confidence": stats.avg_confidence,
                    "percentage": stats.percentage
                }
                for emotion, stats in crowd_sentiment.emotion_distribution.items()
            }
            
            # Convert camera_id string to UUID object
            try:
                cam_uuid = uuid.UUID(crowd_sentiment.camera_id)
            except ValueError:
                # Handle case where camera_id is not a valid UUID (e.g. "cam_1")
                # For now, generate a deterministic UUID or just skip
                logger.warning(f"Invalid UUID for camera_id: {crowd_sentiment.camera_id}")
                return False

            async with self.get_session() as session:
                stats = SentimentStats(
                    timestamp=crowd_sentiment.timestamp,
                    camera_id=cam_uuid,
                    total_faces_observed=crowd_sentiment.total_faces_observed,
                    emotion_distribution=emotion_dist_dict,
                    dominant_emotion=crowd_sentiment.dominant_emotion,
                    mood_score=crowd_sentiment.mood_score,
                    trend=crowd_sentiment.trend,
                    trend_magnitude=crowd_sentiment.trend_magnitude
                )
                session.add(stats)
            
            logger.debug(f"Saved crowd sentiment for camera {crowd_sentiment.camera_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving crowd sentiment: {e}")
            return False
    
    async def batch_save_crowd_sentiments(self, sentiments: List) -> bool:
        """
        Batch save multiple crowd sentiments (VANTA-18).
        
        Args:
            sentiments: List of CrowdSentiment models
            
        Returns:
            bool: True if all saved successfully
        """
        if not sentiments:
            return True
        
        try:
            async with self.get_session() as session:
                for crowd_sentiment in sentiments:
                    # Convert camera_id string to UUID object
                    try:
                        cam_uuid = uuid.UUID(crowd_sentiment.camera_id)
                    except ValueError:
                        logger.warning(f"Invalid UUID for camera_id: {crowd_sentiment.camera_id}")
                        continue
                    
                    # Convert emotion distribution
                    emotion_dist_dict = {
                        emotion: {
                            "count": stats.count,
                            "avg_confidence": stats.avg_confidence,
                            "percentage": stats.percentage
                        }
                        for emotion, stats in crowd_sentiment.emotion_distribution.items()
                    }
                    
                    # Handle timezone-aware timestamps: convert to naive UTC for PostgreSQL
                    ts = crowd_sentiment.timestamp
                    if ts.tzinfo is not None:
                        ts = ts.replace(tzinfo=None)  # Strip timezone, keep UTC value
                    
                    # Calculate time window (30 second window ending at timestamp)
                    window_end = ts
                    window_start = ts - timedelta(seconds=30)
                    
                    # Extract emotion percentages for individual columns
                    emotion_pcts = {e: 0.0 for e in ['happy', 'sad', 'angry', 'neutral', 'surprised', 'fear', 'disgust']}
                    for emotion, stats in crowd_sentiment.emotion_distribution.items():
                        if emotion.lower() in emotion_pcts:
                            emotion_pcts[emotion.lower()] = stats.percentage / 100.0  # Convert % to decimal
                    
                    stats = SentimentStats(
                        timestamp=ts,
                        camera_id=cam_uuid,
                        time_window_start=window_start,
                        time_window_end=window_end,
                        total_faces=crowd_sentiment.total_faces_observed,
                        total_faces_observed=crowd_sentiment.total_faces_observed,
                        avg_happy=emotion_pcts.get('happy'),
                        avg_sad=emotion_pcts.get('sad'),
                        avg_angry=emotion_pcts.get('angry'),
                        avg_neutral=emotion_pcts.get('neutral'),
                        avg_surprised=emotion_pcts.get('surprised'),
                        avg_fear=emotion_pcts.get('fear'),
                        avg_disgust=emotion_pcts.get('disgust'),
                        dominant_emotion=crowd_sentiment.dominant_emotion,
                        mood_score=crowd_sentiment.mood_score,
                        emotion_distribution=emotion_dist_dict,
                        trend=crowd_sentiment.trend,
                        trend_magnitude=crowd_sentiment.trend_magnitude
                    )
                    session.add(stats)
            
            logger.info(f"Batch saved {len(sentiments)} crowd sentiments")
            return True
            
        except Exception as e:
            logger.error(f"Error saving sentiment to database: {e}")
            return False
    
    async def batch_save_emotions(self, emotions_data: List[dict]) -> bool:
        """
        Batch save raw emotion records.
        
        Args:
            emotions_data: List of dicts matching EmotionRecord fields
            
        Returns:
            bool: True if saved successfully
        """
        if not emotions_data:
            return True
            
        try:
            async with self.get_session() as session:
                records = []
                for e in emotions_data:
                    # Parse UUID if string
                    cam_id = e['camera_id']
                    if isinstance(cam_id, str):
                        try:
                            cam_id = uuid.UUID(cam_id)
                        except ValueError:
                            continue # Skip invalid
                            
                    record = EmotionRecord(
                        frame_id=str(e.get('frame_id', 'unknown')),
                        face_id=str(e.get('face_id', 'unknown')),
                        emotion=e['emotion'],
                        confidence=float(e['confidence']),
                        camera_id=cam_id,
                        timestamp=e['timestamp'],
                        bounding_box=e.get('bounding_box'),
                        meta_data=e.get('metadata')
                    )
                    records.append(record)
                
                if records:
                    session.add_all(records)
            
            logger.debug(f"Batch saved {len(records)} emotion records")
            return True
        except Exception as e:
            logger.error(f"Error saving emotions to database: {e}")
            return False

    async def get_rules(self) -> list:
        """
        Get all enabled rules from database.
        
        Returns:
            list: List of Rule objects
        """
        try:
            async with self.get_session() as session:
                from sqlalchemy import select
                result = await session.execute(
                    select(Rule).where(Rule.enabled == True).order_by(Rule.type)
                )
                rules = result.scalars().all()
                return rules
        except Exception as e:
            logger.error(f"Error fetching rules: {e}")
            return []
    
    async def save_alert(self, alert_data) -> bool:
        """
        Save alert to database (VANTA-19, Enhanced for VANTA-22).
        
        Args:
            alert_data: Alert object from rules.py
            
        Returns:
            bool: True if saved successfully
        """
        try:
            async with self.get_session() as session:
                # Generate UUID for alert
                import uuid
                alert_id = str(uuid.uuid4())
                
                # Extract relevant fields from sentiment_snapshot
                emotion = alert_data.sentiment_snapshot.get("dominant_emotion")
                
                alert = Alert(
                    id=alert_id,
                    rule_id=str(alert_data.rule_id),
                    camera_id=str(alert_data.camera_id) if alert_data.camera_id else None,
                    alert_type='rule_trigger',
                    emotion=emotion,
                    message=alert_data.message,
                    severity=alert_data.severity,
                    triggered_at=alert_data.timestamp,
                    resolved_at=None,
                    action_taken=None,
                    metadata_json=alert_data.sentiment_snapshot,
                    acknowledged=False
                )
                session.add(alert)
            
            logger.debug(f"Saved alert: {alert_data.rule_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving alert: {e}")
            return False
    
    async def get_alerts(
        self, 
        camera_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        severity: Optional[str] = None,
        limit: int = 100
    ) -> List[dict]:
        """
        Get alerts within time range (VANTA-22).
        
        Args:
            camera_id: Filter by camera ID
            start_time: Start of time range
            end_time: End of time range
            severity: Filter by severity (info, warning, critical)
            limit: Maximum number of results
            
        Returns:
            List of alert dictionaries
        """
        try:
            async with self.get_session() as session:
                query = select(Alert).order_by(Alert.triggered_at.desc())
                
                if camera_id:
                    query = query.where(Alert.camera_id == camera_id)
                if start_time:
                    query = query.where(Alert.triggered_at >= start_time)
                if end_time:
                    query = query.where(Alert.triggered_at <= end_time)
                if severity:
                    query = query.where(Alert.severity == severity)
                
                query = query.limit(limit)
                
                result = await session.execute(query)
                alerts = result.scalars().all()
                
                return [
                    {
                        "id": alert.id,
                        "rule_id": alert.rule_id,
                        "camera_id": alert.camera_id,
                        "alert_type": alert.alert_type,
                        "emotion": alert.emotion,
                        "message": alert.message,
                        "severity": alert.severity,
                        "triggered_at": alert.triggered_at.isoformat() if alert.triggered_at else None,
                        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                        "metadata": alert.metadata_json
                    }
                    for alert in alerts
                ]
        except Exception as e:
            logger.error(f"Error fetching alerts: {e}")
            return []
    
    async def get_severity_distribution(
        self, 
        camera_id: Optional[str] = None,
        period_hours: int = 24
    ) -> dict:
        """
        Get alert count distribution by severity (VANTA-22).
        
        Args:
            camera_id: Filter by camera ID
            period_hours: Time period in hours (default 24h)
            
        Returns:
            Dict with severity counts
        """
        try:
            async with self.get_session() as session:
                start_time = datetime.utcnow() - timedelta(hours=period_hours)
                
                query = select(
                    Alert.severity,
                    func.count(Alert.id).label('count')
                ).where(
                    Alert.triggered_at >= start_time
                ).group_by(Alert.severity)
                
                if camera_id:
                    query = query.where(Alert.camera_id == camera_id)
                
                result = await session.execute(query)
                rows = result.all()
                
                distribution = {
                    "info": 0,
                    "warning": 0,
                    "critical": 0,
                    "total": 0
                }
                
                for severity, count in rows:
                    distribution[severity] = count
                    distribution["total"] += count
                
                return distribution
        except Exception as e:
            logger.error(f"Error getting severity distribution: {e}")
            return {"info": 0, "warning": 0, "critical": 0, "total": 0}
    
    async def get_top_rules(
        self,
        camera_id: Optional[str] = None,
        limit: int = 5,
        period_hours: int = 24
    ) -> List[dict]:
        """
        Get most frequently triggered rules (VANTA-22).
        
        Args:
            camera_id: Filter by camera ID
            limit: Maximum number of rules to return
            period_hours: Time period in hours (default 24h)
            
        Returns:
            List of rules with trigger counts
        """
        try:
            async with self.get_session() as session:
                start_time = datetime.utcnow() - timedelta(hours=period_hours)
                
                query = select(
                    Alert.rule_id,
                    func.count(Alert.id).label('trigger_count')
                ).where(
                    Alert.triggered_at >= start_time
                ).group_by(
                    Alert.rule_id
                ).order_by(
                    func.count(Alert.id).desc()
                ).limit(limit)
                
                if camera_id:
                    query = query.where(Alert.camera_id == camera_id)
                
                result = await session.execute(query)
                rows = result.all()
                
                return [
                    {
                        "rule_id": rule_id,
                        "trigger_count": count
                    }
                    for rule_id, count in rows
                ]
        except Exception as e:
            logger.error(f"Error getting top rules: {e}")
            return []
    
    async def get_emotion_triggers(
        self,
        camera_id: Optional[str] = None,
        period_hours: int = 24
    ) -> dict:
        """
        Get emotion-to-alert correlation (VANTA-22).
        
        Args:
            camera_id: Filter by camera ID
            period_hours: Time period in hours (default 24h)
            
        Returns:
            Dict mapping emotions to alert counts
        """
        try:
            async with self.get_session() as session:
                start_time = datetime.utcnow() - timedelta(hours=period_hours)
                
                query = select(
                    Alert.emotion,
                    func.count(Alert.id).label('count')
                ).where(
                    Alert.triggered_at >= start_time,
                    Alert.emotion.isnot(None)
                ).group_by(
                    Alert.emotion
                ).order_by(
                    func.count(Alert.id).desc()
                )
                
                if camera_id:
                    query = query.where(Alert.camera_id == camera_id)
                
                result = await session.execute(query)
                rows = result.all()
                
                return {
                    emotion: count
                    for emotion, count in rows
                }
        except Exception as e:
            logger.error(f"Error getting emotion triggers: {e}")
            return {}
    
    async def cleanup_old_alerts(self, days: int = 30) -> int:
        """
        Delete alerts older than specified days (VANTA-22).
        
        Args:
            days: Number of days to retain (default 30)
            
        Returns:
            Number of deleted alerts
        """
        try:
            async with self.get_session() as session:
                cutoff_date = datetime.utcnow() - timedelta(days=days)
                
                # Use PostgreSQL function for efficient cleanup
                query = text("SELECT cleanup_old_alerts()")
                result = await session.execute(query)
                deleted_count = result.scalar()
                
                logger.info(f"Deleted {deleted_count} alerts older than {days} days")
                return deleted_count
        except Exception as e:
            logger.error(f"Error cleaning up old alerts: {e}")
            return 0
    
    async def aggregate_alert_metrics(self, hour: datetime) -> bool:
        """
        Aggregate alerts for a specific hour into metrics table (VANTA-22).
        
        Args:
            hour: Hour to aggregate (will be truncated to hour)
            
        Returns:
            True if successful
        """
        try:
            async with self.get_session() as session:
                # Use PostgreSQL function for efficient aggregation
                query = text("SELECT aggregate_alert_metrics(:target_hour)")
                await session.execute(query, {"target_hour": hour})
                
                logger.debug(f"Aggregated alert metrics for {hour}")
                return True
        except Exception as e:
            logger.error(f"Error aggregating alert metrics: {e}")
            return False
