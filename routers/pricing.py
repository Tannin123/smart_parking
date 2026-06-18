import datetime
import logging
import math
import re
from functools import wraps
from flask import Blueprint, request, jsonify, session
import mysql.connector
from mysql.connector import Error as MySQLError
from config import DB_HOST, DB_USER, DB_PASS, DB_NAME


DB_CONFIG = {
    'host':     DB_HOST,
    'user':     DB_USER,
    'password': DB_PASS,
    'database': DB_NAME,
    'charset':  'utf8mb4',
}

logger = logging.getLogger(__name__)


ROLE_ADMIN = 'admin'

VEHICLE_TYPE_LABELS = {
    'xe_may':       'Xe May',
    'xe_tay_ga':    'Xe Tay Ga',
    'o_to':         'O To',
    'xe_dap_dien':  'Xe Dap Dien',
    'xe_tai':       'Xe Tai',
}

CALC_MODE_TURN   = 'turn'
CALC_MODE_HOURLY = 'hourly'
VALID_MODES      = {CALC_MODE_TURN, CALC_MODE_HOURLY}

TIME_RE = re.compile(r'^\d{2}:\d{2}$')

DT_FORMATS = [
    '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S',
    '%Y-%m-%d %H:%M',    '%Y-%m-%dT%H:%M',
]

pricing_bp = Blueprint('pricing_bp', __name__)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_conn():
    """Trả về kết nối MySQL với autocommit=False."""
    conn = mysql.connector.connect(**DB_CONFIG, autocommit=False)
    return conn


def _rollback(conn):
    try:
        conn.rollback()
    except Exception:
        pass


