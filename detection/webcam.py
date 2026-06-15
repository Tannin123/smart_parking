import cv2
import numpy as np
import re
import time
import logging

from detection.plate_detector import detect_license_plate
from detection.ocr import read_plate_text

# ── Cấu hình ──────────────────────────────────────────────────────────────────
CAMERA_INDEX    = 0    # 0 = webcam mặc định
DETECT_INTERVAL = 0.5  # giây giữa các lần chạy YOLO

# Regex match biển số VN: 99-E1 222.68 / 51A-12345 / 30H1-123.45
PLATE_PATTERN = re.compile(
    r'\d{2}[-\s]?[A-Z]{1,2}\d?[-\s]?\d{3,5}[.\-]?\d{0,3}',
    re.IGNORECASE
)

# ── Cấu hình phát hiện biển số bị che ────────────────────────────────────────
# Số lần OCR thất bại liên tiếp trên vùng detect để coi là bị che
OBSCURED_THRESHOLD = 5

# ── Kết quả detect mới nhất (dùng cho endpoint /webcam/result) ────────────────
_latest_result = {
    'plates':    [],        # list[str] biển số đọc được
    'timestamp': 0.0,       # epoch khi phát hiện lần cuối
    'obscured':  False,     # True nếu phát hiện xe nhưng biển bị che
}

# Đếm số lần liên tiếp phát hiện vùng biển nhưng OCR thất bại
_obscure_counter = 0


def get_latest_result() -> dict:
    """Trả về kết quả detect mới nhất cho frontend polling."""
    return dict(_latest_result)


def _update_result(plates: list, obscured: bool = False):
    """Cập nhật kết quả shared."""
    _latest_result['plates']    = plates
    _latest_result['timestamp'] = time.time()
    _latest_result['obscured']  = obscured


def generate_frames():
    """
    Generator trả về MJPEG frames.
    Dùng trong routers/webcam.py:
        return Response(generate_frames(),
                        mimetype='multipart/x-mixed-replace; boundary=frame')
    """
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        logging.error(f"[Webcam] Không mở được camera (index={CAMERA_INDEX})")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    last_detect_time = 0.0
    shared_data = {'boxes': [], 'texts': [], 'detecting': False}

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                logging.warning("[Webcam] Mất kết nối camera.")
                break

            display = frame.copy()
            now     = time.time()

            # ── Chạy YOLO + OCR theo chu kỳ trong Thread ngầm để chống lag ────────────────────────────────
            if now - last_detect_time >= DETECT_INTERVAL and not shared_data['detecting']:
                last_detect_time = now
                shared_data['detecting'] = True
                
                def bg_detect(detect_frame):
                    global _obscure_counter
                    try:
                        plate_crops, _, boxes_list = detect_license_plate(detect_frame)
                        new_texts   = []
                        valid_plates = []

                        for crop in plate_crops:
                            text = read_plate_text(crop)
                            new_texts.append(text)
                            if text and text != 'UNKNOWN':
                                valid_plates.append(text)
                                logging.info(f"[Webcam] Biển số: {text}")

                        # ── Logic phát hiện biển số bị che ──────────────────
                        if boxes_list and not valid_plates:
                            # Detect được vùng biển nhưng không đọc được chữ
                            _obscure_counter += 1
                            logging.warning(
                                f"[Webcam] Không đọc được biển ({_obscure_counter}/{OBSCURED_THRESHOLD})"
                            )
                        else:
                            # Đọc được hoặc không có xe → reset bộ đếm
                            _obscure_counter = 0

                        is_obscured = _obscure_counter >= OBSCURED_THRESHOLD
                        if is_obscured:
                            logging.warning("[Webcam] CẢNH BÁO: Biển số có thể bị che khuất!")

                        # Cập nhật kết quả
                        shared_data['boxes']    = boxes_list
                        shared_data['texts']    = new_texts
                        shared_data['obscured'] = is_obscured
                        _update_result(valid_plates, obscured=is_obscured)
                    except Exception as e:
                        logging.error(f"[Webcam] Lỗi detect: {e}")
                    finally:
                        shared_data['detecting'] = False

                import threading
                threading.Thread(target=bg_detect, args=(frame.copy(),), daemon=True).start()

            # ── Vẽ kết quả cached lên frame ─────────────────────────────────
            is_obscured = shared_data.get('obscured', False)
            for i, box in enumerate(shared_data['boxes']):
                x1, y1, x2, y2 = box[:4]
                text     = shared_data['texts'][i] if i < len(shared_data['texts']) else ''
                is_valid = text and text != 'UNKNOWN'

                # Màu: xanh lá = OK, đỏ = bị che, xanh dương = đang đọc
                if is_valid:
                    color = (0, 220, 0)
                elif is_obscured:
                    color = (0, 0, 220)   # đỏ BGR
                else:
                    color = (59, 130, 246)

                cv2.rectangle(display, (x1, y1), (x2, y2), color, 2)

                if is_valid:
                    label = text
                elif is_obscured:
                    label = '!! BIEN SO BI CHE !!'
                else:
                    label = 'Bien so...'

                font, fs, th2 = cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2
                (tw, th), _ = cv2.getTextSize(label, font, fs, th2)
                bg_y1 = max(0, y1 - th - 10)
                cv2.rectangle(display, (x1, bg_y1), (x1 + tw + 8, y1), color, -1)
                cv2.putText(display, label, (x1 + 4, y1 - 5),
                            font, fs, (255, 255, 255), th2, cv2.LINE_AA)

            # ── Hiển thị cảnh báo toàn màn hình khi phát hiện che biển ────────
            if is_obscured:
                warn = '!! CANH BAO: BIEN SO BI CHE KHUAT !!'
                font_w = cv2.FONT_HERSHEY_SIMPLEX
                (ww, wh), _ = cv2.getTextSize(warn, font_w, 0.7, 2)
                wx = max(0, (display.shape[1] - ww) // 2)
                # Nền đỏ mờ phía trên
                overlay = display.copy()
                cv2.rectangle(overlay, (0, 0), (display.shape[1], wh + 20), (0, 0, 180), -1)
                cv2.addWeighted(overlay, 0.55, display, 0.45, 0, display)
                cv2.putText(display, warn, (wx, wh + 8),
                            font_w, 0.7, (255, 255, 255), 2, cv2.LINE_AA)

            # ── HUD ─────────────────────────────────────────────────────────
            cv2.putText(display, "Nhan dien bien so xe",
                        (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

            # ── Encode → MJPEG ───────────────────────────────────────────────
            ok, buf = cv2.imencode('.jpg', display, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ok:
                continue
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n'
                   + buf.tobytes()
                   + b'\r\n')

    finally:
        _update_result([], obscured=False)   # xoá kết quả khi tắt camera
        cap.release()
        logging.info("[Webcam] Camera đã giải phóng.")
