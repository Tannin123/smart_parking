import sqlite3
import datetime
import logging
import re
from functools import wraps
from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash

DB_PATH = 'smart_parking.db'
logger  = logging.getLogger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────
ROLE_ADMIN      = 'admin'
ROLE_STAFF      = 'staff'
STATUS_ACTIVE   = 'active'
STATUS_INACTIVE = 'inactive'
VALID_ROLES     = {ROLE_ADMIN, ROLE_STAFF}
VALID_STATUSES  = {STATUS_ACTIVE, STATUS_INACTIVE}

DATE_RE          = re.compile(r'^\d{4}-\d{2}-\d{2}$')
TIME_RE          = re.compile(r'^\d{2}:\d{2}$')
PAGE_SIZE_DEFAULT = 20
PAGE_SIZE_MAX     = 100

employee_bp = Blueprint('employee_bp', __name__)


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory   = sqlite3.Row
    conn.isolation_level = None         
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _rollback(conn):
    try:
        conn.execute("ROLLBACK")
    except Exception:
        pass


def init_employee_tables():
    conn = _get_conn()
    try:
        conn.execute("BEGIN")
        conn.execute('''
            CREATE TABLE IF NOT EXISTS employees (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT    NOT NULL,
                username   TEXT    NOT NULL UNIQUE,
                password   TEXT    NOT NULL,
                role       TEXT    NOT NULL DEFAULT 'staff',
                status     TEXT    NOT NULL DEFAULT 'active',
                note       TEXT    DEFAULT '',
                created_at TEXT    NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS work_shifts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                shift_name  TEXT    NOT NULL,
                work_date   TEXT    NOT NULL,
                start_time  TEXT    NOT NULL,
                end_time    TEXT    NOT NULL,
                note        TEXT    DEFAULT '',
                created_at  TEXT    NOT NULL,
                FOREIGN KEY (employee_id) REFERENCES employees(id)
            )
        ''')
        conn.execute("COMMIT")
    except Exception:
        _rollback(conn)
        raise
    finally:
        conn.close()


def _validate_username(username):
    return bool(username and re.match(r'^[a-zA-Z0-9_]{3,50}$', username))


def _validate_password(password):
    return bool(password and len(password) >= 6)


def _validate_date(date_str):
    if not DATE_RE.match(date_str):
        return False
    try:
        datetime.datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def _validate_time(time_str):
    if not TIME_RE.match(time_str):
        return False
    try:
        datetime.datetime.strptime(time_str, '%H:%M')
        return True
    except ValueError:
        return False


def _validate_shift_input(shift_name, work_date, start_time, end_time):
    """Return error message string, or None if input is valid."""
    if not shift_name or not work_date or not start_time or not end_time:
        return 'Vui long nhap day du ten ca, ngay, gio bat dau va gio ket thuc.'
    if not _validate_date(work_date):
        return 'Ngay lam viec khong hop le (dinh dang YYYY-MM-DD).'
    if not _validate_time(start_time):
        return 'Gio bat dau khong hop le (dinh dang HH:MM).'
    if not _validate_time(end_time):
        return 'Gio ket thuc khong hop le (dinh dang HH:MM).'
    if start_time >= end_time:
        return 'Gio bat dau phai truoc gio ket thuc.'
    return None


def _count_active_admins(conn):
    row = conn.execute(
        "SELECT COUNT(*) AS cnt FROM employees WHERE role=? AND status=?",
        (ROLE_ADMIN, STATUS_ACTIVE)
    ).fetchone()
    return row['cnt']


def _parse_pagination(args):
    try:
        page     = max(1, int(args.get('page', 1)))
        per_page = min(PAGE_SIZE_MAX, max(1, int(args.get('per_page', PAGE_SIZE_DEFAULT))))
    except (TypeError, ValueError):
        page, per_page = 1, PAGE_SIZE_DEFAULT
    return page, per_page


def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != ROLE_ADMIN:
            return jsonify({'success': False, 'message': 'Khong co quyen truy cap'}), 403
        return f(*args, **kwargs)
    return decorated


