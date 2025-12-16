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
from .crowd_processor import CrowdSentimentProcessor

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
crowd_processor: CrowdSentimentProcessor = None
start_time: datetime = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown (VANTA-18).
    
    Handles:
    - Database connection
    - Redis consumer/publisher initialization
    - Crowd sentiment processor setup
    """
    global db_manager, redis_consumer, redis_publisher
    global crowd_processor, start_time
    
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
        
        # Initialize crowd sentiment processor (VANTA-18)
        crowd_processor = CrowdSentimentProcessor(
            redis_consumer=redis_consumer,
            redis_publisher=redis_publisher,
            db_manager=db_manager,
            window_seconds=30,  # 30s sliding window
            publish_interval=30  # Publish every 30s
        )
        await crowd_processor.start()
        logger.info("Crowd sentiment processor initialized and started")
        
        logger.info(
            f"Sentiment Analysis Service started successfully on port {settings.port}"
        )
        
        yield
        
    finally:
        # Shutdown
        logger.info("Shutting down Sentiment Analysis Service...")
        
        # Stop processor
        if crowd_processor:
            await crowd_processor.stop()
        
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
    Health check endpoint with detailed component status (VANTA-18).
    
    Returns service health, database and Redis connection status,
    and crowd sentiment processing metrics.
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
    
    # Get processor metrics
    processor_metrics = crowd_processor.get_metrics() if crowd_processor else {}
    
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
            "uptime_seconds": int(uptime_seconds),
            "memory_usage_mb": round(memory_mb, 2),
            **processor_metrics
        }
    )


@app.post("/reload-rules", tags=["Admin"])
async def reload_rules():
    """
    Reload rules from database (VANTA-24).
    
    Useful for testing - allows reloading rules without restarting the service.
    """
    if not crowd_processor or not crowd_processor.rules_engine:
        return {"error": "Rules engine not initialized"}
    
    try:
        await crowd_processor.rules_engine.load_rules()
        rule_count = len(crowd_processor.rules_engine.rules)
        logger.info(f"Reloaded {rule_count} rules from database")
        return {
            "status": "success",
            "rules_loaded": rule_count,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to reload rules: {e}")
        return {"error": str(e)}

@app.post("/trigger-aggregation", tags=["Admin"])
async def trigger_aggregation():
    """
    Manually trigger sentiment aggregation and rule evaluation (VANTA-24).
    
    Useful for testing - forces immediate aggregation without waiting for 30s timer.
    Also rediscovers streams to pick up new test cameras.
    """
    if not crowd_processor:
        return {"error": "Crowd processor not initialized"}
    
    if not redis_consumer:
        return {"error": "Redis consumer not initialized"}
    
    try:
        # First, rediscover streams to pick up any new test streams
        await redis_consumer.rediscover_streams()
        logger.info("Rediscovered streams before aggregation")
        
        # Wait a moment for any pending messages to be consumed
        await asyncio.sleep(2)
        
        # Now trigger aggregation
        await crowd_processor.trigger_aggregation()
        metrics = crowd_processor.get_metrics()
        logger.info("Manual aggregation completed")
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "streams_discovered": len(redis_consumer._streams) if redis_consumer else 0,
            "metrics": metrics
        }
    except Exception as e:
        logger.error(f"Failed to trigger aggregation: {e}")
        return {"error": str(e)}