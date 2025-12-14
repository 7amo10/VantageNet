"""PostgreSQL database connection and management."""
import logging
from typing import Optional, List
from contextlib import asynccontextmanager

from sqlalchemy import create_engine, text, Column, Integer, String, Float, Boolean, DateTime, JSON
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
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1000))
    condition = Column(String(1000), nullable=False)
    action = Column(String(255), nullable=False)
    priority = Column(Integer, default=0)
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
    """Sentiment statistics table (VANTA-18)."""
    
    __tablename__ = "sentiment_stats"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    camera_id = Column(String(100), nullable=False, index=True)
    total_faces_observed = Column(Integer, nullable=False)
    emotion_distribution = Column(JSON, nullable=False)
    dominant_emotion = Column(String(50))
    mood_score = Column(Float, nullable=False)
    trend = Column(String(20))
    trend_magnitude = Column(Float)
    
    class Config:
        """SQLAlchemy config."""
        
        indexes = [
            ("timestamp", "camera_id")
        ]


class Alert(Base):
    """Triggered alerts from rules engine."""
    
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    rule_id = Column(String(100), nullable=False)
    rule_name = Column(String(255))
    sentiment_score = Column(Float)
    dominant_emotion = Column(String(50))
    message = Column(String(1000))
    acknowledged = Column(Boolean, default=False)
    acknowledged_at = Column(DateTime)


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
            
            async with self.get_session() as session:
                stats = SentimentStats(
                    timestamp=crowd_sentiment.timestamp,
                    camera_id=crowd_sentiment.camera_id,
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
                    # Convert emotion distribution
                    emotion_dist_dict = {
                        emotion: {
                            "count": stats.count,
                            "avg_confidence": stats.avg_confidence,
                            "percentage": stats.percentage
                        }
                        for emotion, stats in crowd_sentiment.emotion_distribution.items()
                    }
                    
                    stats = SentimentStats(
                        timestamp=crowd_sentiment.timestamp,
                        camera_id=crowd_sentiment.camera_id,
                        total_faces_observed=crowd_sentiment.total_faces_observed,
                        emotion_distribution=emotion_dist_dict,
                        dominant_emotion=crowd_sentiment.dominant_emotion,
                        mood_score=crowd_sentiment.mood_score,
                        trend=crowd_sentiment.trend,
                        trend_magnitude=crowd_sentiment.trend_magnitude
                    )
                    session.add(stats)
            
            logger.info(f"Batch saved {len(sentiments)} crowd sentiments")
            return True
            
        except Exception as e:
            logger.error(f"Error saving sentiment to database: {e}")
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
                    select(Rule).where(Rule.enabled == True).order_by(Rule.priority.desc())
                )
                rules = result.scalars().all()
                return rules
        except Exception as e:
            logger.error(f"Error fetching rules: {e}")
            return []
    
    async def save_alert(self, alert_data) -> bool:
        """
        Save alert to database (VANTA-19).
        
        Args:
            alert_data: Alert object from rules.py
            
        Returns:
            bool: True if saved successfully
        """
        try:
            async with self.get_session() as session:
                # Extract relevant fields from sentiment_snapshot
                sentiment_score = alert_data.sentiment_snapshot.get("mood_score")
                dominant_emotion = alert_data.sentiment_snapshot.get("dominant_emotion")
                
                alert = Alert(
                    timestamp=alert_data.timestamp,
                    rule_id=alert_data.rule_id,
                    rule_name=alert_data.rule_name,
                    sentiment_score=sentiment_score,
                    dominant_emotion=dominant_emotion,
                    message=alert_data.message,
                    acknowledged=False
                )
                session.add(alert)
            
            logger.debug(f"Saved alert: {alert_data.rule_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving alert: {e}")
            return False
