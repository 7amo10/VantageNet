# import cv2
# import torch
# import torch.nn as nn
# from torchvision import transforms, models
# from ultralytics import YOLO
# import numpy as np

# # ==========================================
# # 1. Runtime Configuration
# # ==========================================
# # Class labels (Must match the training order)
# classes = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']

# # Use GPU if available
# device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
# print(f"🚀 Running on: {device}")

# # ==========================================
# # 2. Load ResNet18 Emotion Model
# # ==========================================
# def load_emotion_model(model_path):
#     print("⏳ Loading ResNet18 Emotion Model...")
    
#     # Define model architecture (Same as training)
#     # weights=None because we are loading our own trained weights
#     model = models.resnet18(weights=None)
    
#     # Modify the last layer to match 7 classes
#     num_ftrs = model.fc.in_features
#     model.fc = nn.Linear(num_ftrs, len(classes))
    
#     # Load weights
#     try:
#         model.load_state_dict(torch.load(model_path, map_location=device))
#         model.to(device)
#         model.eval() # Set to evaluation mode (Critical for BatchNorm/Dropout)
#         print("✅ Emotion Model Loaded Successfully!")
#         return model
#     except Exception as e:
#         print(f"❌ Error loading model: {e}")
#         print("Make sure you downloaded 'resnet18_emotion.pt' from Colab to this folder.")
#         exit()

# # Model path (Use raw string r"" for Windows paths)
# model_path = r"services/emotion-detection/Models/results/resnet18_Original.pt"
# emotion_model = load_emotion_model(model_path)

# # ==========================================
# # 3. Load YOLO (Face Detection)
# # ==========================================
# print("⏳ Loading YOLO...")
# try:
#     # Try loading the specialized face detection model
#     yolo_model = YOLO("yolov8n-face.pt")
#     print("✅ Using YOLOv8-Face")
# except:
#     # Fallback to standard YOLO if face model is missing
#     print("⚠️ yolov8n-face not found, using standard yolov8n")
#     yolo_model = YOLO("yolov8n.pt")

# # ==========================================
# # 4. Image Preprocessing
# # ==========================================
# # Must match training transforms exactly (224x224, 3 Channels)
# val_transform = transforms.Compose([
#     transforms.ToPILImage(),
#     # Convert to grayscale but repeat 3 times so ResNet accepts it (R=G=B)
#     transforms.Grayscale(num_output_channels=3), 
#     transforms.Resize((224, 224)), # Standard ResNet input size
#     transforms.ToTensor(),
#     # Same ImageNet normalization used during training
#     transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
# ])

# # ==========================================
# # 5. Start Camera Stream
# # ==========================================
# cap = cv2.VideoCapture(0) # 0 for default camera

# if not cap.isOpened():
#     print("❌ Cannot open camera")
#     exit()

# print("\n🎥 Starting Video Stream... Press 'q' to exit.")

# while True:
#     ret, frame = cap.read()
#     if not ret:
#         break

#     # 1. Detect faces using YOLO
#     # conf=0.5 filters out low-confidence detections
#     results = yolo_model(frame, verbose=False, conf=0.5) 
    
#     for result in results:
#         boxes = result.boxes
#         for box in boxes:
#             # Get face coordinates
#             x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
            
#             # Clip coordinates to ensure they are within frame boundaries
#             h, w, _ = frame.shape
#             x1, y1 = max(0, x1), max(0, y1)
#             x2, y2 = min(w, x2), min(h, y2)
            
#             # Crop the face
#             face_img = frame[y1:y2, x1:x2]
            
#             # Skip very small faces to save processing time
#             if face_img.size == 0 or face_img.shape[0] < 20 or face_img.shape[1] < 20:
#                 continue

#             # 2. Predict Emotion
#             try:
#                 # Prepare tensor
#                 face_tensor = val_transform(face_img).unsqueeze(0).to(device)
                
#                 with torch.no_grad():
#                     outputs = emotion_model(face_tensor)
#                     # Convert logits to probabilities
#                     probs = torch.softmax(outputs, dim=1)
#                     # Get highest probability
#                     conf, predicted = torch.max(probs, 1)
                    
#                     label = classes[predicted.item()]
#                     confidence = conf.item()

#                 # 3. Draw on Frame
#                 color = (0, 255, 0) # Green
                
#                 # If confidence is low, change color to yellow
#                 if confidence < 0.5:
#                     color = (0, 255, 255) # Yellow
                
