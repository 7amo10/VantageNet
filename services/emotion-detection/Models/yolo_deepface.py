"""
Real-Time Emotion Detection using YOLOv8 (Face Detection) and DeepFace (Emotion Analysis).

Pipeline:
1. Capture video frame.
2. Detect faces using YOLOv8-Face.
3. Crop the face.
4. Pass the face to DeepFace for emotion analysis.
5. Visualize results.

NOTE: DeepFace is computationally heavy. This script might run at low FPS (Frames Per Second)
on CPU. For production, consider running emotion analysis on a separate thread or 
processing only every 5th frame.
"""

import cv2
import numpy as np
from ultralytics import YOLO
from deepface import DeepFace

# ==========================================
# 1. Configuration
# ==========================================
# Path to the YOLOv8-Face model weights
# Ensure you have 'yolov8n-face.pt' downloaded
YOLO_WEIGHTS = "./yolov8n-face.pt" 

# Initialize YOLO
try:
    print("🔄 Loading YOLO model...")
    yolo_model = YOLO(YOLO_WEIGHTS)
except Exception as e:
    print(f"❌ Error loading YOLO model: {e}")
    exit(1)


def analyze_face_emotion(face_bgr: np.ndarray) -> str:
    """
    Analyzes a cropped face image to determine the dominant emotion using DeepFace.

    Args:
        face_bgr (np.ndarray): Cropped face image in BGR format (OpenCV default).

    Returns:
        str: The dominant emotion (e.g., 'happy', 'sad', 'neutral').
    """
    try:
        # DeepFace.analyze supports BGR images directly (no need to convert to RGB)
        # actions=['emotion'] tells it to only run the emotion model (skips age/gender/race)
        # enforce_detection=False because YOLO has already confirmed there is a face
        result = DeepFace.analyze(
            img_path=face_bgr,
            actions=["emotion"],
            enforce_detection=False,
            detector_backend="skip", # We skip DeepFace's internal detector to save time
            silent=True              # Suppress logging
        )

        # Handle return type: DeepFace returns a list of dicts in newer versions
        if isinstance(result, list):
            result = result[0]
            
        emotion = result.get("dominant_emotion", "unknown")
        
    except Exception as e:
        # DeepFace might throw errors on very small or blurry faces
        # print(f"DeepFace warning: {e}") # Uncomment for debugging
        emotion = "unknown"

    return emotion


def main():
    # Initialize Camera (0 is usually the default webcam)
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("❌ Error: Cannot open camera.")
        return

    print("✅ System Ready. Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Error: Failed to grab frame.")
            break

        # 1. Detect Faces using YOLO
        # stream=True is more efficient for generators
        results = yolo_model(frame, stream=True, verbose=False)

        for r in results:
            if r.boxes is None:
                continue

            for box in r.boxes:
                # Get coordinates
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)

                # Boundary Checks: Ensure box is within the frame
                h, w, _ = frame.shape
                x1 = max(0, min(x1, w - 1))
                x2 = max(0, min(x2, w - 1))
                y1 = max(0, min(y1, h - 1))
                y2 = max(0, min(y2, h - 1))

                # Check if box size is valid
                if x2 <= x1 or y2 <= y1:
                    continue

                # 2. Crop Face
                face_img = frame[y1:y2, x1:x2]
                if face_img.size == 0:
                    continue

                # 3. Analyze Emotion (DeepFace)
                # Note: This is a blocking call and may slow down the video feed
                emotion = analyze_face_emotion(face_img)

                # 4. Draw UI (Bounding Box & Text)
                # Color Format: (B, G, R) -> Green
                color = (0, 255, 0)
                
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                
                # Text Background for better readability
                text_size, _ = cv2.getTextSize(emotion, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                text_w, text_h = text_size
                cv2.rectangle(frame, (x1, y1 - 20), (x1 + text_w, y1), color, -1)
                
                cv2.putText(
                    frame,
                    emotion,
                    (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 0), # Black text
                    2,
                    cv2.LINE_AA,
                )

        # Show Result
        cv2.imshow("YOLOv8 + DeepFace Emotion", frame)

        # Quit logic
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()