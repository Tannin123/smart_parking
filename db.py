import MySQLdb
import MySQLdb.cursors
import datetime
import logging
import os
from config import DB_HOST, DB_USER, DB_PASS, DB_NAME

def get_connection(with_db=True):
    try:
        if with_db:
            return MySQLdb.connect(
                host=DB_HOST,
                user=DB_USER,
                passwd=DB_PASS,
                db=DB_NAME,
                charset='utf8mb4'
            )
        else:
            return MySQLdb.connect(
                host=DB_HOST,
                user=DB_USER,
                passwd=DB_PASS,
                charset='utf8mb4'
            )
    except MySQLdb.Error as e:
        logging.error(f"[DB] Lỗi kết nối MySQL: {e}")
        return None

def init_db():
    """Tạo database và các bảng nếu chưa tồn tại."""
    conn = get_connection(with_db=False)
    if not conn: return
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    conn.commit()
    conn.close()

    conn = get_connection()
    if not conn: return
    cur = conn.cursor()
    
    # 1. Bảng parking_logs
    cur.execute('''
        CREATE TABLE IF NOT EXISTS parking_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            plate VARCHAR(255) NOT NULL,
            time_in DATETIME NOT NULL,
            time_out DATETIME,
            status VARCHAR(50) NOT NULL
        )
    ''')

    # 2. Bảng users
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL,
            role VARCHAR(20) DEFAULT 'employee',
            first_name VARCHAR(50),
            last_name VARCHAR(50),
            dob VARCHAR(20),
            gender VARCHAR(10),
            address VARCHAR(255),
            status VARCHAR(20) DEFAULT 'active',
            note TEXT,
            created_at DATETIME
        )
    ''')
    try:
        cur.execute("ALTER TABLE users ADD COLUMN status VARCHAR(20) DEFAULT 'active'")
        cur.execute("ALTER TABLE users ADD COLUMN note TEXT")
        cur.execute("ALTER TABLE users ADD COLUMN created_at DATETIME")
    except:
        pass

    # 2.5 Bảng work_shifts
    cur.execute('''
        CREATE TABLE IF NOT EXISTS work_shifts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            employee_id INT NOT NULL,
            shift_name VARCHAR(100) NOT NULL,
            work_date DATE NOT NULL,
            start_time TIME NOT NULL,
            end_time TIME NOT NULL,
            note TEXT,
            created_at DATETIME,
            FOREIGN KEY (employee_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ''')

    # 3. Bảng pricing — do pricing.py quản lý schema, db.py không tạo lại
    #    (tránh xung đột cột cũ: type/price_turn vs. vehicle_type/price_per_hour)

    # Thêm tài khoản admin mặc định
    cur.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cur.fetchone():
        cur.execute("INSERT INTO users (username, password, role) VALUES ('admin', 'admin123', 'admin')")
    
    # Migration: thêm cột vehicle_type vào parking_logs nếu chưa có
    try:
        cur.execute("ALTER TABLE parking_logs ADD COLUMN vehicle_type VARCHAR(50) DEFAULT 'xe_may'")
    except:
        pass

    conn.commit()
    conn.close()
    logging.info("[DB] Đã khởi tạo cấu trúc CSDL đầy đủ.")

# === MODULE NHẬN DIỆN ===
def check_in(plate: str, vehicle_type: str = 'xe_may') -> tuple[bool, str]:
    conn = get_connection()
    if not conn: return False, "Lỗi kết nối CSDL!"
    cur = conn.cursor()
    # Migration: đảm bảo cột vehicle_type tồn tại
    try:
        cur.execute("ALTER TABLE parking_logs ADD COLUMN vehicle_type VARCHAR(50) DEFAULT 'xe_may'")
    except:
        pass
    cur.execute("SELECT id FROM parking_logs WHERE plate = %s AND status = 'IN'", (plate,))
    if cur.fetchone():
        conn.close()
        return False, "Xe đang ở trong bãi, chưa được cho ra!"
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("INSERT INTO parking_logs (plate, time_in, status, vehicle_type) VALUES (%s, %s, 'IN', %s)", (plate, now_str, vehicle_type))
    conn.commit()
    conn.close()
    return True, "Cho xe vào thành công!"

def check_in_obscured(vehicle_type: str = 'xe_may', temp_id: str = None) -> tuple[bool, str, str]:
    """
    Ghi nhận xe vào bãi nhưng biển số bị che khuất.
    Tạo ID tạm (OBSCURED_<uuid>) để theo dõi, lưu ảnh nếu có.
    Trả về (success, message, temp_plate_id).
    """
    import uuid as _uuid
    conn = get_connection()
    if not conn:
        return False, "Lỗi kết nối CSDL!", ""
    cur = conn.cursor()
    try:
        cur.execute("ALTER TABLE parking_logs ADD COLUMN vehicle_type VARCHAR(50) DEFAULT 'xe_may'")
    except:
        pass
    try:
        cur.execute("ALTER TABLE parking_logs ADD COLUMN is_obscured TINYINT(1) DEFAULT 0")
    except:
        pass

    # Tạo biển số tạm nếu không truyền vào
    if not temp_id:
        temp_id = f"OBSCURED_{_uuid.uuid4().hex[:8].upper()}"

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        "INSERT INTO parking_logs (plate, time_in, status, vehicle_type, is_obscured) "
        "VALUES (%s, %s, 'IN', %s, 1)",
        (temp_id, now_str, vehicle_type)
    )
    conn.commit()
    conn.close()
    logging.warning(f"[DB] Xe vào bãi với biển số bị che — ID tạm: {temp_id}")
    return True, f"Đã ghi nhận xe vào (biển số bị che). ID tạm: {temp_id}", temp_id

def check_out_obscured(temp_plate_id: str) -> tuple[bool, str, int]:
    """
    Cho xe có biển bị che ra khỏi bãi bằng ID tạm.
    Tính phí theo giờ với giá xe_may mặc định.
    """
    conn = get_connection()
    if not conn:
        return False, "Lỗi kết nối CSDL!", 0
    cur = conn.cursor(MySQLdb.cursors.DictCursor)
    try:
        cur.execute("ALTER TABLE parking_logs ADD COLUMN fee INT DEFAULT 0")
    except:
        pass

    cur.execute(
        "SELECT id, time_in, vehicle_type FROM parking_logs "
        "WHERE plate = %s AND status = 'IN' ORDER BY id DESC LIMIT 1",
        (temp_plate_id,)
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        return False, "Không tìm thấy bản ghi xe bị che này!", 0

    log_id   = row['id']
    time_in  = row['time_in']
    vehicle_type = row.get('vehicle_type') or 'xe_may'
    if isinstance(time_in, str):
        time_in = datetime.datetime.strptime(time_in, "%Y-%m-%d %H:%M:%S")

    import math
    now = datetime.datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    duration_minutes = int((now - time_in).total_seconds() / 60)
    hours_billed = math.ceil(duration_minutes / 60) if duration_minutes > 0 else 1

    cur.execute(
        "SELECT price_per_hour FROM pricing WHERE vehicle_type = %s ORDER BY id ASC LIMIT 1",
        (vehicle_type,)
    )
    p_row = cur.fetchone()
    if not p_row:
        cur.execute("SELECT price_per_hour FROM pricing ORDER BY id ASC LIMIT 1")
        p_row = cur.fetchone()
    price_per_hour = p_row['price_per_hour'] if p_row else 5000
    fee = hours_billed * price_per_hour

    cur.execute(
        "UPDATE parking_logs SET time_out = %s, status = 'OUT', fee = %s WHERE id = %s",
        (now_str, fee, log_id)
    )
    conn.commit()
    conn.close()
    logging.info(f"[DB] Xe bị che biển ra bãi — ID tạm: {temp_plate_id}, phí: {fee}")
    return True, f"Xe ra thành công. Phí: {fee:,}đ", fee

def get_obscured_logs(limit: int = 20) -> list[dict]:
    """Trả về danh sách các xe vào bãi có biển số bị che khuất."""
    conn = get_connection()
    if not conn:
        return []
    cur = conn.cursor(MySQLdb.cursors.DictCursor)
    try:
        cur.execute("ALTER TABLE parking_logs ADD COLUMN is_obscured TINYINT(1) DEFAULT 0")
    except:
        pass
    cur.execute(
        "SELECT * FROM parking_logs WHERE is_obscured = 1 ORDER BY id DESC LIMIT %s",
        (limit,)
    )
    rows = cur.fetchall()
    conn.close()
    res = []
    for row in rows:
        r = dict(row)
        for k, v in r.items():
            if isinstance(v, datetime.datetime):
                r[k] = v.strftime("%Y-%m-%d %H:%M:%S")
        res.append(r)
    return res

def check_out(plate: str) -> tuple[bool, str, int]:
    conn = get_connection()
    if not conn: return False, "Lỗi kết nối CSDL!", 0
    cur = conn.cursor(MySQLdb.cursors.DictCursor)
    try:
        cur.execute("ALTER TABLE parking_logs ADD COLUMN fee INT DEFAULT 0")
    except:
        pass
    cur.execute("SELECT id, time_in, vehicle_type FROM parking_logs WHERE plate = %s AND status = 'IN' ORDER BY id DESC LIMIT 1", (plate,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False, "Xe này chưa được giữ hoặc đã ra khỏi bãi!", 0
    log_id = row['id']
    time_in = row['time_in']
    if isinstance(time_in, str):
        time_in = datetime.datetime.strptime(time_in, "%Y-%m-%d %H:%M:%S")
    now = datetime.datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    # Lấy vehicle_type của xe này
    vehicle_type = row.get('vehicle_type') or 'xe_may'

    # Tính số giờ đỗ (làm tròn lên, tối thiểu 1 giờ)
    import math
    duration_minutes = int((now - time_in).total_seconds() / 60)
    hours_billed = math.ceil(duration_minutes / 60) if duration_minutes > 0 else 1

    # Lấy giá từ bảng pricing đúng loại xe
    cur.execute("SELECT price_per_hour FROM pricing WHERE vehicle_type = %s ORDER BY id ASC LIMIT 1", (vehicle_type,))
    p_row = cur.fetchone()
    if not p_row:
        # Fallback: lấy bất kỳ hàng nào
        cur.execute("SELECT price_per_hour FROM pricing ORDER BY id ASC LIMIT 1")
        p_row = cur.fetchone()
    price_per_hour = p_row['price_per_hour'] if p_row else 5000

    fee = hours_billed * price_per_hour

    cur.execute("UPDATE parking_logs SET time_out = %s, status = 'OUT', fee = %s WHERE id = %s", (now_str, fee, log_id))
    conn.commit()
    conn.close()
    return True, "Cho xe ra thành công!", fee

def get_recent_logs(limit: int = 20) -> list[dict]:
    conn = get_connection()
    if not conn: return []
    cur = conn.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM parking_logs ORDER BY id DESC LIMIT %s", (limit,))
    rows = cur.fetchall()
    conn.close()
    res = []
    for row in rows:
        r = dict(row)
        for k, v in r.items():
            if isinstance(v, datetime.datetime): r[k] = v.strftime("%Y-%m-%d %H:%M:%S")
        res.append(r)
    return res

# === MODULE TÀI KHOẢN (USERS) ===
def verify_login(username, password):
    conn = get_connection()
    if not conn: return False, None
    cur = conn.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT id, username, role FROM users WHERE username = %s AND password = %s", (username, password))
    user = cur.fetchone()
    conn.close()
    if user: return True, dict(user)
    return False, None

def change_password(user_id, old_password, new_password):
    conn = get_connection()
    if not conn: return False, "Lỗi kết nối CSDL"
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE id = %s AND password = %s", (user_id, old_password))
    if not cur.fetchone():
        conn.close()
        return False, "Mật khẩu cũ không đúng"
    cur.execute("UPDATE users SET password = %s WHERE id = %s", (new_password, user_id))
    conn.commit()
    conn.close()
    return True, "Đổi mật khẩu thành công"

def get_users():
    conn = get_connection()
    if not conn: return []
    cur = conn.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT id, username, role, first_name, last_name, dob, gender, address, status, note, created_at FROM users ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_user_by_id(user_id):
    conn = get_connection()
    if not conn: return None
    cur = conn.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT id, username, role, first_name, last_name, dob, gender, address, status, note, created_at FROM users WHERE id = %s", (user_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def add_user(data):
    conn = get_connection()
    if not conn: return False
    cur = conn.cursor()
    try:
        username = data.get('username', data.get('empId'))
        password = data.get('password', '123456')
        role = data.get('role', 'employee')
        status = data.get('status', 'active')
        note = data.get('note', '')
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("""
            INSERT INTO users (username, password, first_name, last_name, dob, gender, address, role, status, note, created_at) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (username, password, data.get('firstName', data.get('name')), data.get('lastName', ''), data.get('dob'), data.get('gender'), data.get('address'), role, status, note, now_str))
        new_id = cur.lastrowid
        conn.commit()
        return new_id
    except Exception as e:
        logging.error(f"Error adding user: {e}")
        return False
    finally:
        conn.close()

def update_user(user_id, data):
    conn = get_connection()
    if not conn: return False
    cur = conn.cursor()
    try:
        # Lấy thông tin cũ
        cur.execute("SELECT role, status FROM users WHERE id=%s", (user_id,))
        current = cur.fetchone()
        if not current: return False
        
        username = data.get('username', data.get('empId'))
        role = data.get('role', current[0])
        status = data.get('status', current[1])
        note = data.get('note', '')
        
        if 'password' in data and data['password']:
            cur.execute("""
                UPDATE users SET username=%s, password=%s, first_name=%s, last_name=%s, dob=%s, gender=%s, address=%s, role=%s, status=%s, note=%s
                WHERE id=%s
            """, (username, data['password'], data.get('firstName', data.get('name')), data.get('lastName', ''), data.get('dob'), data.get('gender'), data.get('address'), role, status, note, user_id))
        else:
            cur.execute("""
                UPDATE users SET username=%s, first_name=%s, last_name=%s, dob=%s, gender=%s, address=%s, role=%s, status=%s, note=%s
                WHERE id=%s
            """, (username, data.get('firstName', data.get('name')), data.get('lastName', ''), data.get('dob'), data.get('gender'), data.get('address'), role, status, note, user_id))
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error updating user: {e}")
        return False
    finally:
        conn.close()

def delete_user(user_id):
    conn = get_connection()
    if not conn: return False
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def get_shifts(user_id, limit=20, offset=0):
    conn = get_connection()
    if not conn: return []
    cur = conn.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM work_shifts WHERE employee_id=%s ORDER BY work_date, start_time LIMIT %s OFFSET %s", (user_id, limit, offset))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_shift_by_id(shift_id):
    conn = get_connection()
    if not conn: return None
    cur = conn.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM work_shifts WHERE id=%s", (shift_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def add_shift(user_id, data):
    conn = get_connection()
    if not conn: return False
    cur = conn.cursor()
    try:
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("""
            INSERT INTO work_shifts (employee_id, shift_name, work_date, start_time, end_time, note, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (user_id, data.get('shift_name'), data.get('work_date'), data.get('start_time'), data.get('end_time'), data.get('note'), now_str))
        new_id = cur.lastrowid
        conn.commit()
        return new_id
    except Exception as e:
        logging.error(f"Error adding shift: {e}")
        return False
    finally:
        conn.close()

def update_shift(shift_id, data):
    conn = get_connection()
    if not conn: return False
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE work_shifts SET shift_name=%s, work_date=%s, start_time=%s, end_time=%s, note=%s WHERE id=%s
        """, (data.get('shift_name'), data.get('work_date'), data.get('start_time'), data.get('end_time'), data.get('note'), shift_id))
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error updating shift: {e}")
        return False
    finally:
        conn.close()

def delete_shift(shift_id):
    conn = get_connection()
    if not conn: return False
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM work_shifts WHERE id=%s", (shift_id,))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

# === MODULE BẢNG GIÁ (PRICING) — dùng schema mới từ pricing.py ===
def get_pricing():
    conn = get_connection()
    if not conn: return []
    cur = conn.cursor(MySQLdb.cursors.DictCursor)
    cur.execute("SELECT * FROM pricing ORDER BY id ASC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_pricing(data):
    conn = get_connection()
    if not conn: return False
    cur = conn.cursor()
    try:
        import datetime as _dt
        now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            "INSERT INTO pricing (vehicle_type, label, price_per_turn, price_per_hour, "
            "free_minutes, time_open, time_close, note, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                data.get('vehicle_type', ''),
                data.get('label', data.get('type', '')),
                data.get('price_per_turn', 0),
                data.get('price_per_hour', data.get('price_turn', 0)),
                data.get('free_minutes', 0),
                data.get('time_open', data.get('time_in', '06:00')),
                data.get('time_close', data.get('time_out', '22:00')),
                data.get('note', ''),
                now, now,
            )
        )
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error add_pricing: {e}")
        return False
    finally:
        conn.close()

def update_pricing(pricing_id, data):
    conn = get_connection()
    if not conn: return False
    cur = conn.cursor()
    try:
        import datetime as _dt
        now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            "UPDATE pricing SET vehicle_type=%s, label=%s, price_per_turn=%s, price_per_hour=%s, "
            "free_minutes=%s, time_open=%s, time_close=%s, note=%s, updated_at=%s WHERE id=%s",
            (
                data.get('vehicle_type', ''),
                data.get('label', data.get('type', '')),
                data.get('price_per_turn', 0),
                data.get('price_per_hour', data.get('price_turn', 0)),
                data.get('free_minutes', 0),
                data.get('time_open', data.get('time_in', '06:00')),
                data.get('time_close', data.get('time_out', '22:00')),
                data.get('note', ''),
                now,
                pricing_id,
            )
        )
        conn.commit()
        return True
    except Exception as e:
        logging.error(f"Error update_pricing: {e}")
        return False
    finally:
        conn.close()

def delete_pricing(pricing_id):
    conn = get_connection()
    if not conn: return False
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM pricing WHERE id=%s", (pricing_id,))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

# === MODULE THỐNG KÊ (REPORT) ===
def get_report_data(from_date_str, to_date_str):
    conn = get_connection()
    if not conn: return {"tableData": [], "barChartLabels": [], "barChartData": []}
    cur = conn.cursor(MySQLdb.cursors.DictCursor)
    try:
        # Check if fee column exists
        cur.execute("SHOW COLUMNS FROM parking_logs LIKE 'fee'")
        if not cur.fetchone():
            cur.execute("ALTER TABLE parking_logs ADD COLUMN fee INT DEFAULT 0")
            conn.commit()
            
        # Thống kê tổng quan
        query = """
        SELECT 
            COUNT(*) as total_in,
            SUM(CASE WHEN status = 'OUT' THEN 1 ELSE 0 END) as total_out,
            SUM(CASE WHEN status = 'OUT' THEN fee ELSE 0 END) as total_revenue
        FROM parking_logs
        WHERE time_in >= %s AND time_in <= %s
        """
        cur.execute(query, (from_date_str, to_date_str))
        row = cur.fetchone()
        
        total_revenue = int(row['total_revenue'] or 0) if row else 0
        total_in = int(row['total_in'] or 0) if row else 0
        total_out = int(row['total_out'] or 0) if row else 0
        
        tableData = [
            {
                "name": "Tất cả",
                "doanhthu": total_revenue,
                "vao": total_in,
                "ra": total_out,
                "highlight": True
            }
        ]
        
        # Thống kê biểu đồ theo ngày
        query_daily = """
        SELECT 
            DATE(time_in) as log_date,
            COUNT(*) as count_in
        FROM parking_logs
        WHERE time_in >= %s AND time_in <= %s
        GROUP BY DATE(time_in)
        ORDER BY DATE(time_in) ASC
        """
        cur.execute(query_daily, (from_date_str, to_date_str))
        daily_rows = cur.fetchall()
        
        barLabels = []
        barData = []
        for dr in daily_rows:
            date_obj = dr['log_date']
            barLabels.append(date_obj.strftime('%d/%m'))
            barData.append(dr['count_in'])
            
        return {
            "tableData": tableData,
            "barChartLabels": barLabels,
            "barChartData": barData
        }
    except Exception as e:
        logging.error(f"Error getting report data: {e}")
        return {"tableData": [], "barChartLabels": [], "barChartData": []}
    finally:
        conn.close()

# === MODULE DEBUG ===
def debug_check():
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    conn = get_connection()
    if not conn:
        print("Lỗi kết nối CSDL")
        return
    cur = conn.cursor(MySQLdb.cursors.DictCursor)
    
    print("=== PRICING ===")
    cur.execute("SELECT id, vehicle_type, label, price_per_turn, price_per_hour FROM pricing ORDER BY id")
    for r in cur.fetchall():
        print(dict(r))

    print("\n=== RECENT parking_logs ===")
    cur.execute("SELECT id, plate, status, vehicle_type, time_in, time_out, fee FROM parking_logs ORDER BY id DESC LIMIT 5")
    for r in cur.fetchall():
        print(dict(r))

    conn.close()

