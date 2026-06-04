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
            address VARCHAR(255)
        )
    ''')

    # 3. Bảng pricing
    cur.execute('''
        CREATE TABLE IF NOT EXISTS pricing (
            id INT AUTO_INCREMENT PRIMARY KEY,
            type VARCHAR(50) NOT NULL,
            price_turn INT NOT NULL,
            time_in VARCHAR(20),
            time_out VARCHAR(20),
            note VARCHAR(255)
        )
    ''')

    # Thêm tài khoản admin mặc định
    cur.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cur.fetchone():
        cur.execute("INSERT INTO users (username, password, role) VALUES ('admin', 'admin123', 'admin')")
    
    # Thêm cấu hình giá mặc định
    cur.execute("SELECT count(*) FROM pricing")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO pricing (type, price_turn, time_in, time_out, note) VALUES ('Xe Máy', 5000, '06:00', '22:00', 'Thường ngày')")
        cur.execute("INSERT INTO pricing (type, price_turn, time_in, time_out, note) VALUES ('Xe Tay Ga', 5000, '06:00', '22:00', 'Thường ngày')")
        cur.execute("INSERT INTO pricing (type, price_turn, time_in, time_out, note) VALUES ('Ô tô', 15000, '06:00', '22:00', '')")

    conn.commit()
    conn.close()
    logging.info("[DB] Đã khởi tạo cấu trúc CSDL đầy đủ.")

# === MODULE NHẬN DIỆN ===
def check_in(plate: str) -> tuple[bool, str]:
    conn = get_connection()
    if not conn: return False, "Lỗi kết nối CSDL!"
    cur = conn.cursor()
    cur.execute("SELECT id FROM parking_logs WHERE plate = %s AND status = 'IN'", (plate,))
    if cur.fetchone():
        conn.close()
        return False, "Xe đang ở trong bãi, chưa được cho ra!"
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("INSERT INTO parking_logs (plate, time_in, status) VALUES (%s, %s, 'IN')", (plate, now_str))
    conn.commit()
    conn.close()
    return True, "Cho xe vào thành công!"

def check_out(plate: str) -> tuple[bool, str, int]:
    conn = get_connection()
    if not conn: return False, "Lỗi kết nối CSDL!", 0
    cur = conn.cursor(MySQLdb.cursors.DictCursor)
    try:
        cur.execute("ALTER TABLE parking_logs ADD COLUMN fee INT DEFAULT 0")
    except:
        pass
    cur.execute("SELECT id FROM parking_logs WHERE plate = %s AND status = 'IN' ORDER BY id DESC LIMIT 1", (plate,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False, "Xe này chưa được giữ hoặc đã ra khỏi bãi!", 0
    log_id = row['id']
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("SELECT price_turn FROM pricing ORDER BY id ASC LIMIT 1")
    p_row = cur.fetchone()
    fee = p_row['price_turn'] if p_row else 5000
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
    cur.execute("SELECT id, username, role, first_name, last_name, dob, gender, address FROM users ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_user(data):
    conn = get_connection()
    if not conn: return False
    cur = conn.cursor()
    try:
        # Use username as default if username not explicitly provided in employee form
        # We assume data is from employee form: empId (username), firstName, lastName, dob, gender, address
        username = data.get('username', data.get('empId'))
        # Password default to 123456 for new employees
        password = data.get('password', '123456')
        cur.execute("""
            INSERT INTO users (username, password, first_name, last_name, dob, gender, address, role) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'employee')
        """, (username, password, data.get('firstName'), data.get('lastName'), data.get('dob'), data.get('gender'), data.get('address')))
        conn.commit()
        return True
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
        username = data.get('username', data.get('empId'))
        cur.execute("""
            UPDATE users SET username=%s, first_name=%s, last_name=%s, dob=%s, gender=%s, address=%s 
            WHERE id=%s
        """, (username, data.get('firstName'), data.get('lastName'), data.get('dob'), data.get('gender'), data.get('address'), user_id))
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

# === MODULE BẢNG GIÁ (PRICING) ===
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
        cur.execute("INSERT INTO pricing (type, price_turn, time_in, time_out, note) VALUES (%s, %s, %s, %s, %s)", 
                    (data.get('type'), data.get('price_turn', 0), data.get('time_in'), data.get('time_out'), data.get('note')))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def update_pricing(pricing_id, data):
    conn = get_connection()
    if not conn: return False
    cur = conn.cursor()
    try:
        cur.execute("UPDATE pricing SET type=%s, price_turn=%s, time_in=%s, time_out=%s, note=%s WHERE id=%s", 
                    (data.get('type'), data.get('price_turn', 0), data.get('time_in'), data.get('time_out'), data.get('note'), pricing_id))
        conn.commit()
        return True
    except:
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

