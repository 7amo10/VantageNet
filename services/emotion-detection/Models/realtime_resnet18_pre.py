"""
Real-Time Emotion Detection Module using YOLOv8 and EfficientNet-B0.

This script performs real-time emotion recognition on a video feed (webcam or video file).
It integrates two deep learning models:
1. **YOLOv8 (Face)**: Detects faces in each video frame.
2. **EfficientNet-B0**: Classifies the cropped face into one of 7 emotion categories.

Pipeline:
    1. Capture frame from video source.
    2. Detect faces using YOLOv8.
    3. Crop the detected face region.
    4. Preprocess the face image (Resize to 224x224, Grayscale to 3-channel, Normalize).
    5. Pass the processed face to the loaded EfficientNet model for inference.
    6. Draw bounding boxes and predicted emotion labels on the original frame.

Dependencies:
    - opencv-python (cv2)
    - torch
    - torchvision
    - ultralytics (YOLO)
    - numpy

Usage:
    Ensure the model weight paths (EFFICIENTNET_WEIGHTS, YOLO_WEIGHTS) are correct.
    Run the script directly to start the webcam feed.
"""

import cv2
import torch
import torch.nn as nn
from torchvision import models, transforms
from ultralytics import YOLO
import numpy as np

# ==========================================
# 1. General Settings
# ==========================================
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# Same number of classes used during EfficientNet training
NUM_CLASSES = 7

# Ensure label order matches the ImageFolder structure (usually alphabetical):
# angry, disgust, fear, happy, neutral, sad, surprise
EMOTION_LABELS = ["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"]

# Paths
EFFICIENTNET_WEIGHTS = "services/emotion-detection/Models/results/efficientnet_emotion (2).pt"   # عدّل لو حاطه في مكان تاني
YOLO_WEIGHTS         = "services/emotion-detection/Models/yolov8n-face.pt"           # أو "yolov8n-face.pt" لو في نفس الفولدر


# ==========================================
# 2. EfficientNet-B0 Model (Same architecture as trained)
# ==========================================
class EmotionEfficientNet(nn.Module):
    def __init__(self, num_classes=7, pretrained=False):
        super(EmotionEfficientNet, self).__init__()

        if pretrained:
            weights = models.EfficientNet_B0_Weights.DEFAULT
        else:
            weights = None

        self.base_model = models.efficientnet_b0(weights=weights)

        # Modify the classifier to match our number of classes
        in_features = self.base_model.classifier[1].in_features
        self.base_model.classifier[1] = nn.Sequential(
            nn.Dropout(p=0.3),
            nn.Linear(in_features, num_classes)
        )

    def forward(self, x):
        return self.base_model(x)


def load_emotion_model(weights_path: str):
    """
    Initializes the model architecture and loads the saved state dictionary.
    """
    model = EmotionEfficientNet(num_classes=NUM_CLASSES, pretrained=False)
    state = torch.load(weights_path, map_location=DEVICE)
    model.load_state_dict(state)
    model.to(DEVICE)
    model.eval()
    return model


# ==========================================
# 3. YOLO Model + Image Transforms
# ==========================================
print("🔄 Loading YOLO face model...")
yolo_model = YOLO(YOLO_WEIGHTS)

print("🔄 Loading EfficientNet emotion model...")
emotion_model = load_emotion_model(EFFICIENTNET_WEIGHTS)

# Transform for the face image before passing to EfficientNet
face_transform = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Grayscale(num_output_channels=3),
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],   # Same normalization used in training
        std=[0.229, 0.224, 0.225],
    ),
])


def predict_emotion(face_bgr: np.ndarray) -> str:
    """
    Predicts emotion from a cropped face image.

    Args:
        face_bgr: Cropped face image from OpenCV (BGR format).

    Returns:
        str: Predicted emotion label.
    """
    if face_bgr is None or face_bgr.size == 0:
        return "unknown"

    # Convert BGR -> RGB
    face_rgb = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2RGB)

    # Preprocess and convert to Tensor
    img = face_transform(face_rgb).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        outputs = emotion_model(img)
        _, pred = torch.max(outputs, 1)
        idx = pred.item()

    # Safety check for index out of bounds
    if idx < 0 or idx >= len(EMOTION_LABELS):
        return "unknown"

    return EMOTION_LABELS[idx]


# ==========================================
# 4. Real-Time Loop
# ==========================================
def main():
    # If running on local machine (Webcam):
    cap = cv2.VideoCapture(0)

    # If running on Colab or without a camera, use a video file:
    # cap = cv2.VideoCapture("/content/your_video.mp4")

    if not cap.isOpened():
        print("❌ Cannot open camera / video.")
        return

    print("✅ Running... Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Run YOLO on the frame (stream=True for generator efficiency)
        results = yolo_model(frame, stream=True, verbose=False)

        for r in results:
            if r.boxes is None:
                continue

            for box in r.boxes:
                xyxy = box.xyxy[0].cpu().numpy()
                x1, y1, x2, y2 = map(int, xyxy)

                h, w, _ = frame.shape
                # Ensure coordinates are within frame bounds
                x1 = max(0, min(x1, w - 1))
                x2 = max(0, min(x2, w - 1))
                y1 = max(0, min(y1, h - 1))
                y2 = max(0, min(y2, h - 1))

                if x2 <= x1 or y2 <= y1:
                    continue

                face = frame[y1:y2, x1:x2]
                if face.size == 0:
                    continue

                emotion = predict_emotion(face)

                # Draw bounding box and label
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
                cv2.putText(
                    frame,
                    emotion,
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 255),
                    2,
                    cv2.LINE_AA,
                )

        cv2.imshow("YOLO + EfficientNet Emotion", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()