def init_pricing_tables():
    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS pricing (
                id             INT AUTO_INCREMENT PRIMARY KEY,
                vehicle_type   VARCHAR(50)  NOT NULL DEFAULT '',
                label          VARCHAR(100) NOT NULL DEFAULT '',
                price_per_turn INT          NOT NULL DEFAULT 0,
                price_per_hour INT          NOT NULL DEFAULT 0,
                time_open      VARCHAR(5)   NOT NULL DEFAULT '06:00',
                time_close     VARCHAR(5)   NOT NULL DEFAULT '22:00',
                note           TEXT         NULL,
                created_at     DATETIME     NULL,
                updated_at     DATETIME     NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')

        # ── Migration: bổ sung cột còn thiếu vào bảng cũ ──────────────────
        # Đọc danh sách cột hiện tại của bảng
        cur.execute("SHOW COLUMNS FROM pricing")
        existing_cols = {row[0] for row in cur.fetchall()}

        col_migrations = {
            'vehicle_type':   "ALTER TABLE pricing ADD COLUMN vehicle_type   VARCHAR(50)  NOT NULL DEFAULT ''      AFTER id",
            'label':          "ALTER TABLE pricing ADD COLUMN label          VARCHAR(100) NOT NULL DEFAULT ''      AFTER vehicle_type",
            'price_per_turn': "ALTER TABLE pricing ADD COLUMN price_per_turn INT          NOT NULL DEFAULT 0       AFTER label",
            'price_per_hour': "ALTER TABLE pricing ADD COLUMN price_per_hour INT          NOT NULL DEFAULT 0       AFTER price_per_turn",
            'time_open':      "ALTER TABLE pricing ADD COLUMN time_open      VARCHAR(5)   NOT NULL DEFAULT '06:00' AFTER price_per_hour",
            'time_close':     "ALTER TABLE pricing ADD COLUMN time_close     VARCHAR(5)   NOT NULL DEFAULT '22:00' AFTER time_open",
            'note':           "ALTER TABLE pricing ADD COLUMN note           TEXT         NULL                     AFTER time_close",
            'created_at':     "ALTER TABLE pricing ADD COLUMN created_at     DATETIME     NULL                     AFTER note",
            'updated_at':     "ALTER TABLE pricing ADD COLUMN updated_at     DATETIME     NULL                     AFTER created_at",
        }
        for col, sql in col_migrations.items():
            if col not in existing_cols:
                cur.execute(sql)
                logger.info("Migration: added column '%s' to pricing table", col)

        # Thêm UNIQUE index nếu chưa có (chạy an toàn nhiều lần)
        try:
            cur.execute(
                "ALTER TABLE pricing ADD UNIQUE KEY uq_vehicle_type (vehicle_type)"
            )
        except Exception:
            pass   # index đã tồn tại → bỏ qua

        # Seed 3 loại xe mặc định — INSERT IGNORE giữ nguyên nếu đã có
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        defaults = [
            ('xe_may', 'Xe Máy',  5000, '06:00', '22:00', 'Xe máy thường ngày'),
            ('o_to',   'Ô Tô',   20000, '06:00', '22:00', 'Ô tô thường ngày'),
            ('xe_dap', 'Xe Đạp',  2000, '06:00', '22:00', 'Xe đạp thường ngày'),
        ]
        cur.executemany(
            "INSERT IGNORE INTO pricing "
            "(vehicle_type, label, price_per_turn, price_per_hour, "
            " time_open, time_close, note, created_at, updated_at) "
            "VALUES (%s, %s, 0, %s, %s, %s, %s, %s, %s)",
            [(vt, lb, pph, to_, tc, note, now, now)
             for vt, lb, pph, to_, tc, note in defaults]
        )

        conn.commit()
    except Exception:
        _rollback(conn)
        raise
    finally:
        conn.close()


# ─── Validation ───────────────────────────────────────────────────────────────

def _validate_time(t):
    if not t or not TIME_RE.match(t):
        return False
    try:
        datetime.datetime.strptime(t, '%H:%M')
        return True
    except ValueError:
        return False


def _validate_pricing_input(data):
    """Return error string or None if valid."""
    vehicle_type   = (data.get('vehicle_type') or '').strip()
    label          = (data.get('label') or '').strip()
    price_per_turn = data.get('price_per_turn')
    price_per_hour = data.get('price_per_hour')
    time_open      = data.get('time_open', '00:00')
    time_close     = data.get('time_close', '23:59')

    if not vehicle_type:
        return 'Vui long nhap loai xe.'
    if not label:
        return 'Vui long nhap ten hien thi.'
    try:
        if int(price_per_turn) < 0:
            return 'Gia luot phai >= 0.'
    except (TypeError, ValueError):
        return 'Gia luot phai la so nguyen.'
    try:
        if int(price_per_hour) < 0:
            return 'Gia theo gio phai >= 0.'
    except (TypeError, ValueError):
        return 'Gia theo gio phai la so nguyen.'
    if not _validate_time(time_open):
        return 'Gio mo cua khong hop le (dinh dang HH:MM).'
    if not _validate_time(time_close):
        return 'Gio dong cua khong hop le (dinh dang HH:MM).'
    if time_open >= time_close:
        return 'Gio mo cua phai truoc gio dong cua.'
    return None


def _parse_datetime(s):
    for fmt in DT_FORMATS:
        try:
            return datetime.datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _parse_pagination(args):
    try:
        page     = max(1, int(args.get('page', 1)))
        per_page = min(100, max(1, int(args.get('per_page', 20))))
    except (TypeError, ValueError):
        page, per_page = 1, 20
    return page, per_page


# ─── Auth decorator ───────────────────────────────────────────────────────────

def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != ROLE_ADMIN:
            return jsonify({'success': False, 'message': 'Khong co quyen truy cap'}), 403
        return f(*args, **kwargs)
    return decorated


# ─── Routes ───────────────────────────────────────────────────────────────────

# Xem danh sách bảng giá
@pricing_bp.route('/api/pricing', methods=['GET'])
@require_admin
def get_all_pricing():
    vehicle_type   = request.args.get('vehicle_type', '').strip()
    page, per_page = _parse_pagination(request.args)
    offset         = (page - 1) * per_page

    conn = _get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        if vehicle_type:
            cur.execute(
                "SELECT * FROM pricing WHERE vehicle_type=%s ORDER BY id ASC LIMIT %s OFFSET %s",
                (vehicle_type, per_page, offset)
            )
        else:
            cur.execute(
                "SELECT * FROM pricing ORDER BY id ASC LIMIT %s OFFSET %s",
                (per_page, offset)
            )
        rows = cur.fetchall()
        # Chuyển datetime sang string để JSON serialize
        for row in rows:
            for k, v in row.items():
                if isinstance(v, datetime.datetime):
                    row[k] = v.strftime('%Y-%m-%d %H:%M:%S')
        return jsonify({
            'success':  True,
            'data':     rows,
            'page':     page,
            'per_page': per_page,
        }), 200
    except Exception:
        logger.exception("get_all_pricing error")
        return jsonify({'success': False, 'message': 'Loi he thong.'}), 500
    finally:
        conn.close()


# Xem chi tiết 1 mục bảng giá
@pricing_bp.route('/api/pricing/<int:pricing_id>', methods=['GET'])
@require_admin
def get_pricing(pricing_id):
    conn = _get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM pricing WHERE id=%s", (pricing_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'Khong tim thay muc bang gia.'}), 404
        for k, v in row.items():
            if isinstance(v, datetime.datetime):
                row[k] = v.strftime('%Y-%m-%d %H:%M:%S')
        return jsonify({'success': True, 'data': row}), 200
    except Exception:
        logger.exception("get_pricing error")
        return jsonify({'success': False, 'message': 'Loi he thong.'}), 500
    finally:
        conn.close()


# Thêm mục bảng giá mới
@pricing_bp.route('/api/pricing', methods=['POST'])
@require_admin
def add_pricing():
    data = request.json or {}
    err  = _validate_pricing_input(data)
    if err:
        return jsonify({'success': False, 'message': err}), 400

    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    conn = _get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO pricing "
            "(vehicle_type, label, price_per_turn, price_per_hour, "
            " time_open, time_close, note, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                data['vehicle_type'].strip(),
                data['label'].strip(),
                int(data['price_per_turn']),
                int(data['price_per_hour']),
                data.get('time_open', '00:00'),
                data.get('time_close', '23:59'),
                (data.get('note') or '').strip(),
                now, now,
            )
        )
        new_id = cur.lastrowid
        conn.commit()
        return jsonify({'success': True, 'message': 'Them bang gia thanh cong', 'id': new_id}), 201
    except Exception:
        _rollback(conn)
        logger.exception("add_pricing error")
        return jsonify({'success': False, 'message': 'Loi he thong.'}), 500
    finally:
        conn.close()


