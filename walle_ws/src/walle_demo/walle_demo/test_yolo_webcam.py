#!/usr/bin/env python3
"""Quick standalone test: run YOLOv8 on webcam or video file.

Usage:
    python3 test_yolo_webcam.py              # webcam (index 0)
    python3 test_yolo_webcam.py --source 1   # webcam index 1
    python3 test_yolo_webcam.py --source video.mp4
    python3 test_yolo_webcam.py --model yolov8s.pt --conf 0.4
"""

import argparse
import sys

import cv2
from ultralytics import YOLO


SAMPLE_IMAGES = [
    '/home/thailuu/.local/lib/python3.12/site-packages/ultralytics/assets/bus.jpg',
    '/home/thailuu/.local/lib/python3.12/site-packages/ultralytics/assets/zidane.jpg',
]


def run_image(path: str, model_name: str, conf: float) -> None:
    print(f'Loading {model_name} …')
    model = YOLO(model_name)

    frame = cv2.imread(path)
    if frame is None:
        print(f'ERROR: cannot read image "{path}"')
        sys.exit(1)

    print(f'Running inference on {path} …')
    results = model(frame, conf=conf, verbose=False)
    annotated = results[0].plot()

    detections = []
    for box in results[0].boxes:
        cls_id = int(box.cls[0])
        label  = results[0].names[cls_id]
        conf_  = float(box.conf[0])
        detections.append(f'{label} {conf_:.2f}')

    print(f'Detected {len(detections)} object(s): {", ".join(detections)}')

    out_path = path.replace('.jpg', '_detected.jpg')
    cv2.imwrite(out_path, annotated)
    print(f'Saved annotated image → {out_path}')

    cv2.imshow('YOLOv8 — WallE3 Test (any key to next, Q to quit)', annotated)
    return cv2.waitKey(0) & 0xFF


def run_camera(source, model_name: str, conf: float) -> None:
    print(f'Loading {model_name} …')
    model = YOLO(model_name)
    print('Model ready. Press Q to quit.')

    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        print(f'ERROR: cannot open source "{source}"')
        sys.exit(1)

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        results = model(frame, conf=conf, verbose=False)
        annotated = results[0].plot()
        n = len(results[0].boxes)
        cv2.putText(annotated, f'Objects: {n}', (8, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 200, 255), 2)
        cv2.imshow('YOLOv8 — WallE3 Test (Q to quit)', annotated)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--source', default=None,
                    help='Camera index, image path, or video path. '
                         'Omit to run on built-in sample images.')
    ap.add_argument('--model', default='yolov8n.pt')
    ap.add_argument('--conf', type=float, default=0.45)
    args = ap.parse_args()

    if args.source is None:
        # No source → cycle through built-in sample images
        for img_path in SAMPLE_IMAGES:
            key = run_image(img_path, args.model, args.conf)
            if key == ord('q'):
                break
        cv2.destroyAllWindows()
    else:
        source = args.source
        try:
            source = int(source)
        except (ValueError, TypeError):
            pass
        run_camera(source, args.model, args.conf)


if __name__ == '__main__':
    main()