#                 # Draw bounding box
#                 cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                
#                 # Draw label background and text
#                 text = f"{label} ({confidence*100:.1f}%)"
#                 (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
#                 cv2.rectangle(frame, (x1, y1 - 25), (x1 + text_w, y1), color, -1)
#                 cv2.putText(frame, text, (x1, y1 - 5), 
#                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
                           
#             except Exception as e:
#                 pass # Continue if a single face fails

#     # Show video
#     cv2.imshow('ResNet18 Emotion Detection', frame)

#     # Exit on 'q' key
#     if cv2.waitKey(1) & 0xFF == ord('q'):
#         break

# cap.release()
# cv2.destroyAllWindows()

import cv2
import torch
import torch.nn as nn
import numpy as np
from torchvision import transforms
from collections import deque, Counter

# ==========================================
# 1. تعريف الموديل (زي ما هو)
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
# 2. الإعدادات
# ==========================================
CLASS_NAMES = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Running on: {device}")

# تحميل موديل المشاعر
# تأكد إن المسار صح لملف الموديل بتاعك
model_path = "services/emotion-detection/Models/results/emotion_model_best (1).pt"
emotion_model = EmotionCNN(num_classes=7).to(device)

try:
    emotion_model.load_state_dict(torch.load(model_path, map_location=device))
    emotion_model.eval()
    print("✅ Emotion model loaded.")
except FileNotFoundError:
    print(f"❌ Error: '{model_path}' not found.")
    exit()

# ==========================================
# 3. إعداد كاشف الوشوش (Haar Cascade)
# ==========================================
# ده موجود جوه OpenCV مش محتاج تحميل حاجة خارجية
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# التجهيز (Preprocessing)
val_transform = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Grayscale(num_output_channels=1),
    transforms.Resize((48, 48)),
    transforms.ToTensor(),
    transforms.Normalize((0.5,), (0.5,)),
])

# مخزن لتثبيت النتيجة (Smoothing)
emotion_buffer = deque(maxlen=10)

def get_dominant_emotion(buffer):
    if not buffer: return "Computing..."
    counts = Counter(buffer)
    most_common, _ = counts.most_common(1)[0]
    return most_common

# ==========================================
# 4. تشغيل الكاميرا
# ==========================================
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Cannot open camera.")
    exit()

print("\n🎥 Starting stream (Face Only)... Press 'q' to exit.")

while True:
    ret, frame = cap.read()
    if not ret: break

    # تحويل لرمادي عشان Haar Cascade يشتغل
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # كشف الوشوش
    # scaleFactor=1.1, minNeighbors=5 (بيقلل الغلطات)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    
    # لو لقينا وشوش، نختار أكبر واحد بس (عشان نركز عليك أنت)
    if len(faces) > 0:
        # بنختار الوش اللي مساحته (w * h) أكبر حاجة
        largest_face = max(faces, key=lambda rect: rect[2] * rect[3])
        x, y, w, h = largest_face

        # --- قص الوش ---
        # ممكن نزود هوامش بسيطة لو الوش مقصوص أوي
        margin_x = int(w * 0.1)
        margin_y = int(h * 0.1)
        
        x1 = max(0, x - margin_x)
        y1 = max(0, y - margin_y)
        x2 = min(frame.shape[1], x + w + margin_x)
        y2 = min(frame.shape[0], y + h + margin_y)

        face_img = frame[y1:y2, x1:x2]

        if face_img.size != 0:
            try:
                # توقع الإيموشن
                face_tensor = val_transform(face_img).unsqueeze(0).to(device)
                
                with torch.no_grad():
                    outputs = emotion_model(face_tensor)
                    probs = torch.softmax(outputs, dim=1)
                    _, predicted = torch.max(probs, 1)
                    current_emotion = CLASS_NAMES[predicted.item()]
                
                # تثبيت النتيجة
                emotion_buffer.append(current_emotion)
                final_emotion = get_dominant_emotion(emotion_buffer)

                # الرسم (مربع أخضر على الوش بس)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # كتابة النتيجة
                cv2.rectangle(frame, (x1, y1 - 30), (x1 + 150, y1), (0, 255, 0), -1)
                cv2.putText(frame, final_emotion, (x1 + 5, y1 - 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

            except Exception as e:
                pass

    cv2.imshow('Face Only Emotion Detection', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()