# Cập nhật mục bảng giá
@pricing_bp.route('/api/pricing/<int:pricing_id>', methods=['PUT'])
@require_admin
def update_pricing(pricing_id):
    data = request.json or {}
    err  = _validate_pricing_input(data)
    if err:
        return jsonify({'success': False, 'message': err}), 400

    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    conn = _get_conn()
    try:
        cur = conn.cursor()

        cur.execute("SELECT id FROM pricing WHERE id=%s", (pricing_id,))
        if not cur.fetchone():
            return jsonify({'success': False, 'message': 'Khong tim thay muc bang gia.'}), 404

        cur.execute(
            "UPDATE pricing SET "
            "vehicle_type=%s, label=%s, price_per_turn=%s, price_per_hour=%s, "
            "time_open=%s, time_close=%s, note=%s, updated_at=%s "
            "WHERE id=%s",
            (
                data['vehicle_type'].strip(),
                data['label'].strip(),
                int(data['price_per_turn']),
                int(data['price_per_hour']),
                data.get('time_open', '00:00'),
                data.get('time_close', '23:59'),
                (data.get('note') or '').strip(),
                now,
                pricing_id,
            )
        )
        conn.commit()
        return jsonify({'success': True, 'message': 'Cap nhat bang gia thanh cong'}), 200
    except Exception:
        _rollback(conn)
        logger.exception("update_pricing error")
        return jsonify({'success': False, 'message': 'Loi he thong.'}), 500
    finally:
        conn.close()


