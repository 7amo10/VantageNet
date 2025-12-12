"""Frame processor with dummy processing for Sprint 1."""
import asyncio
import logging
import time
import numpy as np
import cv2
import torch
from torchvision import transforms
from PIL import Image
from datetime import datetime
from .models import FrameData, EmotionResult, FaceDetection, EmotionPrediction
from .redis_consumer import redis_consumer
from .model_loader import model_loader
from .config import settings

logger = logging.getLogger(__name__)

EMOTION_LABELS = ["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"]
class FrameProcessor:
    """Processes frames from Redis streams."""
    
    def __init__(self):
        self.running = False
        self.frames_processed = 0
        self.frames_skipped = 0
        self.processing_task: asyncio.Task = None

        self.transform = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        
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
    
    # async def _process_frame(self, frame_data: FrameData):
    #     """
    #     Process a single frame (dummy implementation for Sprint 1).
        
    #     For now, just logs the frame information.
    #     In Sprint 2, this will do actual face detection and emotion classification.
        
    #     Args:
    #         frame_data: Frame to process
    #     """
    #     start_time = time.time()
        
    #     try:
    #         # Dummy processing - just log frame info
    #         logger.info(
    #             f"📸 Frame received | "
    #             f"Camera: {frame_data.camera_id} | "
    #             f"Frame: {frame_data.frame_number} | "
    #             f"Timestamp: {frame_data.timestamp} | "
    #             f"Size: {frame_data.frame_size_bytes} bytes"
    #         )
            
    #         # Simulate some processing time
    #         await asyncio.sleep(0.01)
            
    #         self.frames_processed += 1
            
    #         processing_time = (time.time() - start_time) * 1000
            
    #         logger.info(
    #             f"✓ Frame processed | "
    #             f"Camera: {frame_data.camera_id} | "
    #             f"Frame: {frame_data.frame_number} | "
    #             f"Time: {processing_time:.2f}ms | "
    #             f"Total processed: {self.frames_processed}"
    #         )
            
    #         # TODO Sprint 2: Actual processing will be:
    #         # 1. Decode JPEG frame
    #         # 2. Run YOLO face detection
    #         # 3. For each face, run FER emotion classification
    #         # 4. Publish results to Redis output stream
            
    #     except Exception as e:
    #         logger.error(f"Error processing frame {frame_data.frame_number}: {e}")
    

    async def _process_frame(self, frame_data: FrameData):
        start_time = time.time()
        try:
            # 1. Decode Frame
            np_arr = np.frombuffer(frame_data.frame_data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if frame is None: return

            # 2. YOLO Detection
            if not model_loader.yolo_model: return
            
            # تشغيل YOLO
            yolo_results = model_loader.yolo_model(frame, conf=settings.confidence_threshold, verbose=False)
            
            faces_list = []
            emotions_list = []
            
            # تجهيز الموديل (EfficientNet)
            fer_model = model_loader.fer_model
            device = model_loader.device

            # 3. Loop over faces
            for box in yolo_results[0].boxes:
                # إحداثيات الوجه
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                conf = float(box.conf[0])
                
                # تصحيح الحدود
                h, w, _ = frame.shape
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w, x2), min(h, y2)
                
                face_img = frame[y1:y2, x1:x2]
                if face_img.size == 0: continue
                
                # حفظ بيانات الوجه
                face_id = f"{frame_data.camera_id}_{frame_data.frame_number}_{len(faces_list)}"
                faces_list.append(FaceDetection(
                    bbox=[float(x1), float(y1), float(x2), float(y2)],
                    confidence=conf,
                    face_id=face_id
                ))

                # --- 4. EfficientNet Inference ---
                if fer_model:
                    try:
                        # أ. تحويل من BGR (OpenCV) إلى RGB
                        face_rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
                        
                        # ب. تحويل لـ PIL Image ثم تطبيق الـ Transform
                        pil_img = Image.fromarray(face_rgb)
                        input_tensor = self.transform(pil_img).unsqueeze(0) # إضافة Batch Dimension [1, 3, 224, 224]
                        
                        # ج. النقل للـ Device وتشغيل الموديل
                        input_tensor = input_tensor.to(device)
                        
                        with torch.no_grad():
                            outputs = fer_model(input_tensor)
                            # تحويل الـ Logits لاحتمالات باستخدام Softmax
                            probs = torch.nn.functional.softmax(outputs, dim=1)
                            
                            # الحصول على أعلى احتمال
                            top_prob, top_idx = torch.max(probs, 1)
                            
                            top_prob = top_prob.item()
                            top_idx = top_idx.item()
                            
                            predicted_emotion = EMOTION_LABELS[top_idx]

                        # د. التصفية وحفظ النتيجة
                        if top_prob > settings.emotion_threshold:
                            # تحويل جميع الاحتمالات لـ Dictionary
                            all_probs = {EMOTION_LABELS[i]: float(probs[0][i].item()) for i in range(len(EMOTION_LABELS))}
                            
                            emotions_list.append(EmotionPrediction(
                                face_id=face_id,
                                emotion=predicted_emotion,
                                confidence=top_prob,
                                all_emotions=all_probs
                            ))
                            
                    except Exception as e:
                        logger.error(f"FER Inference error: {e}")

            # 5. Final Output
            processing_time = (time.time() - start_time) * 1000
            
            # يمكنك هنا طباعة النتيجة أو إرسالها لـ Redis Output
            logger.info(
                f"✅ Frame: {frame_data.frame_number} | "
                f"Faces: {len(faces_list)} | "
                f"Emotion: {[e.emotion for e in emotions_list]} | "
                f"Time: {processing_time:.1f}ms"
            )
            
            self.frames_processed += 1
            
        except Exception as e:
            logger.error(f"Processing error: {e}")


            
    def get_stats(self) -> dict:
        """Get processing statistics."""
        return {
            "frames_processed": self.frames_processed,
            "frames_skipped": self.frames_skipped,
            "running": self.running
        }


# Global processor instance
frame_processor = FrameProcessor()
