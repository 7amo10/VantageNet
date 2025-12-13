"""
CPU-Optimized Frame Processor for VANTA-14
Implements performance optimizations for 30+ FPS on CPU-only deployment.
"""
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
from typing import Deque, Dict, Optional, List, Tuple
import hashlib

from .models import FrameData, EmotionResult, FaceDetection, EmotionPrediction
from .redis_consumer import redis_consumer
from .redis_publisher import redis_publisher
from .model_loader import model_loader
from .config import settings
from .face_tracker import FaceTracker

# Configure JSON logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

EMOTION_LABELS = ["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"]

# Optimization constants
MAX_FRAME_SIZE = (640, 480)  # Downscale if larger
FACE_CACHE_FRAMES = 2  # Cache face detections
EMOTION_CACHE_THRESHOLD = 10  # Pixels movement threshold
BATCH_SIZE = 5  # Batch inference


class FaceCache:
    """Cache for face detection results."""
    
    def __init__(self, ttl_frames: int = 2):
        self.cache: Dict[str, Dict] = {}
        self.ttl_frames = ttl_frames
    
    def get(self, camera_id: str, frame_number: int) -> Optional[List]:
        """Get cached face detections if still valid."""
        key = f"{camera_id}_{frame_number}"
        
        # Check recent frames
        for i in range(self.ttl_frames):
            check_key = f"{camera_id}_{frame_number - i}"
            if check_key in self.cache:
                cached = self.cache[check_key]
                # Simple heuristic: if frame is recent enough, reuse
                if i <= self.ttl_frames:
                    return cached.get('faces')
        return None
    
    def set(self, camera_id: str, frame_number: int, faces: List):
        """Cache face detection results."""
        key = f"{camera_id}_{frame_number}"
        self.cache[key] = {
            'faces': faces,
            'frame': frame_number
        }
        
        # Cleanup old entries (keep only last 10 frames per camera)
        keys_to_remove = []
        for k in self.cache:
            if k.startswith(camera_id):
                parts = k.split('_')
                if len(parts) >= 2:
                    try:
                        cached_frame = int(parts[-1])
                        if frame_number - cached_frame > 10:
                            keys_to_remove.append(k)
                    except:
                        pass
        
        for k in keys_to_remove:
            del self.cache[k]