# ─── Xem danh sách nhân viên ──────────────────────────────────────────────────
@employee_bp.route('/api/employees', methods=['GET'])
@require_admin
def get_employees():
    q              = request.args.get('q', '').strip()
    page, per_page = _parse_pagination(request.args)
    offset         = (page - 1) * per_page

    conn = _get_conn()
    try:
        if q:
            rows = conn.execute(
                "SELECT id, name, username, role, status, note, created_at "
                "FROM employees WHERE name LIKE ? OR username LIKE ? "
                "ORDER BY id LIMIT ? OFFSET ?",
                (f'%{q}%', f'%{q}%', per_page, offset)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, name, username, role, status, note, created_at "
                "FROM employees ORDER BY id LIMIT ? OFFSET ?",
                (per_page, offset)
            ).fetchall()
        return jsonify({
            'success': True,
            'data': [dict(r) for r in rows],
            'page': page,
            'per_page': per_page,
        }), 200
    except Exception:
        logger.exception("get_employees error")
        return jsonify({'success': False, 'message': 'Loi he thong.'}), 500
    finally:
        conn.close()


# ─── Xem chi tiết một nhân viên ───────────────────────────────────────────────
@employee_bp.route('/api/employees/<int:emp_id>', methods=['GET'])
@require_admin
def get_employee(emp_id):
    conn = _get_conn()
    try:
        emp = conn.execute(
            "SELECT id, name, username, role, status, note, created_at "
            "FROM employees WHERE id=?", (emp_id,)
        ).fetchone()
        if not emp:
            return jsonify({'success': False, 'message': 'Khong tim thay nhan vien.'}), 404
        return jsonify({'success': True, 'data': dict(emp)}), 200
    except Exception:
        logger.exception("get_employee error")
        return jsonify({'success': False, 'message': 'Loi he thong.'}), 500
    finally:
        conn.close()


# ─── Thêm nhân viên ───────────────────────────────────────────────────────────
@employee_bp.route('/api/employees', methods=['POST'])
@require_admin
def add_employee():
    data     = request.json or {}
    name     = data.get('name', '').strip()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    role     = data.get('role', ROLE_STAFF)
    status   = data.get('status', STATUS_ACTIVE)
    note     = data.get('note', '').strip()

    if not name or not username or not password:
        return jsonify({'success': False, 'message': 'Vui long nhap day du ho ten, tai khoan va mat khau.'}), 400
    if not _validate_username(username):
        return jsonify({'success': False, 'message': 'Tai khoan khong hop le (3-50 ky tu, chi chu va so).'}), 400
    if not _validate_password(password):
        return jsonify({'success': False, 'message': 'Mat khau phai co it nhat 6 ky tu.'}), 400
    if role not in VALID_ROLES:
        return jsonify({'success': False, 'message': f'Role khong hop le. Chi chap nhan: {", ".join(VALID_ROLES)}.'}), 400
    if status not in VALID_STATUSES:
        return jsonify({'success': False, 'message': f'Status khong hop le. Chi chap nhan: {", ".join(VALID_STATUSES)}.'}), 400

    hashed = generate_password_hash(password)
    now    = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    conn = _get_conn()
    try:
        conn.execute("BEGIN")
        cur = conn.execute(
            "INSERT INTO employees (name, username, password, role, status, note, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (name, username, hashed, role, status, note, now)
        )
        new_id = cur.lastrowid
        conn.execute("COMMIT")
        return jsonify({'success': True, 'message': 'Them nhan vien thanh cong', 'id': new_id}), 201
    except sqlite3.IntegrityError:
        _rollback(conn)
        return jsonify({'success': False, 'message': 'Tai khoan da ton tai trong he thong.'}), 400
    except Exception:
        _rollback(conn)
        logger.exception("add_employee error")
        return jsonify({'success': False, 'message': 'Loi he thong.'}), 500
    finally:
        conn.close()


