import cv2
import torch
import torch.nn as nn
from torchvision import transforms, models
from ultralytics import YOLO
import numpy as np

# ==========================================
# 1. Runtime Configuration
# ==========================================
# Class labels (Must match the training order)
classes = ['angry', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']

# Use GPU if available
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"🚀 Running on: {device}")

# ==========================================
# 2. Load ResNet18 Emotion Model
# ==========================================
def load_emotion_model(model_path):
    print("⏳ Loading ResNet18 Emotion Model...")
    
    # Define model architecture (Same as training)
    # weights=None because we are loading our own trained weights
    model = models.resnet18(weights=None)
    
    # Modify the last layer to match 7 classes
    num_ftrs = model.fc.in_features
    model.fc = nn.Linear(num_ftrs, len(classes))
    
    # Load weights
    try:
        model.load_state_dict(torch.load(model_path, map_location=device))
        model.to(device)
        model.eval() # Set to evaluation mode (Critical for BatchNorm/Dropout)
        print("✅ Emotion Model Loaded Successfully!")
        return model
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        print("Make sure you downloaded 'resnet18_emotion.pt' from Colab to this folder.")
        exit()

# Model path (Use raw string r"" for Windows paths)
model_path = r"services/emotion-detection/Models/results/resnet18_Original.pt"
emotion_model = load_emotion_model(model_path)

# ==========================================
# 3. Load YOLO (Face Detection)
# ==========================================
print("⏳ Loading YOLO...")
try:
    # Try loading the specialized face detection model
    yolo_model = YOLO("yolov8n-face.pt")
    print("✅ Using YOLOv8-Face")
except:
    # Fallback to standard YOLO if face model is missing
    print("⚠️ yolov8n-face not found, using standard yolov8n")
    yolo_model = YOLO("yolov8n.pt")

# ==========================================
# 4. Image Preprocessing
# ==========================================
# Must match training transforms exactly (224x224, 3 Channels)
val_transform = transforms.Compose([
    transforms.ToPILImage(),
    # Convert to grayscale but repeat 3 times so ResNet accepts it (R=G=B)
    transforms.Grayscale(num_output_channels=3), 
    transforms.Resize((224, 224)), # Standard ResNet input size
    transforms.ToTensor(),
    # Same ImageNet normalization used during training
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

# ==========================================
# 5. Start Camera Stream
# ==========================================
cap = cv2.VideoCapture(0) # 0 for default camera

if not cap.isOpened():
    print("❌ Cannot open camera")
    exit()

print("\n🎥 Starting Video Stream... Press 'q' to exit.")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # 1. Detect faces using YOLO
    # conf=0.5 filters out low-confidence detections
    results = yolo_model(frame, verbose=False, conf=0.5) 
    
    for result in results:
        boxes = result.boxes
        for box in boxes:
            # Get face coordinates
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
            
            # Clip coordinates to ensure they are within frame boundaries
            h, w, _ = frame.shape
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            
            # Crop the face
            face_img = frame[y1:y2, x1:x2]
            
            # Skip very small faces to save processing time
            if face_img.size == 0 or face_img.shape[0] < 20 or face_img.shape[1] < 20:
                continue

            # 2. Predict Emotion
            try:
                # Prepare tensor
                face_tensor = val_transform(face_img).unsqueeze(0).to(device)
                
                with torch.no_grad():
                    outputs = emotion_model(face_tensor)
                    # Convert logits to probabilities
                    probs = torch.softmax(outputs, dim=1)
                    # Get highest probability
                    conf, predicted = torch.max(probs, 1)
                    
                    label = classes[predicted.item()]
                    confidence = conf.item()

                # 3. Draw on Frame
                color = (0, 255, 0) # Green
                
                # If confidence is low, change color to yellow
                if confidence < 0.5:
                    color = (0, 255, 255) # Yellow
                
                # Draw bounding box
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                
                # Draw label background and text
                text = f"{label} ({confidence*100:.1f}%)"
                (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                cv2.rectangle(frame, (x1, y1 - 25), (x1 + text_w, y1), color, -1)
                cv2.putText(frame, text, (x1, y1 - 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
                           
            except Exception as e:
                pass # Continue if a single face fails

    # Show video
    cv2.imshow('ResNet18 Emotion Detection', frame)

    # Exit on 'q' key
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()