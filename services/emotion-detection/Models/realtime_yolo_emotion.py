import cv2
import torch
import torch.nn as nn
import numpy as np
from torchvision import transforms
from ultralytics import YOLO

# ==========================================
# 1. Model Architecture Definition
# (Must match the training architecture exactly)
# ==========================================

class ConvBlock(nn.Module):
    def __init__(self, in_channels: int, out_channels: int):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),

            nn.MaxPool2d(2),
        )

    def forward(self, x):
        return self.block(x)


class EmotionCNN(nn.Module):
    def __init__(self, num_classes: int = 7):
        super().__init__()
        self.features = nn.Sequential(
            ConvBlock(1, 32),    # 48x48 -> 24x24
            ConvBlock(32, 64),   # 24x24 -> 12x12
            ConvBlock(64, 128),  # 12x12 -> 6x6
            ConvBlock(128, 256), # 6x6 -> 3x3
        )
        self.global_pool = nn.AdaptiveAvgPool2d((1, 1))
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(0.5),
            nn.Linear(256, num_classes)
        )

    def forward(self, x):
        x = self.features(x)
        x = self.global_pool(x)
        x = self.classifier(x)
        return x

# ==========================================
# 2. Setup and Configuration
# ==========================================

# Class names must follow the alphabetical order of training folders
CLASS_NAMES = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']

# Select device
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Running on: {device}")

# ==========================================
# 3. Load Models
# ==========================================

# --- A. Load Custom Emotion CNN ---
model_path = "services/emotion-detection/Models/results/emotion_model_best (1).pt"  # Ensure this file is in the same directory
emotion_model = EmotionCNN(num_classes=7).to(device)

try:
    emotion_model.load_state_dict(torch.load(model_path, map_location=device))
    print("Emotion model loaded successfully.")
except FileNotFoundError:
    print(f"Error: '{model_path}' not found. Please download it from Colab.")
    exit()

emotion_model.eval()

# --- B. Load YOLO for Face Detection ---
# 'yolov8n-face.pt' is optimized for faces. If not found, it might download or error out.
# You can use standard 'yolov8n.pt' as a fallback, though less accurate for close-ups.
try:
    yolo_model = YOLO("yolov8n-face.pt") 
    print("Using YOLOv8-Face model.")
except:
    print("Warning: yolov8n-face not found, falling back to standard yolov8n.")
    yolo_model = YOLO("yolov8n.pt")

# ==========================================
# 4. Preprocessing Transforms
# ==========================================
# Prepares the cropped face for the CNN (Grayscale -> Resize -> Normalize)
val_transform = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Grayscale(num_output_channels=1),
    transforms.Resize((48, 48)),
    transforms.ToTensor(),
    transforms.Normalize((0.5,), (0.5,)),
])

# ==========================================
# 5. Real-time Inference Loop
# ==========================================
cap = cv2.VideoCapture(0) # 0 is usually the default webcam

if not cap.isOpened():
    print("Error: Cannot open camera.")
    exit()

print("Starting video stream. Press 'q' to exit.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # 1. Detect faces using YOLO
    # verbose=False suppresses YOLO's log printing to console
    results = yolo_model(frame, verbose=False)
    
    for result in results:
        boxes = result.boxes
        for box in boxes:
            # Get box coordinates
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
            
            # Ensure coordinates are within frame boundaries
            h, w, _ = frame.shape
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            
            # Crop the face
            face_img = frame[y1:y2, x1:x2]
            
            # Skip if crop is empty (e.g., face on the very edge)
            if face_img.size == 0:
                continue

            try:
                # 2. Preprocess face for Emotion Model
                face_tensor = val_transform(face_img).unsqueeze(0).to(device) # Add batch dim: [1, 1, 48, 48]
                
                # 3. Predict Emotion
                with torch.no_grad():
                    outputs = emotion_model(face_tensor)
                    probs = torch.softmax(outputs, dim=1)
                    conf, predicted = torch.max(probs, 1)
                    
                    emotion_label = CLASS_NAMES[predicted.item()]
                    confidence = conf.item()

                # 4. Draw Bounding Box and Label
                color = (0, 255, 0) # Green color (B, G, R)
                
                # Draw rectangle around face
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                
                # Display text label with confidence
                text = f"{emotion_label} ({confidence*100:.1f}%)"
                cv2.putText(frame, text, (x1, y1 - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                           
            except Exception as e:
                # Catch errors during processing (e.g., weird tensor shapes)
                print(f"Error processing face: {e}")

    # Display the resulting frame
    cv2.imshow('Emotion Detection (YOLO + CNN)', frame)

    # Break loop on 'q' key press
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Cleanup
cap.release()
cv2.destroyAllWindows()