# ─── Sửa thông tin nhân viên ──────────────────────────────────────────────────
@employee_bp.route('/api/employees/<int:emp_id>', methods=['PUT'])
@require_admin
def update_employee(emp_id):
    data     = request.json or {}
    name     = data.get('name', '').strip()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    note     = data.get('note', '').strip()

    new_role   = data.get('role')
    new_status = data.get('status')

    if not name or not username:
        return jsonify({'success': False, 'message': 'Vui long nhap ho ten va tai khoan.'}), 400
    if not _validate_username(username):
        return jsonify({'success': False, 'message': 'Tai khoan khong hop le.'}), 400
    if password and not _validate_password(password):
        return jsonify({'success': False, 'message': 'Mat khau moi phai co it nhat 6 ky tu.'}), 400
    if new_role is not None and new_role not in VALID_ROLES:
        return jsonify({'success': False, 'message': f'Role khong hop le. Chi chap nhan: {", ".join(VALID_ROLES)}.'}), 400
    if new_status is not None and new_status not in VALID_STATUSES:
        return jsonify({'success': False, 'message': f'Status khong hop le. Chi chap nhan: {", ".join(VALID_STATUSES)}.'}), 400

    conn = _get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")

        current = conn.execute(
            "SELECT role, status FROM employees WHERE id=?", (emp_id,)
        ).fetchone()
        if not current:
            _rollback(conn)
            return jsonify({'success': False, 'message': 'Khong tim thay nhan vien.'}), 404

        role   = new_role   if new_role   is not None else current['role']
        status = new_status if new_status is not None else current['status']

        is_demotion   = current['role'] == ROLE_ADMIN and role != ROLE_ADMIN
        is_deactivate = (current['role'] == ROLE_ADMIN
                         and current['status'] == STATUS_ACTIVE
                         and status != STATUS_ACTIVE)

        if is_demotion or is_deactivate:
            if emp_id == session.get('user_id'):
                _rollback(conn)
                return jsonify({'success': False, 'message': 'Khong the tu thay doi quyen cua chinh minh.'}), 400
            if _count_active_admins(conn) <= 1:
                _rollback(conn)
                return jsonify({'success': False, 'message': 'Khong the ha quyen hoac vo hieu hoa admin cuoi cung.'}), 400

        if password:
            hashed = generate_password_hash(password)
            conn.execute(
                "UPDATE employees SET name=?, username=?, password=?, role=?, status=?, note=? WHERE id=?",
                (name, username, hashed, role, status, note, emp_id)
            )
        else:
            conn.execute(
                "UPDATE employees SET name=?, username=?, role=?, status=?, note=? WHERE id=?",
                (name, username, role, status, note, emp_id)
            )
        conn.execute("COMMIT")
        return jsonify({'success': True, 'message': 'Cap nhat thanh cong'}), 200

    except sqlite3.IntegrityError:
        _rollback(conn)
        return jsonify({'success': False, 'message': 'Tai khoan (username) nay da bi trung lap.'}), 400
    except Exception:
        _rollback(conn)
        logger.exception("update_employee error")
        return jsonify({'success': False, 'message': 'Loi he thong.'}), 500
    finally:
        conn.close()


# ─── Xóa nhân viên ────────────────────────────────────────────────────────────
@employee_bp.route('/api/employees/<int:emp_id>', methods=['DELETE'])
@require_admin
def delete_employee(emp_id):
    conn = _get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")

        emp = conn.execute(
            "SELECT id, role, status FROM employees WHERE id=?", (emp_id,)
        ).fetchone()
        if not emp:
            _rollback(conn)
            return jsonify({'success': False, 'message': 'Khong tim thay nhan vien.'}), 404
        if emp_id == session.get('user_id'):
            _rollback(conn)
            return jsonify({'success': False, 'message': 'Khong the xoa tai khoan cua chinh minh.'}), 400
        if emp['role'] == ROLE_ADMIN and emp['status'] == STATUS_ACTIVE and _count_active_admins(conn) <= 1:
            _rollback(conn)
            return jsonify({'success': False, 'message': 'Khong the xoa admin cuoi cung.'}), 400

        conn.execute("DELETE FROM employees WHERE id=?", (emp_id,))
        conn.execute("COMMIT")
        return jsonify({'success': True, 'message': 'Da xoa nhan vien'}), 200

    except Exception:
        _rollback(conn)
        logger.exception("delete_employee error")
        return jsonify({'success': False, 'message': 'Loi he thong.'}), 500
    finally:
        conn.close()


# ═══ PHÂN CÔNG CA TRỰC ════════════════════════════════════════════════════════

# ─── Xem ca trực của nhân viên ────────────────────────────────────────────────
@employee_bp.route('/api/employees/<int:emp_id>/shifts', methods=['GET'])
@require_admin
def get_shifts(emp_id):
    page, per_page = _parse_pagination(request.args)
    offset         = (page - 1) * per_page

    conn = _get_conn()
    try:
        if not conn.execute("SELECT id FROM employees WHERE id=?", (emp_id,)).fetchone():
            return jsonify({'success': False, 'message': 'Khong tim thay nhan vien.'}), 404

        rows = conn.execute(
            "SELECT id, shift_name, work_date, start_time, end_time, note, created_at "
            "FROM work_shifts WHERE employee_id=? "
            "ORDER BY work_date, start_time LIMIT ? OFFSET ?",
            (emp_id, per_page, offset)
        ).fetchall()
        return jsonify({
            'success': True,
            'data': [dict(r) for r in rows],
            'page': page,
            'per_page': per_page,
        }), 200
    except Exception:
        logger.exception("get_shifts error")
        return jsonify({'success': False, 'message': 'Loi he thong.'}), 500
    finally:
        conn.close()


