"""Model loading and management for YOLO and DeepFace."""
import logging
import psutil
from typing import Optional, Dict
import torch
from ultralytics import YOLO
from .config import settings
from .models import ModelStatus
import torch.nn as nn
from torchvision import models
logger = logging.getLogger(__name__)

class EmotionEfficientNet(nn.Module):
    def __init__(self, num_classes=7):
        super(EmotionEfficientNet, self).__init__()
        # تحميل الهيكل فقط بدون أوزان ImageNet لأننا سنحمل أوزانك الخاصة
        self.base_model = models.efficientnet_b0(weights=None)
        
        in_features = self.base_model.classifier[1].in_features
        self.base_model.classifier[1] = nn.Sequential(
            nn.Dropout(p=0.3),
            nn.Linear(in_features, num_classes)
        )

    def forward(self, x):
        return self.base_model(x)
    


class ModelLoader:
    """Manages loading and lifecycle of ML models."""
    
    def __init__(self):
        self.yolo_model: Optional[YOLO] = None
        self.fer_model: Optional[any] = None
        self.device: str = "cpu"
        self.models_loaded: bool = False
        self.load_errors: Dict[str, str] = {}
        
    def get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    
    async def load_models(self) -> bool:
        """
        Load YOLOv8 and FER models into memory.
        
        Returns:
            True if all models loaded successfully
        """
        initial_memory = self.get_memory_usage()
        logger.info(f"Initial memory usage: {initial_memory:.2f} MB")
        
        # Determine device
        self.device = self._determine_device()
        logger.info(f"Using device: {self.device}")
        
        # Load YOLO face detection model
        yolo_success = await self._load_yolo()
        
        # Load FER model
        fer_success = await self._load_fer()
        
        final_memory = self.get_memory_usage()
        memory_increase = final_memory - initial_memory
        
        logger.info(f"Final memory usage: {final_memory:.2f} MB (+{memory_increase:.2f} MB)")
        
        if final_memory > settings.max_memory_mb:
            logger.warning(
                f"Memory usage ({final_memory:.2f} MB) exceeds limit ({settings.max_memory_mb} MB)"
            )
        
        self.models_loaded = yolo_success and fer_success
        return self.models_loaded
    
    def _determine_device(self) -> str:
        """Determine which device to use for inference."""
        if settings.use_cuda and torch.cuda.is_available():
            return "cuda"
        return "cpu"
    
    async def _load_yolo(self) -> bool:
        """Load YOLOv8 face detection model."""
        try:
            logger.info(f"Loading YOLO model from {settings.yolo_model_path}")
            
            # Load model
            self.yolo_model = YOLO(settings.yolo_model_path)
            
            # Move to device
            if self.device == "cuda":
                self.yolo_model.to("cuda")
            
            logger.info("✓ YOLO model loaded successfully")
            return True
            
        except Exception as e:
            error_msg = f"Failed to load YOLO model: {e}"
            logger.error(error_msg)
            self.load_errors["yolo"] = str(e)
            return False
    
    async def _load_fer(self) -> bool:
        """Load FER (Facial Expression Recognition) model using DeepFace."""
        try:
            logger.info("Loading DeepFace emotion model...")
            
            # Import DeepFace
            from deepface import DeepFace
            
            # Pre-load model by running a dummy prediction
            # This forces DeepFace to download and cache the model
            import numpy as np
            dummy_img = np.zeros((224, 224, 3), dtype=np.uint8)
            
            try:
                # This will download the model if not cached
                _ = DeepFace.analyze(
                    img_path=dummy_img,
                    actions=['emotion'],
                    detector_backend='skip',  # Skip detection since YOLO handles it
                    enforce_detection=False,
                    silent=True
                )
            except:
                # Expected to fail on dummy image, but model should now be cached
                pass
            
            self.fer_model = "deepface"  # DeepFace doesn't return model object, use marker
            logger.info("✓ DeepFace emotion model loaded successfully")
            return True
            
        except Exception as e:
            error_msg = f"Failed to load DeepFace model: {e}"
            logger.error(error_msg)
            self.load_errors["fer"] = str(e)
            return False
    
    def get_model_status(self) -> list[ModelStatus]:
        """Get status of all loaded models."""
        current_memory = self.get_memory_usage()
        
        # return [
        #     ModelStatus(
        #         name="YOLOv8-face",
        #         loaded=self.yolo_model is not None,
        #         memory_mb=current_memory / 2 if self.yolo_model else None,
        #         error=self.load_errors.get("yolo")
        #     ),
        #     ModelStatus(
        #         name="FER (DeepFace)",
        #         loaded=self.fer_model is not None,
        #         memory_mb=current_memory / 2 if self.fer_model else None,
        #         error=self.load_errors.get("fer")
        #     )
        # ]

        mem = self.get_memory_usage()
        return [
            ModelStatus(name="YOLOv8-face", loaded=self.yolo_model is not None, memory_mb=mem/2),
            ModelStatus(name="DeepFace-emotion", loaded=self.fer_model is not None, memory_mb=mem/2)
        ]
    

    
    
    def unload_models(self):
        """Unload models and free memory."""
        logger.info("Unloading models...")
        
        if self.yolo_model:
            del self.yolo_model
            self.yolo_model = None
        
        if self.fer_model:
            del self.fer_model
            self.fer_model = None
        
        # Clear CUDA cache if using GPU
        if self.device == "cuda":
            torch.cuda.empty_cache()
        
        self.models_loaded = False
        logger.info("Models unloaded")


# Global model loader instance
model_loader = ModelLoader()
