"""Enhanced frame processor with complete pipeline for Sprint 2."""
import asyncio
import logging
import time
import json
import psutil
import numpy as np
import cv2
import torch
from torchvision import transforms
from PIL import Image
from datetime import datetime
from collections import deque
from typing import Deque, Dict
from .models import FrameData, EmotionResult, FaceDetection, EmotionPrediction
from .redis_consumer import redis_consumer
from .redis_publisher import redis_publisher
from .model_loader import model_loader
from .config import settings

# Configure JSON logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

EMOTION_LABELS = ["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"]

class FrameProcessor:
    """Enhanced frame processor with complete emotion detection pipeline."""
    
    def __init__(self):
        self.running = False
        self.frames_processed = 0
        self.frames_skipped = 0
        self.frames_dropped = 0
        self.errors_total = 0
        self.processing_task: asyncio.Task = None
        
        # Performance tracking
        self.processing_times: Deque[float] = deque(maxlen=100)
        self.last_metrics_publish = time.time()
        self.last_fps_calc = time.time()
        self.fps = 0.0
        
        # Image preprocessing transform
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        
    async def start(self):
        """Start the frame processing loop."""
        if self.running:
            logger.warning(json.dumps({
                "level": "WARNING",
                "message": "Processor already running",
                "timestamp": datetime.now().isoformat()
            }))
            return
        
        # Connect publisher
        if not await redis_publisher.connect():
            logger.error(json.dumps({
                "level": "ERROR",
                "message": "Failed to connect publisher",
                "timestamp": datetime.now().isoformat()
            }))
            return
        
        self.running = True
        self.processing_task = asyncio.create_task(self._process_loop())
        
        logger.info(json.dumps({
            "level": "INFO",
            "message": "Frame processor started",
            "timestamp": datetime.now().isoformat(),
            "config": {
                "process_every_n_frames": settings.process_every_n_frames,
                "confidence_threshold": settings.confidence_threshold,
                "emotion_threshold": settings.emotion_threshold
            }
        }))
    
    async def stop(self):
        """Stop the frame processing loop gracefully."""
        if not self.running:
            return
        
        logger.info(json.dumps({
            "level": "INFO",
            "message": "Stopping frame processor...",
            "timestamp": datetime.now().isoformat()
        }))
        
        self.running = False
        
        # Wait for current frame to finish (graceful shutdown)
        if self.processing_task:
            try:
                await asyncio.wait_for(self.processing_task, timeout=10.0)
            except asyncio.TimeoutError:
                logger.warning(json.dumps({
                    "level": "WARNING",
                    "message": "Processing task did not complete in time",
                    "timestamp": datetime.now().isoformat()
                }))
                self.processing_task.cancel()
        
        # Close connections
        await redis_publisher.disconnect()
        
        logger.info(json.dumps({
            "level": "INFO",
            "message": "Frame processor stopped",
            "timestamp": datetime.now().isoformat(),
            "stats": {
                "frames_processed": self.frames_processed,
                "frames_skipped": self.frames_skipped,
                "frames_dropped": self.frames_dropped,
                "errors_total": self.errors_total
            }
        }))
    
    async def _process_loop(self):
        """Main processing loop - reads and processes frames."""
        logger.info(json.dumps({
            "level": "INFO",
            "message": "Starting frame processing loop",
            "timestamp": datetime.now().isoformat()
        }))
        
        try:
            async for frame_data in redis_consumer.read_frames():
                if not self.running:
                    logger.info(json.dumps({
                        "level": "INFO",
                        "message": "Processing loop stopping",
                        "timestamp": datetime.now().isoformat()
                    }))
                    break
                
                # Frame dropping logic based on CPU load
                cpu_load = psutil.cpu_percent(interval=0.1)
                if cpu_load > 80 and frame_data.frame_number % 3 != 0:
                    self.frames_dropped += 1
                    logger.debug(json.dumps({
                        "level": "DEBUG",
                        "message": "Frame dropped due to high CPU load",
                        "cpu_load": cpu_load,
                        "frame_number": frame_data.frame_number,
                        "timestamp": datetime.now().isoformat()
                    }))
                    continue
                
                # Process every Nth frame
                if frame_data.frame_number % settings.process_every_n_frames != 0:
                    self.frames_skipped += 1
                    continue
                
                # Process the frame
                await self._process_frame(frame_data)
                
                # Publish metrics periodically (every 5 seconds)
                if time.time() - self.last_metrics_publish > 5.0:
                    await self._publish_metrics()
                    self.last_metrics_publish = time.time()
                
        except asyncio.CancelledError:
            logger.info(json.dumps({
                "level": "INFO",
                "message": "Processing loop cancelled",
                "timestamp": datetime.now().isoformat()
            }))
        except Exception as e:
            logger.error(json.dumps({
                "level": "ERROR",
                "message": "Error in processing loop",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }), exc_info=True)
    
    async def _process_frame(self, frame_data: FrameData):
        """
        Process a single frame through the complete pipeline.
        
        Pipeline:
        1. Decode JPEG frame
        2. Run YOLO face detection
        3. For each face, run FER emotion classification
        4. Publish results to Redis output stream
        5. Acknowledge message in consumer group
        
        Args:
            frame_data: Frame to process
        """
        start_time = time.time()
        
        try:
            # 1. Decode JPEG frame
            try:
                np_arr = np.frombuffer(frame_data.frame_data, np.uint8)
                frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
                
                if frame is None:
                    logger.error(json.dumps({
                        "level": "ERROR",
                        "message": "Invalid JPEG frame - skipping",
                        "camera_id": frame_data.camera_id,
                        "frame_number": frame_data.frame_number,
                        "timestamp": datetime.now().isoformat()
                    }))
                    self.errors_total += 1
                    return
                    
            except Exception as e:
                logger.error(json.dumps({
                    "level": "ERROR",
                    "message": "Failed to decode frame",
                    "error": str(e),
                    "camera_id": frame_data.camera_id,
                    "frame_number": frame_data.frame_number,
                    "timestamp": datetime.now().isoformat()
                }))
                self.errors_total += 1
                return
            
            # 2. Check if models are loaded
            if not model_loader.yolo_model or not model_loader.fer_model:
                logger.error(json.dumps({
                    "level": "ERROR",
                    "message": "Models not loaded",
                    "timestamp": datetime.now().isoformat()
                }))
                return
            
            # 3. YOLO face detection
            try:
                yolo_results = model_loader.yolo_model(
                    frame, 
                    conf=settings.confidence_threshold, 
                    verbose=False
                )
            except Exception as e:
                logger.error(json.dumps({
                    "level": "ERROR",
                    "message": "YOLO inference failed",
                    "error": str(e),
                    "camera_id": frame_data.camera_id,
                    "frame_number": frame_data.frame_number,
                    "timestamp": datetime.now().isoformat()
                }))
                self.errors_total += 1
                return
            
            faces_list = []
            emotions_list = []
            
            fer_model = model_loader.fer_model
            device = model_loader.device
            
            # 4. For each detected face: run FER classification
            if yolo_results and len(yolo_results) > 0 and yolo_results[0].boxes is not None:
                for box in yolo_results[0].boxes:
                    try:
                        # Get face coordinates
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                        conf = float(box.conf[0])
                        
                        # Boundary correction
                        h, w, _ = frame.shape
                        x1, y1 = max(0, x1), max(0, y1)
                        x2, y2 = min(w, x2), min(h, y2)
                        
                        # Crop face
                        face_img = frame[y1:y2, x1:x2]
                        if face_img.size == 0:
                            continue
                        
                        # Create face ID
                        face_id = f"{frame_data.camera_id}_{frame_data.frame_number}_{len(faces_list)}"
                        
                        # Store face detection
                        faces_list.append(FaceDetection(
                            bbox=[float(x1), float(y1), float(x2), float(y2)],
                            confidence=conf,
                            face_id=face_id
                        ))
                        
                        # FER emotion classification
                        if fer_model:
                            try:
                                # Convert BGR to RGB
                                face_rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
                                
                                # Convert to PIL Image and apply transforms
                                pil_img = Image.fromarray(face_rgb)
                                input_tensor = self.transform(pil_img).unsqueeze(0)
                                
                                # Move to device and run inference
                                input_tensor = input_tensor.to(device)
                                
                                with torch.no_grad():
                                    outputs = fer_model(input_tensor)
                                    probs = torch.nn.functional.softmax(outputs, dim=1)
                                    top_prob, top_idx = torch.max(probs, 1)
                                    
                                    top_prob = top_prob.item()
                                    top_idx = top_idx.item()
                                    predicted_emotion = EMOTION_LABELS[top_idx]
                                
                                # Filter by threshold
                                if top_prob > settings.emotion_threshold:
                                    all_probs = {
                                        EMOTION_LABELS[i]: float(probs[0][i].item()) 
                                        for i in range(len(EMOTION_LABELS))
                                    }
                                    
                                    emotions_list.append(EmotionPrediction(
                                        face_id=face_id,
                                        emotion=predicted_emotion,
                                        confidence=top_prob,
                                        all_emotions=all_probs
                                    ))
                                    
                            except Exception as e:
                                logger.error(json.dumps({
                                    "level": "ERROR",
                                    "message": "FER inference error",
                                    "error": str(e),
                                    "face_id": face_id,
                                    "timestamp": datetime.now().isoformat()
                                }))
                                
                    except Exception as e:
                        logger.error(json.dumps({
                            "level": "ERROR",
                            "message": "Face processing error",
                            "error": str(e),
                            "timestamp": datetime.now().isoformat()
                        }))
                        continue
            
            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000
            self.processing_times.append(processing_time)
            
            # Check for timeout (> 100ms)
            if processing_time > 100:
                logger.warning(json.dumps({
                    "level": "WARNING",
                    "message": "Frame processing exceeded 100ms",
                    "processing_time_ms": processing_time,
                    "camera_id": frame_data.camera_id,
                    "frame_number": frame_data.frame_number,
                    "timestamp": datetime.now().isoformat()
                }))
                self.frames_dropped += 1
            
            # 5. Publish results to Redis
            result = EmotionResult(
                camera_id=frame_data.camera_id,
                frame_number=frame_data.frame_number,
                timestamp=frame_data.timestamp,
                processed_at=datetime.now().isoformat(),
                faces_detected=len(faces_list),
                faces=faces_list,
                emotions=emotions_list,
                processing_time_ms=processing_time
            )
            
            published = await redis_publisher.publish_result(result)
            
            if published:
                self.frames_processed += 1
                
                logger.info(json.dumps({
                    "level": "INFO",
                    "message": "Frame processed",
                    "camera_id": frame_data.camera_id,
                    "frame_number": frame_data.frame_number,
                    "faces_detected": len(faces_list),
                    "emotions_detected": len(emotions_list),
                    "emotions": [e.emotion for e in emotions_list],
                    "processing_time_ms": round(processing_time, 2),
                    "timestamp": datetime.now().isoformat()
                }))
            else:
                logger.error(json.dumps({
                    "level": "ERROR",
                    "message": "Failed to publish result",
                    "camera_id": frame_data.camera_id,
                    "frame_number": frame_data.frame_number,
                    "timestamp": datetime.now().isoformat()
                }))
                self.errors_total += 1
            
            # Calculate FPS
            if time.time() - self.last_fps_calc >= 1.0:
                self.fps = self.frames_processed / (time.time() - self.last_fps_calc)
                self.last_fps_calc = time.time()
                self.frames_processed = 0
                
        except Exception as e:
            logger.error(json.dumps({
                "level": "ERROR",
                "message": "Unexpected error processing frame",
                "error": str(e),
                "camera_id": frame_data.camera_id if frame_data else "unknown",
                "frame_number": frame_data.frame_number if frame_data else 0,
                "timestamp": datetime.now().isoformat()
            }), exc_info=True)
            self.errors_total += 1
    
    async def _publish_metrics(self):
        """Publish performance metrics to Redis."""
        avg_latency = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
        
        metrics = {
            "fps": round(self.fps, 2),
            "avg_latency_ms": round(avg_latency, 2),
            "errors_total": self.errors_total
        }
        
        await redis_publisher.publish_metrics(metrics)
        
        logger.debug(json.dumps({
            "level": "DEBUG",
            "message": "Metrics published",
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }))
    
    def get_stats(self) -> dict:
        """Get processing statistics."""
        avg_latency = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
        
        return {
            "frames_processed": self.frames_processed,
            "frames_skipped": self.frames_skipped,
            "frames_dropped": self.frames_dropped,
            "errors_total": self.errors_total,
            "fps": round(self.fps, 2),
            "avg_latency_ms": round(avg_latency, 2),
            "running": self.running
        }


# Global processor instance
frame_processor = FrameProcessor()