# Xóa bảng giá
@pricing_bp.route('/api/pricing/<int:pricing_id>', methods=['DELETE'])
@require_admin
def delete_pricing(pricing_id):
    conn = _get_conn()
    try:
        cur = conn.cursor()

        cur.execute("SELECT id FROM pricing WHERE id=%s", (pricing_id,))
        if not cur.fetchone():
            return jsonify({'success': False, 'message': 'Khong tim thay muc bang gia.'}), 404

        cur.execute("SELECT COUNT(*) FROM pricing")
        count = cur.fetchone()[0]
        if count <= 1:
            return jsonify({'success': False, 'message': 'Phai giu lai it nhat mot muc bang gia.'}), 400

        cur.execute("DELETE FROM pricing WHERE id=%s", (pricing_id,))
        conn.commit()
        return jsonify({'success': True, 'message': 'Da xoa muc bang gia'}), 200
    except Exception:
        _rollback(conn)
        logger.exception("delete_pricing error")
        return jsonify({'success': False, 'message': 'Loi he thong.'}), 500
    finally:
        conn.close()


# Danh sách loại xe
@pricing_bp.route('/api/pricing/vehicle-types', methods=['GET'])
@require_admin
def get_vehicle_types():
    return jsonify({
        'success': True,
        'data': [{'value': k, 'label': v} for k, v in VEHICLE_TYPE_LABELS.items()]
    }), 200


# Tính phí gửi xe
@pricing_bp.route('/api/pricing/calculate', methods=['POST'])
@require_admin
def calculate_fee():
    """
    Body JSON:
      vehicle_type : str  – loai xe (xe_may, o_to, ...)
      time_in      : str  – thoi diem vao  'YYYY-MM-DD HH:MM[:SS]'
      time_out     : str  – thoi diem ra   (de trong = hien tai)
      mode         : str  – 'turn' hoac 'hourly'  mac dinh 'turn'
    """
    data         = request.json or {}
    vehicle_type = (data.get('vehicle_type') or '').strip()
    time_in_raw  = (data.get('time_in')      or '').strip()
    time_out_raw = (data.get('time_out')     or '').strip()
    mode         = (data.get('mode')         or CALC_MODE_TURN).strip().lower()

    if not vehicle_type:
        return jsonify({'success': False, 'message': 'Vui long chon loai xe.'}), 400
    if not time_in_raw:
        return jsonify({'success': False, 'message': 'Vui long nhap thoi gian vao.'}), 400
    if mode not in VALID_MODES:
        return jsonify({'success': False, 'message': "Mode phai la 'turn' hoac 'hourly'."}), 400

    time_in = _parse_datetime(time_in_raw)
    if time_in is None:
        return jsonify({'success': False, 'message': 'Dinh dang thoi gian vao khong hop le.'}), 400

    time_out = _parse_datetime(time_out_raw) if time_out_raw else datetime.datetime.now()
    if time_out is None:
        return jsonify({'success': False, 'message': 'Dinh dang thoi gian ra khong hop le.'}), 400

    if time_out < time_in:
        return jsonify({'success': False, 'message': 'Thoi gian ra khong the truoc thoi gian vao.'}), 400

    conn = _get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT * FROM pricing WHERE vehicle_type=%s ORDER BY id ASC LIMIT 1",
            (vehicle_type,)
        )
        row = cur.fetchone()
    except Exception:
        logger.exception("calculate_fee error")
        return jsonify({'success': False, 'message': 'Loi he thong.'}), 500
    finally:
        conn.close()

    if not row:
        return jsonify({
            'success': False,
            'message': f"Khong tim thay bang gia cho loai xe '{vehicle_type}'."
        }), 404

    price_per_turn = row['price_per_turn']
    price_per_hour = row['price_per_hour']
    label          = row['label']

    duration_minutes = int((time_out - time_in).total_seconds() / 60)

    if mode == CALC_MODE_TURN:
        fee          = price_per_turn
        hours_billed = None
    else:
        hours_billed = math.ceil(duration_minutes / 60) if duration_minutes > 0 else 0
        fee          = hours_billed * price_per_hour

    return jsonify({
        'success':          True,
        'fee':              fee,
        'duration_minutes': duration_minutes,
        'hours_billed':     hours_billed,
        'price_per_turn':   price_per_turn,
        'price_per_hour':   price_per_hour,
        'vehicle_type':     vehicle_type,
        'label':            label,
        'mode':             mode,
        'time_in':          time_in.strftime('%Y-%m-%d %H:%M:%S'),
        'time_out':         time_out.strftime('%Y-%m-%d %H:%M:%S'),
    }), 200

