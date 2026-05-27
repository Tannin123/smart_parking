import os

# ── Flask ───────────────────────────────────────────────────────────────
SECRET_KEY = 'smart_parking_secret_2024'
DEBUG      = True

# ── Upload / Output folders ─────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
RESULT_FOLDER = os.path.join(BASE_DIR, 'static', 'results')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

ALLOWED_IMAGE_EXT = {'jpg', 'jpeg', 'png', 'bmp', 'webp'}
ALLOWED_VIDEO_EXT = {'mp4', 'avi', 'mov', 'mkv'}

# ── YOLO model ──────────────────────────────────────────────────────────
MODEL_PATH = os.path.join(BASE_DIR, 'models', 'yolov8n.pt')

# ── MySQL ───────────────────────────────────────────────────────────────
DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASS = ''
DB_NAME = 'smart_parking'