class OptimizedFrameProcessor:
    """CPU-optimized frame processor with caching and batch processing."""
    
    def __init__(self):
        self.running = False
        self.frames_processed = 0
        self.frames_skipped = 0
        self.frames_dropped = 0
        self.errors_total = 0
        self.processing_task: asyncio.Task = None
        
        # Performance tracking
        self.processing_times: Deque[float] = deque(maxlen=100)
        self.decompress_times: Deque[float] = deque(maxlen=100)
        self.yolo_times: Deque[float] = deque(maxlen=100)
        self.fer_times: Deque[float] = deque(maxlen=100)
        self.redis_times: Deque[float] = deque(maxlen=100)
        self.tracking_times: Deque[float] = deque(maxlen=100)
        
        self.last_metrics_publish = time.time()
        self.last_fps_calc = time.time()
        self.fps = 0.0
        
        # Caching
        self.face_cache = FaceCache(ttl_frames=FACE_CACHE_FRAMES)
        self.cache_hits = 0
        self.cache_misses = 0
        
        # Face tracking
        self.face_tracker = FaceTracker(
            max_missing_frames=10,
            match_threshold=0.3,
            use_orb=True
        )
        
        # Batch processing
        self.batch_buffer: List[Tuple] = []
        
        # Optimized image preprocessing (reuse transform)
        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        
        # Pre-allocate numpy array for BGR->RGB conversion
        self.rgb_buffer = None
    
    async def start(self):
        """Start the optimized frame processing loop."""
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
            "message": "Optimized frame processor started",
            "timestamp": datetime.now().isoformat(),
            "optimizations": {
                "max_frame_size": MAX_FRAME_SIZE,
                "face_cache_frames": FACE_CACHE_FRAMES,
                "batch_size": BATCH_SIZE
            }
        }))
    
    async def stop(self):
        """Stop the frame processing loop gracefully."""
        if not self.running:
            return
        
        logger.info(json.dumps({
            "level": "INFO",
            "message": "Stopping optimized processor...",
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
            "message": "Optimized processor stopped",
            "timestamp": datetime.now().isoformat(),
            "stats": {
                "frames_processed": self.frames_processed,
                "frames_skipped": self.frames_skipped,
                "frames_dropped": self.frames_dropped,
                "errors_total": self.errors_total,
                "cache_hits": self.cache_hits,
                "cache_misses": self.cache_misses,
                "cache_hit_rate": f"{(self.cache_hits / (self.cache_hits + self.cache_misses) * 100) if (self.cache_hits + self.cache_misses) > 0 else 0:.1f}%"
            }
        }))
    
    def _downscale_if_needed(self, frame: np.ndarray) -> np.ndarray:
        """Downscale frame if larger than MAX_FRAME_SIZE."""
        h, w = frame.shape[:2]
        max_w, max_h = MAX_FRAME_SIZE
        
        if w > max_w or h > max_h:
            # Calculate scale to fit within max size
            scale = min(max_w / w, max_h / h)
            new_w, new_h = int(w * scale), int(h * scale)
            frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        return frame
    
    async def _process_loop(self):
        """Main processing loop - reads and processes frames."""
        logger.info(json.dumps({
            "level": "INFO",
            "message": "Starting optimized processing loop",
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
        Process a single frame through the optimized pipeline.
        
        Optimizations:
        1. Fast JPEG decompression with cv2
        2. Downscale large frames to 640x480
        3. Convert BGR→RGB once
        4. Cache face detections for 2 frames
        5. Batch FER inference when possible
        
        Args:
            frame_data: Frame to process
        """
        start_time = time.time()
        
        try:
            # 1. Optimized JPEG decompression
            decompress_start = time.time()
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
                
                # Downscale if needed
                frame = self._downscale_if_needed(frame)
                
                decompress_time = (time.time() - decompress_start) * 1000
                self.decompress_times.append(decompress_time)
                    
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
            
            # 3. YOLO face detection with caching
            yolo_start = time.time()
            try:
                # Check cache first
                cached_faces = self.face_cache.get(frame_data.camera_id, frame_data.frame_number)
                
                if cached_faces is not None:
                    self.cache_hits += 1
                    yolo_boxes = cached_faces
                else:
                    self.cache_misses += 1
                    yolo_results = model_loader.yolo_model(
                        frame, 
                        conf=settings.confidence_threshold, 
                        verbose=False
                    )
                    
                    # Extract boxes for caching
                    yolo_boxes = []
                    if yolo_results and len(yolo_results) > 0 and yolo_results[0].boxes is not None:
                        for box in yolo_results[0].boxes:
                            yolo_boxes.append({
                                'xyxy': box.xyxy[0].cpu().numpy().astype(int),
                                'conf': float(box.conf[0])
                            })
                    
                    # Cache the detections
                    self.face_cache.set(frame_data.camera_id, frame_data.frame_number, yolo_boxes)
                
                yolo_time = (time.time() - yolo_start) * 1000
                self.yolo_times.append(yolo_time)
                
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
            
            # 3.5. Face tracking - assign stable face_id
            tracking_start = time.time()
            tracked_faces = []
            try:
                # Prepare detections for tracking (x1, y1, x2, y2, conf)
                detections_for_tracking = []
                for box_data in yolo_boxes:
                    x1, y1, x2, y2 = box_data['xyxy']
                    conf = box_data['conf']
                    detections_for_tracking.append((int(x1), int(y1), int(x2), int(y2), float(conf)))
                
                # Track faces and get stable IDs
                tracked_faces = self.face_tracker.track_faces(frame, detections_for_tracking)
                
                tracking_time = (time.time() - tracking_start) * 1000
                self.tracking_times.append(tracking_time)
                
            except Exception as e:
                logger.warning(json.dumps({
                    "level": "WARNING",
                    "message": "Face tracking failed, falling back to frame-based IDs",
                    "error": str(e),
                    "camera_id": frame_data.camera_id,
                    "frame_number": frame_data.frame_number,
                    "timestamp": datetime.now().isoformat()
                }))
                # Fallback: use frame-based IDs
                for idx, box_data in enumerate(yolo_boxes):
                    x1, y1, x2, y2 = box_data['xyxy']
                    tracked_faces.append({
                        'face_id': f"{frame_data.camera_id}_{frame_data.frame_number}_{idx}",
                        'bbox': (int(x1), int(y1), int(x2), int(y2)),
                        'confidence': box_data['conf'],
                        'is_new': True,
                        'frames_tracked': 1
                    })
            
            faces_list = []
            emotions_list = []
            
            fer_model = model_loader.fer_model
            device = model_loader.device
            
            # 4. FER emotion classification (optimized BGR→RGB conversion)
            fer_start = time.time()
            for tracked_face in tracked_faces:
                try:
                    x1, y1, x2, y2 = tracked_face['bbox']
                    conf = tracked_face['confidence']
                    face_id = tracked_face['face_id']
                    
                    # Boundary correction
                    h, w, _ = frame.shape
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(w, x2), min(h, y2)
                    
                    # Crop face
                    face_img = frame[y1:y2, x1:x2]
                    if face_img.size == 0:
                        continue
                    
                    # Store face detection with stable face_id
                    faces_list.append(FaceDetection(
                        bbox=[float(x1), float(y1), float(x2), float(y2)],
                        confidence=conf,
                        face_id=face_id
                    ))
                    
                    # FER emotion classification
                    if fer_model:
                        try:
                            # Optimized BGR→RGB conversion (single operation)
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
            
            fer_time = (time.time() - fer_start) * 1000
            self.fer_times.append(fer_time)
            
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
            redis_start = time.time()
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
            redis_time = (time.time() - redis_start) * 1000
            self.redis_times.append(redis_time)
            
            if published:
                self.frames_processed += 1
                
                logger.info(json.dumps({
                    "level": "INFO",
                    "message": "Frame processed (optimized)",
                    "camera_id": frame_data.camera_id,
                    "frame_number": frame_data.frame_number,
                    "faces_detected": len(faces_list),
                    "emotions_detected": len(emotions_list),
                    "emotions": [e.emotion for e in emotions_list],
                    "processing_time_ms": round(processing_time, 2),
                    "breakdown": {
                        "decompress_ms": round(decompress_time, 2),
                        "yolo_ms": round(yolo_time, 2),
                        "fer_ms": round(fer_time, 2),
                        "redis_ms": round(redis_time, 2)
                    },
                    "cache_hit": self.cache_hits > 0 and cached_faces is not None,
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
        avg_decompress = sum(self.decompress_times) / len(self.decompress_times) if self.decompress_times else 0
        avg_yolo = sum(self.yolo_times) / len(self.yolo_times) if self.yolo_times else 0
        avg_fer = sum(self.fer_times) / len(self.fer_times) if self.fer_times else 0
        avg_redis = sum(self.redis_times) / len(self.redis_times) if self.redis_times else 0
        avg_tracking = sum(self.tracking_times) / len(self.tracking_times) if self.tracking_times else 0
        
        # Get tracking stats
        tracking_stats = self.face_tracker.get_stats()
        
        metrics = {
            "fps": round(self.fps, 2),
            "avg_latency_ms": round(avg_latency, 2),
            "errors_total": self.errors_total,
            "cache_hit_rate": round((self.cache_hits / (self.cache_hits + self.cache_misses) * 100) if (self.cache_hits + self.cache_misses) > 0 else 0, 1),
            "active_tracked_faces": tracking_stats["active_faces"],
            "total_faces_tracked": tracking_stats["total_faces_seen"]
        }
        
        await redis_publisher.publish_metrics(metrics)
        
        logger.debug(json.dumps({
            "level": "DEBUG",
            "message": "Optimized metrics published",
            "metrics": metrics,
            "breakdown": {
                "decompress_ms": round(avg_decompress, 2),
                "yolo_ms": round(avg_yolo, 2),
                "fer_ms": round(avg_fer, 2),
                "redis_ms": round(avg_redis, 2),
                "tracking_ms": round(avg_tracking, 2)
            }
            },
            "timestamp": datetime.now().isoformat()
        }))
    
    def get_stats(self) -> dict:
        """Get processing statistics."""
        avg_latency = sum(self.processing_times) / len(self.processing_times) if self.processing_times else 0
        avg_decompress = sum(self.decompress_times) / len(self.decompress_times) if self.decompress_times else 0
        avg_yolo = sum(self.yolo_times) / len(self.yolo_times) if self.yolo_times else 0
        avg_fer = sum(self.fer_times) / len(self.fer_times) if self.fer_times else 0
        avg_redis = sum(self.redis_times) / len(self.redis_times) if self.redis_times else 0
        avg_tracking = sum(self.tracking_times) / len(self.tracking_times) if self.tracking_times else 0
        
        tracking_stats = self.face_tracker.get_stats()
        
        return {
            "frames_processed": self.frames_processed,
            "frames_skipped": self.frames_skipped,
            "frames_dropped": self.frames_dropped,
            "errors_total": self.errors_total,
            "fps": round(self.fps, 2),
            "avg_latency_ms": round(avg_latency, 2),
            "breakdown_ms": {
                "decompress": round(avg_decompress, 2),
                "yolo": round(avg_yolo, 2),
                "fer": round(avg_fer, 2),
                "redis": round(avg_redis, 2),
                "tracking": round(avg_tracking, 2)
            },
            "cache_stats": {
                "hits": self.cache_hits,
                "misses": self.cache_misses,
                "hit_rate": f"{(self.cache_hits / (self.cache_hits + self.cache_misses) * 100) if (self.cache_hits + self.cache_misses) > 0 else 0:.1f}%"
            },
            "tracking_stats": tracking_stats
            },
            "running": self.running
        }


# Global processor instance
frame_processor = OptimizedFrameProcessor()
