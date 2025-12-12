import cv2
import torch
import torch.nn as nn
import numpy as np
from torchvision import transforms
from ultralytics import YOLO
from collections import deque, Counter # Imported for smoothing

# ==========================================
# 1. Model Architecture (Must match exactly)
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
            ConvBlock(1, 32),
            ConvBlock(32, 64),
            ConvBlock(64, 128),
            ConvBlock(128, 256),
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
# 2. Setup
# ==========================================
CLASS_NAMES = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Running on: {device}")

# --- Load Emotion Model ---
# NOTE: Ensure the path is correct
model_path = "services/emotion-detection/Models/results/emotion_model_best (1).pt"
emotion_model = EmotionCNN(num_classes=7).to(device)

try:
    emotion_model.load_state_dict(torch.load(model_path, map_location=device))
    emotion_model.eval()
    print("✅ Emotion model loaded.")
except FileNotFoundError:
    print(f"❌ Error: '{model_path}' not found.")
    exit()

# --- Load YOLO ---
try:
    yolo_model = YOLO("yolov8n-face.pt") 
    print("✅ Using YOLOv8-Face.")
except:
    print("⚠️ yolov8n-face not found, using standard yolov8n.")
    yolo_model = YOLO("yolov8n.pt")

# --- Preprocessing ---
val_transform = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Grayscale(num_output_channels=1),
    transforms.Resize((48, 48)),
    transforms.ToTensor(),
    transforms.Normalize((0.5,), (0.5,)),
])

# ==========================================
# 3. Helper Functions
# ==========================================

# Buffer to store the last 10 predictions (Stabilizes output)
emotion_buffer = deque(maxlen=10)

def get_dominant_emotion(buffer):
    if not buffer: return "Computing...", 0.0
    # Count the most frequent emotion in the buffer
    counts = Counter(buffer)
    most_common, count = counts.most_common(1)[0]
    # Return emotion and 'stability' score
    return most_common, count / len(buffer)

# ==========================================
# 4. Main Loop
# ==========================================
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Cannot open camera.")
    exit()

print("\n🎥 Starting stream... Press 'q' to exit.")

while True:
    ret, frame = cap.read()
    if not ret: break

    # 1. Detect faces
    results = yolo_model(frame, verbose=False)
    
    # We only care if faces are found
    if len(results[0].boxes) > 0:
        
        # --- LOGIC TO FIND ONLY YOUR FACE (LARGEST FACE) ---
        # We calculate Area = Width * Height for all boxes
        # max() finds the box with the biggest area
        largest_box = max(results[0].boxes, key=lambda b: (b.xyxy[0][2] - b.xyxy[0][0]) * (b.xyxy[0][3] - b.xyxy[0][1]))
        
        # Get coordinates
        x1, y1, x2, y2 = largest_box.xyxy[0].cpu().numpy().astype(int)

        # --- ADD PADDING (Helps accuracy significantly) ---
        h, w, _ = frame.shape
        padding_x = int((x2 - x1) * 0.15) # 15% margin
        padding_y = int((y2 - y1) * 0.15)

        x1 = max(0, x1 - padding_x)
        y1 = max(0, y1 - padding_y)
        x2 = min(w, x2 + padding_x)
        y2 = min(h, y2 + padding_y)

        # Crop face
        face_img = frame[y1:y2, x1:x2]

        if face_img.size != 0:
            try:
                # Predict
                face_tensor = val_transform(face_img).unsqueeze(0).to(device)
                
                with torch.no_grad():
                    outputs = emotion_model(face_tensor)
                    probs = torch.softmax(outputs, dim=1)
                    conf, predicted = torch.max(probs, 1)
                    current_emotion = CLASS_NAMES[predicted.item()]
                
                # Add to buffer for smoothing
                emotion_buffer.append(current_emotion)
                
                # Get smoothed result
                final_emotion, stability = get_dominant_emotion(emotion_buffer)

                # Draw (Green box)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Text Background (Black) for readability
                label = f"{final_emotion}"
                (w_text, h_text), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
                cv2.rectangle(frame, (x1, y1 - 30), (x1 + w_text, y1), (0, 255, 0), -1)
                
                # Text
                cv2.putText(frame, label, (x1, y1 - 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

            except Exception as e:
                pass

    cv2.imshow('Optimized Emotion Detection', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()