"""
Face Tracking Module for VANTA-15
Assigns stable face_id to detected faces across frames using feature matching.
"""
import cv2
import numpy as np
import logging
from typing import Dict, List, Tuple, Optional
from collections import deque
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TrackedFace:
    """Represents a tracked face with persistent ID."""
    face_id: str
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    keypoints: Optional[np.ndarray] = None
    descriptors: Optional[np.ndarray] = None
    last_seen_frame: int = 0
    confidence: float = 0.0
    frames_tracked: int = 0


class FaceTracker:
    """
    Face tracking using Harris corners and ORB descriptors.
    Maintains consistent face_id across frames.
    """
    
    def __init__(
        self,
        max_missing_frames: int = 10,
        match_threshold: float = 0.3,
        use_orb: bool = True
    ):
        """
        Initialize face tracker.
        
        Args:
            max_missing_frames: Remove face_id after N frames without detection
            match_threshold: Similarity threshold for matching (0-1)
            use_orb: Use ORB (True) or SIFT (False) for descriptors
        """
        self.tracked_faces: Dict[str, TrackedFace] = {}
        self.next_face_id = 0
        self.max_missing_frames = max_missing_frames
        self.match_threshold = match_threshold
        self.current_frame_number = 0
        
        # Feature detector/descriptor
        if use_orb:
            self.detector = cv2.ORB_create(nfeatures=500)
            self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        else:
            self.detector = cv2.SIFT_create(nfeatures=500)
            self.matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)
        
        # Harris corner parameters
        self.harris_block_size = 2
        self.harris_ksize = 3
        self.harris_k = 0.04
        self.harris_threshold = 0.01
        
        # Performance tracking
        self.tracking_times = deque(maxlen=100)
        
        logger.info(f"FaceTracker initialized with {'ORB' if use_orb else 'SIFT'} descriptors")
    
    def _extract_features(self, face_img: np.ndarray) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Extract keypoints and descriptors from face ROI.
        
        Args:
            face_img: Face crop (BGR)
            
        Returns:
            (keypoints, descriptors) tuple or (None, None) if extraction fails
        """
        if face_img.size == 0 or face_img.shape[0] < 20 or face_img.shape[1] < 20:
            return None, None
        
        # Convert to grayscale
        gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
        
        # Enhance contrast
        gray = cv2.equalizeHist(gray)
        
        # Detect Harris corners to guide feature detection
        harris = cv2.cornerHarris(
            gray,
            blockSize=self.harris_block_size,
            ksize=self.harris_ksize,
            k=self.harris_k
        )
        
        # Normalize Harris response
        harris = cv2.dilate(harris, None)
        harris_norm = cv2.normalize(harris, None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)
        
        # Create mask for feature detection (focus on Harris corners)
        mask = (harris_norm > self.harris_threshold * 255).astype(np.uint8) * 255
        
        # Detect keypoints and compute descriptors
        try:
            keypoints, descriptors = self.detector.detectAndCompute(gray, mask=mask)
            
            if keypoints is None or len(keypoints) == 0 or descriptors is None:
                # Fallback: try without mask
                keypoints, descriptors = self.detector.detectAndCompute(gray, mask=None)
            
            if keypoints and descriptors is not None and len(descriptors) > 0:
                # Convert keypoints to numpy array for storage
                kp_array = np.array([[kp.pt[0], kp.pt[1]] for kp in keypoints])
                return kp_array, descriptors
            
        except Exception as e:
            logger.warning(f"Feature extraction failed: {e}")
        
        return None, None
    
    def _match_faces(
        self,
        descriptors1: np.ndarray,
        descriptors2: np.ndarray
    ) -> float:
        """
        Compute similarity between two sets of descriptors.
        
        Args:
            descriptors1: First descriptor set
            descriptors2: Second descriptor set
            
        Returns:
            Similarity score (0-1), higher is better match
        """
        if descriptors1 is None or descriptors2 is None:
            return 0.0
        
        if len(descriptors1) == 0 or len(descriptors2) == 0:
            return 0.0
        
        try:
            # KNN matching with k=2 for ratio test
            matches = self.matcher.knnMatch(descriptors1, descriptors2, k=2)
            
            # Apply Lowe's ratio test
            good_matches = []
            for match_pair in matches:
                if len(match_pair) == 2:
                    m, n = match_pair
                    if m.distance < 0.75 * n.distance:
                        good_matches.append(m)
            
            # Calculate match ratio
            if len(descriptors1) > 0:
                match_ratio = len(good_matches) / min(len(descriptors1), len(descriptors2))
                return min(match_ratio, 1.0)
            
        except Exception as e:
            logger.warning(f"Descriptor matching failed: {e}")
        
        return 0.0
    
    def _compute_iou(self, bbox1: Tuple, bbox2: Tuple) -> float:
        """
        Compute Intersection over Union between two bounding boxes.
        
        Args:
            bbox1: (x1, y1, x2, y2)
            bbox2: (x1, y1, x2, y2)
            
        Returns:
            IoU score (0-1)
        """
        x1_1, y1_1, x2_1, y2_1 = bbox1
        x1_2, y1_2, x2_2, y2_2 = bbox2
        
        # Intersection
        x1_i = max(x1_1, x1_2)
        y1_i = max(y1_1, y1_2)
        x2_i = min(x2_1, x2_2)
        y2_i = min(y2_1, y2_2)
        
        if x2_i < x1_i or y2_i < y1_i:
            return 0.0
        
        intersection = (x2_i - x1_i) * (y2_i - y1_i)
        
        # Union
        area1 = (x2_1 - x1_1) * (y2_1 - y1_1)
        area2 = (x2_2 - x1_2) * (y2_2 - y1_2)
        union = area1 + area2 - intersection
        
        return intersection / union if union > 0 else 0.0
    
    def _generate_face_id(self) -> str:
        """Generate unique face ID."""
        face_id = f"face_{self.next_face_id}"
        self.next_face_id += 1
        return face_id
    
    def _cleanup_old_faces(self):
        """Remove faces not seen in max_missing_frames."""
        faces_to_remove = []
        
        for face_id, tracked_face in self.tracked_faces.items():
            frames_missing = self.current_frame_number - tracked_face.last_seen_frame
            if frames_missing > self.max_missing_frames:
                faces_to_remove.append(face_id)
        
        for face_id in faces_to_remove:
            logger.debug(f"Removing {face_id} (not seen for {self.max_missing_frames} frames)")
            del self.tracked_faces[face_id]
    
    def track_faces(
        self,
        frame: np.ndarray,
        detections: List[Tuple[int, int, int, int, float]]
    ) -> List[Dict]:
        """
        Track faces across frames and assign stable face_id.
        
        Args:
            frame: Current frame (BGR)
            detections: List of (x1, y1, x2, y2, confidence) from YOLO
            
        Returns:
            List of dicts with keys: face_id, bbox, confidence, is_new
        """
        import time
        start_time = time.time()
        
        self.current_frame_number += 1
        
        # Cleanup old faces
        self._cleanup_old_faces()
        
        if len(detections) == 0:
            elapsed = (time.time() - start_time) * 1000
            self.tracking_times.append(elapsed)
            return []
        
        # Extract features for all detections
        detection_features = []
        for x1, y1, x2, y2, conf in detections:
            face_crop = frame[y1:y2, x1:x2]
            keypoints, descriptors = self._extract_features(face_crop)
            detection_features.append({
                'bbox': (x1, y1, x2, y2),
                'confidence': conf,
                'keypoints': keypoints,
                'descriptors': descriptors
            })
        
        # Match detections with tracked faces
        tracked_results = []
        matched_face_ids = set()
        matched_detection_indices = set()
        
        # First pass: Match based on descriptors + IoU
        for det_idx, det_feat in enumerate(detection_features):
            best_match_id = None
            best_match_score = 0.0
            
            for face_id, tracked_face in self.tracked_faces.items():
                if face_id in matched_face_ids:
                    continue
                
                # Compute IoU for spatial proximity
                iou = self._compute_iou(det_feat['bbox'], tracked_face.bbox)
                
                # Compute descriptor similarity
                desc_sim = 0.0
                if det_feat['descriptors'] is not None and tracked_face.descriptors is not None:
                    desc_sim = self._match_faces(det_feat['descriptors'], tracked_face.descriptors)
                
                # Combined score (40% descriptor, 60% IoU for better spatial tracking)
                combined_score = 0.4 * desc_sim + 0.6 * iou
                
                if combined_score > best_match_score and combined_score > self.match_threshold:
                    best_match_score = combined_score
                    best_match_id = face_id
            
            # Assign face_id
            if best_match_id:
                # Matched existing face
                tracked_face = self.tracked_faces[best_match_id]
                tracked_face.bbox = det_feat['bbox']
                tracked_face.keypoints = det_feat['keypoints']
                tracked_face.descriptors = det_feat['descriptors']
                tracked_face.last_seen_frame = self.current_frame_number
                tracked_face.confidence = det_feat['confidence']
                tracked_face.frames_tracked += 1
                
                tracked_results.append({
                    'face_id': best_match_id,
                    'bbox': det_feat['bbox'],
                    'confidence': det_feat['confidence'],
                    'is_new': False,
                    'frames_tracked': tracked_face.frames_tracked
                })
                
                matched_face_ids.add(best_match_id)
                matched_detection_indices.add(det_idx)
            else:
                # New face
                new_face_id = self._generate_face_id()
                new_tracked_face = TrackedFace(
                    face_id=new_face_id,
                    bbox=det_feat['bbox'],
                    keypoints=det_feat['keypoints'],
                    descriptors=det_feat['descriptors'],
                    last_seen_frame=self.current_frame_number,
                    confidence=det_feat['confidence'],
                    frames_tracked=1
                )
                
                self.tracked_faces[new_face_id] = new_tracked_face
                
                tracked_results.append({
                    'face_id': new_face_id,
                    'bbox': det_feat['bbox'],
                    'confidence': det_feat['confidence'],
                    'is_new': True,
                    'frames_tracked': 1
                })
                
                matched_detection_indices.add(det_idx)
        
        elapsed = (time.time() - start_time) * 1000
        self.tracking_times.append(elapsed)
        
        return tracked_results
    
    def get_stats(self) -> Dict:
        """Get tracking statistics."""
        avg_time = np.mean(self.tracking_times) if self.tracking_times else 0.0
        
        return {
            "active_faces": len(self.tracked_faces),
            "total_faces_seen": self.next_face_id,
            "avg_tracking_time_ms": round(avg_time, 2),
            "current_frame": self.current_frame_number
        }
    
    def reset(self):
        """Reset tracker state."""
        self.tracked_faces.clear()
        self.next_face_id = 0
        self.current_frame_number = 0
        self.tracking_times.clear()
        logger.info("FaceTracker reset")
