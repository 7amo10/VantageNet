import cv2
import torch
import torch.nn as nn
from torchvision import models, transforms
from ultralytics import YOLO
import numpy as np

# ==========================================
# 1. إعدادات عامة
# ==========================================
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# نفس عدد الكلاسات اللي دربت بيه EfficientNet
NUM_CLASSES = 7

# تأكد إن ترتيب الليبلات هو نفس ترتيب الفولدرات في ImageFolder (أبجديًا غالبًا):
# angry, disgust, fear, happy, neutral, sad, surprise
EMOTION_LABELS = ["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"]

# Paths
EFFICIENTNET_WEIGHTS = "services/emotion-detection/Models/results/efficientnet_emotion (1).pt"   # عدّل لو حاطه في مكان تاني
YOLO_WEIGHTS         = "services/emotion-detection/Models/yolov8n-face.pt"           # أو "yolov8n-face.pt" لو في نفس الفولدر


# ==========================================
# 2. موديل EfficientNet-B0 (نفس اللي دربناه)
# ==========================================
class EmotionEfficientNet(nn.Module):
    def __init__(self, num_classes=7, pretrained=False):
        super(EmotionEfficientNet, self).__init__()

        if pretrained:
            weights = models.EfficientNet_B0_Weights.DEFAULT
        else:
            weights = None

        self.base_model = models.efficientnet_b0(weights=weights)

        in_features = self.base_model.classifier[1].in_features
        self.base_model.classifier[1] = nn.Sequential(
            nn.Dropout(p=0.3),
            nn.Linear(in_features, num_classes)
        )

    def forward(self, x):
        return self.base_model(x)


def load_emotion_model(weights_path: str):
    model = EmotionEfficientNet(num_classes=NUM_CLASSES, pretrained=False)
    state = torch.load(weights_path, map_location=DEVICE)
    model.load_state_dict(state)
    model.to(DEVICE)
    model.eval()
    return model


# ==========================================
# 3. YOLO model + Transform للصورة
# ==========================================
print("🔄 Loading YOLO face model...")
yolo_model = YOLO(YOLO_WEIGHTS)

print("🔄 Loading EfficientNet emotion model...")
emotion_model = load_emotion_model(EFFICIENTNET_WEIGHTS)

# Transform للوجه قبل دخوله EfficientNet
face_transform = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Grayscale(num_output_channels=3),
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],   # نفس اللي استخدمته في التدريب
        std=[0.229, 0.224, 0.225],
    ),
])


def predict_emotion(face_bgr: np.ndarray) -> str:
    """
    face_bgr: صورة الوجه (crop) من OpenCV (BGR)
    """
    if face_bgr is None or face_bgr.size == 0:
        return "unknown"

    # BGR -> RGB
    face_rgb = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2RGB)

    # إلى Tensor
    img = face_transform(face_rgb).unsqueeze(0).to(DEVICE)

    with torch.no_grad():
        outputs = emotion_model(img)
        _, pred = torch.max(outputs, 1)
        idx = pred.item()

    # حماية لو حصل أي غلطة في الـ index
    if idx < 0 or idx >= len(EMOTION_LABELS):
        return "unknown"

    return EMOTION_LABELS[idx]


# ==========================================
# 4. حلقة الـ Real-Time
# ==========================================
def main():
    # لو شغال على جهازك المحلي:
    cap = cv2.VideoCapture(0)

    # لو في كولاب ومش عندك كاميرا تبقى تشغّل على فيديو:
    # cap = cv2.VideoCapture("/content/your_video.mp4")

    if not cap.isOpened():
        print("❌ Cannot open camera / video.")
        return

    print("✅ Running... Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # تشغيل YOLO على الفريم (stream=True عشان نلف على النتائج)
        results = yolo_model(frame, stream=True, verbose=False)

        for r in results:
            if r.boxes is None:
                continue

            for box in r.boxes:
                xyxy = box.xyxy[0].cpu().numpy()
                x1, y1, x2, y2 = map(int, xyxy)

                h, w, _ = frame.shape
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

                # رسم البوكس والليبل
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
