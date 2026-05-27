"""
routers/webcam.py
Blueprint xử lý webcam streaming + result polling.
"""

from flask import Blueprint, Response, jsonify
from detection.webcam import generate_frames, get_latest_result

webcam_bp = Blueprint('webcam', __name__)


@webcam_bp.route('/api/detect/webcam/stream')
def webcam_stream():
    """MJPEG streaming endpoint – frontend dùng <img src="/api/detect/webcam/stream">."""
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@webcam_bp.route('/api/detect/webcam/result')
def webcam_result():
    """
    Trả về kết quả nhận diện mới nhất dưới dạng JSON.
    Frontend polling endpoint này mỗi giây khi webcam đang bật.
    """
    result = get_latest_result()
    return jsonify({
        'success': True,
        'plates':    [{'text': p} for p in result['plates']],
        'timestamp': result['timestamp'],
    })