# ─── Phân công ca trực ────────────────────────────────────────────────────────
@employee_bp.route('/api/employees/<int:emp_id>/shifts', methods=['POST'])
@require_admin
def assign_shift(emp_id):
    data       = request.json or {}
    shift_name = data.get('shift_name', '').strip()
    work_date  = data.get('work_date', '').strip()
    start_time = data.get('start_time', '').strip()
    end_time   = data.get('end_time', '').strip()
    note       = data.get('note', '').strip()

    err = _validate_shift_input(shift_name, work_date, start_time, end_time)
    if err:
        return jsonify({'success': False, 'message': err}), 400

    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    conn = _get_conn()
    try:
        conn.execute("BEGIN")
        if not conn.execute("SELECT id FROM employees WHERE id=?", (emp_id,)).fetchone():
            _rollback(conn)
            return jsonify({'success': False, 'message': 'Khong tim thay nhan vien.'}), 404

        cur = conn.execute(
            "INSERT INTO work_shifts (employee_id, shift_name, work_date, start_time, end_time, note, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (emp_id, shift_name, work_date, start_time, end_time, note, now)
        )
        new_id = cur.lastrowid
        conn.execute("COMMIT")
        return jsonify({'success': True, 'message': 'Phan cong ca truc thanh cong', 'id': new_id}), 201
    except Exception:
        _rollback(conn)
        logger.exception("assign_shift error")
        return jsonify({'success': False, 'message': 'Loi he thong.'}), 500
    finally:
        conn.close()


# ─── Sửa ca trực ──────────────────────────────────────────────────────────────
@employee_bp.route('/api/employees/<int:emp_id>/shifts/<int:shift_id>', methods=['PUT'])
@require_admin
def update_shift(emp_id, shift_id):
    data       = request.json or {}
    shift_name = data.get('shift_name', '').strip()
    work_date  = data.get('work_date', '').strip()
    start_time = data.get('start_time', '').strip()
    end_time   = data.get('end_time', '').strip()
    note       = data.get('note', '').strip()

    err = _validate_shift_input(shift_name, work_date, start_time, end_time)
    if err:
        return jsonify({'success': False, 'message': err}), 400

    conn = _get_conn()
    try:
        conn.execute("BEGIN")
        if not conn.execute(
            "SELECT id FROM work_shifts WHERE id=? AND employee_id=?", (shift_id, emp_id)
        ).fetchone():
            _rollback(conn)
            return jsonify({'success': False, 'message': 'Khong tim thay ca truc nay.'}), 404

        conn.execute(
            "UPDATE work_shifts SET shift_name=?, work_date=?, start_time=?, end_time=?, note=? WHERE id=?",
            (shift_name, work_date, start_time, end_time, note, shift_id)
        )
        conn.execute("COMMIT")
        return jsonify({'success': True, 'message': 'Cap nhat ca truc thanh cong'}), 200
    except Exception:
        _rollback(conn)
        logger.exception("update_shift error")
        return jsonify({'success': False, 'message': 'Loi he thong.'}), 500
    finally:
        conn.close()


# ─── Xóa ca trực ──────────────────────────────────────────────────────────────
@employee_bp.route('/api/employees/<int:emp_id>/shifts/<int:shift_id>', methods=['DELETE'])
@require_admin
def delete_shift(emp_id, shift_id):
    conn = _get_conn()
    try:
        conn.execute("BEGIN")
        if not conn.execute(
            "SELECT id FROM work_shifts WHERE id=? AND employee_id=?", (shift_id, emp_id)
        ).fetchone():
            _rollback(conn)
            return jsonify({'success': False, 'message': 'Khong tim thay ca truc nay.'}), 404

        conn.execute("DELETE FROM work_shifts WHERE id=?", (shift_id,))
        conn.execute("COMMIT")
        return jsonify({'success': True, 'message': 'Da xoa ca truc'}), 200
    except Exception:
        _rollback(conn)
        logger.exception("delete_shift error")
        return jsonify({'success': False, 'message': 'Loi he thong.'}), 500
    finally:
        conn.close()
