import cv2
from ultralytics import YOLO
from deepface import DeepFace

# -------- إعداد YOLO --------
# حط هنا وزن YOLO للكشف عن الوجه (face model)
YOLO_WEIGHTS = "services\emotion-detection\Models\yolov8n-face.pt"  # عدل للمسار الصحيح عندك

yolo_model = YOLO(YOLO_WEIGHTS)


def analyze_face_emotion(face_bgr):
    """
    face_bgr: crop من الفريم (BGR من OpenCV)
    """
    try:
        # DeepFace بيستقبل BGR عادي
        result = DeepFace.analyze(
            face_bgr,
            actions=["emotion"],
            enforce_detection=False,
        )
        # DeepFace.analyze بترجع list في الإصدارات الجديدة
        if isinstance(result, list):
            result = result[0]
        emotion = result.get("dominant_emotion", "unknown")
    except Exception as e:
        print("DeepFace error:", e)
        emotion = "unknown"

    return emotion


def main():
    cap = cv2.VideoCapture(0)  # الكاميرا الافتراضية

    if not cap.isOpened():
        print("Cannot open camera")
        return

    print("Press 'q' to quit")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # تشغيل YOLO على الفريم
        results = yolo_model(frame, stream=True, verbose=False)

        for r in results:
            if r.boxes is None:
                continue

            for box in r.boxes:
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)

                # تأكد إن البوكس جوه حدود الصورة
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

                emotion = analyze_face_emotion(face)

                # رسم البوكس والليبل
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(
                    frame,
                    emotion,
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 0),
                    2,
                    cv2.LINE_AA,
                )

        cv2.imshow("YOLO + DeepFace", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
