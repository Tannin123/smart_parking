"""
routers/vehicle.py
Blueprint xử lý nhận diện biển số từ ảnh và video.
"""

import os
import uuid
import base64
import logging
import datetime

import cv2
from flask import Blueprint, request, jsonify

import config
from detection.plate_detector import detect_license_plate
from detection.ocr import read_plate_text

detect_bp = Blueprint('vehicle', __name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _allowed_file(filename: str, allowed: set) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed


def _unique_filename(original: str) -> str:
    ext = original.rsplit('.', 1)[1].lower()
    return f"{uuid.uuid4().hex}.{ext}"


def _save_photo_base64(b64_str: str, prefix: str) -> str | None:
    """
    Nhận chuỗi base64 (đã bỏ header data:image/...;base64, hoặc chưa),
    giải mã và lưu thành file JPG trong PHOTO_FOLDER.
    Trả về đường dẫn tương đối static/photos/<filename> hoặc None nếu lỗi.
    """
    if not b64_str:
        return None
    try:
        # Bỏ header nếu có: "data:image/jpeg;base64,XXXXX"
        if ',' in b64_str:
            b64_str = b64_str.split(',', 1)[1]
        img_bytes = base64.b64decode(b64_str)
        ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{prefix}_{ts}_{uuid.uuid4().hex[:6]}.jpg"
        filepath = os.path.join(config.PHOTO_FOLDER, filename)
        with open(filepath, 'wb') as f:
            f.write(img_bytes)
        return f"static/photos/{filename}"
    except Exception as e:
        logging.error(f"[Vehicle] Lưu ảnh chụp xe thất bại: {e}")
        return None


# ── POST /api/detect/image ────────────────────────────────────────────────────

@detect_bp.route('/api/detect/image', methods=['POST'])
def detect_image():
    """Nhận file ảnh, trả về JSON chứa danh sách biển số và ảnh annotated."""
    file = request.files.get('image')
    if not file or not _allowed_file(file.filename, config.ALLOWED_IMAGE_EXT):
        return jsonify({'success': False, 'error': 'File ảnh không hợp lệ.'}), 400

    filename = _unique_filename(file.filename)
    save_path = os.path.join(config.UPLOAD_FOLDER, filename)
    file.save(save_path)

    image = cv2.imread(save_path)
    if image is None:
        return jsonify({'success': False, 'error': 'Không đọc được file ảnh.'}), 400

    # Phóng to ảnh nhỏ để YOLO detect chính xác hơn (tối thiểu 640px)
    h, w = image.shape[:2]
    if w < 640:
        scale = 640 / w
        image = cv2.resize(image, (640, int(h * scale)), interpolation=cv2.INTER_CUBIC)

    try:
        plate_crops, annotated, boxes_list = detect_license_plate(image)

        plates = []
        for crop in plate_crops:
            text = read_plate_text(crop)
            plates.append({'text': text})

        # Encode annotated image sang base64 để trả về frontend
        ok, buf = cv2.imencode('.jpg', annotated)
        annotated_b64 = base64.b64encode(buf.tobytes()).decode() if ok else ''

        return jsonify({
            'success': True,
            'plates': plates,
            'annotated_b64': annotated_b64,
        })

    except Exception as e:
        logging.error(f"[Vehicle] Lỗi detect image: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ── POST /api/detect/video ────────────────────────────────────────────────────

@detect_bp.route('/api/detect/video', methods=['POST'])
def detect_video():
    """Nhận file video, xử lý từng frame, trả về JSON biển số và path video output."""
    file = request.files.get('video')
    if not file or not _allowed_file(file.filename, config.ALLOWED_VIDEO_EXT):
        return jsonify({'success': False, 'error': 'File video không hợp lệ.'}), 400

    filename    = _unique_filename(file.filename)
    save_path   = os.path.join(config.UPLOAD_FOLDER, filename)
    output_name = f"out_{filename.rsplit('.', 1)[0]}.mp4"
    output_path = os.path.join(config.RESULT_FOLDER, output_name)
    file.save(save_path)

    cap = cv2.VideoCapture(save_path)
    if not cap.isOpened():
        return jsonify({'success': False, 'error': 'Không mở được file video.'}), 400

    fps    = cap.get(cv2.CAP_PROP_FPS) or 25
    width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    all_plates   = set()
    total_frames = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            total_frames += 1

            # Chỉ chạy detect mỗi 10 frame để tiết kiệm thời gian
            if total_frames % 10 == 0:
                plate_crops, annotated, _ = detect_license_plate(frame)
                for crop in plate_crops:
                    text = read_plate_text(crop)
                    if text and text != 'UNKNOWN':
                        all_plates.add(text)
                writer.write(annotated)
            else:
                writer.write(frame)

    except Exception as e:
        logging.error(f"[Vehicle] Lỗi detect video: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        cap.release()
        writer.release()

    return jsonify({
        'success':      True,
        'plates':       list(all_plates),
        'total_frames': total_frames,
        'output_path':  f"static/results/{output_name}",
    })


# ── POST /api/parking/in ──────────────────────────────────────────────────────

import db

@detect_bp.route('/api/parking/in', methods=['POST'])
def parking_in():
    data = request.json
    plate = data.get('plate')
    vehicle_type = data.get('vehicle_type', 'xe_may')
    if not plate:
        return jsonify({'success': False, 'error': 'Thiếu biển số.'}), 400

    if plate.strip().upper() == 'UNKNOWN':
        return jsonify({
            'success': False,
            'error': 'Không thể đọc biển số xe. Vui lòng chụp lại hoặc nhập thủ công.'
        }), 400

    # Lưu ảnh chụp xe vào (nếu có)
    photo_path = _save_photo_base64(data.get('photo'), prefix='in')

    success, msg = db.check_in(plate, vehicle_type, photo_path)
    return jsonify({'success': success, 'message': msg})

# ── POST /api/parking/out ─────────────────────────────────────────────────────

@detect_bp.route('/api/parking/out', methods=['POST'])
def parking_out():
    data = request.json
    plate = data.get('plate')
    if not plate:
        return jsonify({'success': False, 'error': 'Thiếu biển số.'}), 400

    # Lưu ảnh chụp xe ra (nếu có)
    photo_path = _save_photo_base64(data.get('photo'), prefix='out')

    success, msg, fee = db.check_out(plate, photo_path)
    return jsonify({'success': success, 'message': msg, 'fee': fee})

# ── GET /api/parking/history ──────────────────────────────────────────────────

@detect_bp.route('/api/parking/history', methods=['GET'])
def parking_history():
    logs = db.get_recent_logs(limit=20)
    return jsonify({'success': True, 'logs': logs})


# ── POST /api/parking/in-obscured ────────────────────────────────────────────
# Dùng khi YOLO phát hiện xe nhưng OCR không đọc được biển số

@detect_bp.route('/api/parking/in-obscured', methods=['POST'])
def parking_in_obscured():
    """
    Ghi nhận xe vào bãi khi biển số bị che khuất.
    Body JSON (tùy chọn):
      vehicle_type : str  – loại xe (mặc định 'xe_may')
    Trả về ID tạm để nhân viên dùng cho xe ra.
    """
    data         = request.json or {}
    vehicle_type = data.get('vehicle_type', 'xe_may')

    success, msg, temp_id = db.check_in_obscured(vehicle_type=vehicle_type)
    if success:
        logging.warning(f"[Vehicle] Xe vào với biển bị che — ID tạm: {temp_id}")
        return jsonify({'success': True, 'message': msg, 'temp_id': temp_id}), 201
    return jsonify({'success': False, 'error': msg}), 500


# ── POST /api/parking/out-obscured ───────────────────────────────────────────

@detect_bp.route('/api/parking/out-obscured', methods=['POST'])
def parking_out_obscured():
    """
    Cho xe có biển bị che ra khỏi bãi, tính phí theo giờ.
    Body JSON:
      temp_id : str  – ID tạm nhận được lúc vào (dạng OBSCURED_XXXXXXXX)
    """
    data    = request.json or {}
    temp_id = (data.get('temp_id') or '').strip()

    if not temp_id:
        return jsonify({'success': False, 'error': 'Thiếu temp_id.'}), 400
    if not temp_id.startswith('OBSCURED_'):
        return jsonify({'success': False, 'error': 'temp_id không hợp lệ.'}), 400

    success, msg, fee = db.check_out_obscured(temp_id)
    if success:
        return jsonify({'success': True, 'message': msg, 'fee': fee})
    return jsonify({'success': False, 'error': msg}), 404


# ── GET /api/parking/obscured ─────────────────────────────────────────────────

@detect_bp.route('/api/parking/obscured', methods=['GET'])
def parking_obscured_list():
    """
    Trả về danh sách các xe vào bãi có biển số bị che khuất.
    Dùng để nhân viên theo dõi và xử lý thủ công.
    """
    logs = db.get_obscured_logs(limit=50)
    return jsonify({'success': True, 'logs': logs})
