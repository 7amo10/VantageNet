"""Frame processor with dummy processing for Sprint 1."""
import asyncio
import logging
import time
from datetime import datetime
from .models import FrameData
from .redis_consumer import redis_consumer
from .model_loader import model_loader
from .config import settings

logger = logging.getLogger(__name__)


class FrameProcessor:
    """Processes frames from Redis streams."""
    
    def __init__(self):
        self.running = False
        self.frames_processed = 0
        self.frames_skipped = 0
        self.processing_task: asyncio.Task = None
        
    async def start(self):
        """Start the frame processing loop."""
        if self.running:
            logger.warning("Processor already running")
            return
        
        self.running = True
        self.processing_task = asyncio.create_task(self._process_loop())
        logger.info("Frame processor started")
    
    async def stop(self):
        """Stop the frame processing loop gracefully."""
        if not self.running:
            return
        
        logger.info("Stopping frame processor...")
        self.running = False
        
        # Wait for current frame to finish
        if self.processing_task:
            try:
                await asyncio.wait_for(self.processing_task, timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning("Processing task did not complete in time")
                self.processing_task.cancel()
        
        logger.info(f"Frame processor stopped. Processed: {self.frames_processed}, Skipped: {self.frames_skipped}")
    
    async def _process_loop(self):
        """Main processing loop - reads and processes frames."""
        logger.info("Starting frame processing loop...")
        
        try:
            async for frame_data in redis_consumer.read_frames():
                if not self.running:
                    logger.info("Processing loop stopping...")
                    break
                
                # Process every Nth frame
                if frame_data.frame_number % settings.process_every_n_frames != 0:
                    self.frames_skipped += 1
                    continue
                
                # Process the frame (dummy for now)
                await self._process_frame(frame_data)
                
        except asyncio.CancelledError:
            logger.info("Processing loop cancelled")
        except Exception as e:
            logger.error(f"Error in processing loop: {e}")
    
    async def _process_frame(self, frame_data: FrameData):
        """
        Process a single frame (dummy implementation for Sprint 1).
        
        For now, just logs the frame information.
        In Sprint 2, this will do actual face detection and emotion classification.
        
        Args:
            frame_data: Frame to process
        """
        start_time = time.time()
        
        try:
            # Dummy processing - just log frame info
            logger.info(
                f"📸 Frame received | "
                f"Camera: {frame_data.camera_id} | "
                f"Frame: {frame_data.frame_number} | "
                f"Timestamp: {frame_data.timestamp} | "
                f"Size: {frame_data.frame_size_bytes} bytes"
            )
            
            # Simulate some processing time
            await asyncio.sleep(0.01)
            
            self.frames_processed += 1
            
            processing_time = (time.time() - start_time) * 1000
            
            logger.info(
                f"✓ Frame processed | "
                f"Camera: {frame_data.camera_id} | "
                f"Frame: {frame_data.frame_number} | "
                f"Time: {processing_time:.2f}ms | "
                f"Total processed: {self.frames_processed}"
            )
            
            # TODO Sprint 2: Actual processing will be:
            # 1. Decode JPEG frame
            # 2. Run YOLO face detection
            # 3. For each face, run FER emotion classification
            # 4. Publish results to Redis output stream
            
        except Exception as e:
            logger.error(f"Error processing frame {frame_data.frame_number}: {e}")
    
    def get_stats(self) -> dict:
        """Get processing statistics."""
        return {
            "frames_processed": self.frames_processed,
            "frames_skipped": self.frames_skipped,
            "running": self.running
        }


# Global processor instance
frame_processor = FrameProcessor()
