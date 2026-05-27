import cv2
import numpy as np
import logging
import os

CONFIDENCE_THRESHOLD = 0.3

_PLATE_MODEL_PATH = 'models/plate_detector.pt'
_COCO_MODEL_PATH  = 'models/yolov8n.pt'

_IS_PLATE_MODEL = False

model = None

try:
    from ultralytics import YOLO

    if os.path.exists(_PLATE_MODEL_PATH):
        model = YOLO(_PLATE_MODEL_PATH)
        _IS_PLATE_MODEL = True
        logging.info(f"[Plate Detector] Da load model bien so: {_PLATE_MODEL_PATH}")
    elif os.path.exists(_COCO_MODEL_PATH):
        model = YOLO(_COCO_MODEL_PATH)
        _IS_PLATE_MODEL = False
        logging.warning(
            f"[Plate Detector] Khong tim thay {_PLATE_MODEL_PATH}. "
            f"Dung tam model COCO ({_COCO_MODEL_PATH}). "
            "Model nay KHONG nhan dien bien so — chi dung de test."
        )
    else:
        logging.error("[Plate Detector] Khong tim thay file model nao trong models/")

except ImportError:
    logging.warning("[Plate Detector] Chua cai ultralytics: pip install ultralytics")
except Exception as e:
    logging.error(f"[Plate Detector] Loi khi load model: {e}")


def detect_license_plate(image):
    if image is None or not isinstance(image, np.ndarray) or image.size == 0:
        logging.error("[Plate Detector] Anh dau vao khong hop le.")
        return [], image, []

    if model is None:
        logging.error("[Plate Detector] Model chua load duoc.")
        return [], image, []

    try:
        img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    except cv2.error as e:
        logging.error(f"[Plate Detector] Loi chuyen mau: {e}")
        return [], image, []

    plate_crops = []
    boxes_list  = []

    try:
        results = model(img_rgb, verbose=False)

        annotated_rgb   = results[0].plot()
        annotated_image = cv2.cvtColor(annotated_rgb, cv2.COLOR_RGB2BGR)

        h, w = image.shape[:2]

        for result in results:
            for box in result.boxes:
                confidence = float(box.conf[0])
                class_id   = int(box.cls[0])

                if confidence < CONFIDENCE_THRESHOLD:
                    continue

                if not _IS_PLATE_MODEL and class_id != 2:
                    continue

                x1, y1, x2, y2 = map(int, box.xyxy[0])
                
                # Expand box slightly to avoid cutting off edge characters
                padding = 10
                px1 = max(0, x1 - padding)
                py1 = max(0, y1 - padding)
                px2 = min(w, x2 + padding)
                py2 = min(h, y2 + padding)

                plate_crop = image[py1:py2, px1:px2]
                if plate_crop.size == 0:
                    continue

                plate_crops.append(plate_crop)
                boxes_list.append((x1, y1, x2, y2, round(confidence, 3)))
                logging.info(
                    f"[Plate Detector] Phat hien tai [{x1},{y1},{x2},{y2}] conf={confidence:.2f}"
                )

        logging.info(f"[Plate Detector] Tim thay {len(plate_crops)} vung.")
        return plate_crops, annotated_image, boxes_list

    except Exception as e:
        logging.error(f"[Plate Detector] Loi detect: {e}")
        return [], image, []


def draw_plate_annotations(image: np.ndarray,
                            boxes_list: list,
                            plate_texts: list) -> np.ndarray:
    if not boxes_list:
        return image.copy()

    output = image.copy()

    for box, text in zip(boxes_list, plate_texts):
        x1, y1, x2, y2 = box[:4]

        color = (34, 197, 94) if text else (59, 130, 246)
        label = text if text else "Bien so"

        cv2.rectangle(output, (x1, y1), (x2, y2), color, 2)

        font       = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.65
        thickness  = 2
        (tw, th), baseline = cv2.getTextSize(label, font, font_scale, thickness)

        bg_y1 = max(0, y1 - th - 10)
        bg_y2 = y1
        bg_x2 = x1 + tw + 8
        cv2.rectangle(output, (x1, bg_y1), (bg_x2, bg_y2), color, -1)

        cv2.putText(
            output, label,
            (x1 + 4, y1 - 5),
            font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA
        )

    return output
