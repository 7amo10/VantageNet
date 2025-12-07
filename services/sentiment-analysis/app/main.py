"""Sentiment Analysis Service - Main FastAPI Application."""
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
import psutil

from fastapi import FastAPI

from .config import settings
from .models import HealthResponse, DatabaseStatus, RedisStatus
from .database import DatabaseManager
from .redis_consumer import RedisConsumer
from .redis_publisher import RedisPublisher
from .aggregator import EmotionAggregator
from .rules_engine import RulesEngine

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global components
db_manager: DatabaseManager = None
redis_consumer: RedisConsumer = None
redis_publisher: RedisPublisher = None
aggregator: EmotionAggregator = None
rules_engine: RulesEngine = None
processor_task: asyncio.Task = None
start_time: datetime = None

# Metrics
emotions_processed = 0
sentiments_published = 0


async def sentiment_processor():
    """Background task for processing emotions and generating sentiment."""
    global emotions_processed, sentiments_published
    
    logger.info("Starting sentiment processor...")
    
    try:
        async for emotion_data in redis_consumer.read_emotions():
            emotions_processed += 1
            
            # Add to aggregator
            aggregator.add_emotion(emotion_data)
            
            logger.debug(
                f"Processed emotion from {emotion_data.camera_id}, "
                f"total processed: {emotions_processed}"
            )
            
            # Check if we can aggregate
            if aggregator.can_aggregate():
                sentiment = aggregator.aggregate()
                
                if sentiment:
                    # Publish sentiment
                    published = await redis_publisher.publish_sentiment(sentiment)
                    if published:
                        sentiments_published += 1
                    
                    # Save to database
                    await db_manager.save_sentiment(sentiment)
                    
                    # Evaluate rules
                    triggered_rules = await rules_engine.evaluate(sentiment)
                    if triggered_rules:
                        logger.info(
                            f"Sentiment triggered {len(triggered_rules)} rule(s): "
                            f"{[r.name for r in triggered_rules]}"
                        )
    
    except asyncio.CancelledError:
        logger.info("Sentiment processor cancelled")
    except Exception as e:
        logger.error(f"Error in sentiment processor: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown.
    
    Handles:
    - Database connection
    - Redis consumer/publisher initialization
    - Aggregator and rules engine setup
    - Background processor task
    """
    global db_manager, redis_consumer, redis_publisher
    global aggregator, rules_engine, processor_task, start_time
    
    # Startup
    logger.info(f"Starting {settings.service_name} v{settings.service_version}")
    start_time = datetime.now()
    
    try:
        # Initialize database
        db_manager = DatabaseManager()
        await db_manager.connect()
        logger.info("Database initialized")
        
        # Initialize Redis components
        redis_consumer = RedisConsumer()
        await redis_consumer.connect()
        logger.info("Redis consumer initialized")
        
        redis_publisher = RedisPublisher()
        await redis_publisher.connect()
        logger.info("Redis publisher initialized")
        
        # Initialize aggregator
        aggregator = EmotionAggregator()
        logger.info("Emotion aggregator initialized")
        
        # Initialize rules engine
        rules_engine = RulesEngine()
        await rules_engine.load_rules_from_database(db_manager)
        logger.info("Rules engine initialized")
        
        # Start background processor
        processor_task = asyncio.create_task(sentiment_processor())
        logger.info("Background sentiment processor started")
        
        logger.info(
            f"Sentiment Analysis Service started successfully on port {settings.port}"
        )
        
        yield
        
    finally:
        # Shutdown
        logger.info("Shutting down Sentiment Analysis Service...")
        
        # Stop processor
        if processor_task:
            processor_task.cancel()
            try:
                await processor_task
            except asyncio.CancelledError:
                pass
        
        # Disconnect components
        if redis_consumer:
            await redis_consumer.disconnect()
        
        if redis_publisher:
            await redis_publisher.disconnect()
        
        if db_manager:
            await db_manager.disconnect()
        
        logger.info("Sentiment Analysis Service stopped")


# Create FastAPI application
app = FastAPI(
    title=settings.service_name,
    version=settings.service_version,
    lifespan=lifespan
)


@app.get("/", tags=["Info"])
async def root():
    """Root endpoint with service information."""
    return {
        "service": settings.service_name,
        "version": settings.service_version,
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "port": settings.port
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health():
    """
    Health check endpoint with detailed component status.
    
    Returns service health, database and Redis connection status,
    and processing metrics.
    """
    # Get database status
    db_status = await db_manager.get_status() if db_manager else {
        "connected": False
    }
    database_status = DatabaseStatus(**db_status)
    
    # Get Redis status
    redis_status = await redis_consumer.get_status() if redis_consumer else {
        "connected": False,
        "input_streams": 0,
        "consumer_group_exists": False
    }
    redis_status_model = RedisStatus(**redis_status)
    
    # Calculate uptime
    uptime_seconds = (datetime.now() - start_time).total_seconds() if start_time else 0
    
    # Get memory usage
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    
    # Get aggregator stats
    aggregator_stats = aggregator.get_buffer_stats() if aggregator else {}
    
    # Get rules engine stats
    rules_stats = rules_engine.get_stats() if rules_engine else {}
    
    # Determine overall health status
    overall_status = "healthy" if (
        database_status.connected and redis_status_model.connected
    ) else "degraded"
    
    return HealthResponse(
        status=overall_status,
        service=settings.service_name,
        version=settings.service_version,
        timestamp=datetime.now(),
        database=database_status,
        redis=redis_status_model,
        metrics={
            "emotions_processed": emotions_processed,
            "sentiments_published": sentiments_published,
            "uptime_seconds": int(uptime_seconds),
            "memory_usage_mb": round(memory_mb, 2),
            "aggregator": aggregator_stats,
            "rules": rules_stats
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        log_level=settings.log_level.lower()
    )

