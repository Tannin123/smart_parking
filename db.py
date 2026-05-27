import sqlite3
import datetime
import logging
import os

DB_PATH = 'smart_parking.db'

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    """Tạo bảng lưu lịch sử xe ra vào nếu chưa tồn tại."""
    conn = get_connection()
    cur = conn.cursor()
    # Bảng hiện tại (bang_bien_so) không có cột trạng thái. 
    # Tốt nhất tạo bảng mới 'parking_logs' để dễ quản lý.
    cur.execute('''
        CREATE TABLE IF NOT EXISTS parking_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plate TEXT NOT NULL,
            time_in TEXT NOT NULL,
            time_out TEXT,
            status TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    logging.info("[DB] Đã khởi tạo/kiểm tra bảng parking_logs.")

def check_in(plate: str) -> tuple[bool, str]:
    """
    Cho xe vào bãi.
    Trả về (thành công?, thông báo lỗi nếu có).
    """
    conn = get_connection()
    cur = conn.cursor()
    
    # Kiểm tra xem xe này có đang ở trong bãi không
    cur.execute("SELECT id FROM parking_logs WHERE plate = ? AND status = 'IN'", (plate,))
    if cur.fetchone():
        conn.close()
        return False, "Xe đang ở trong bãi, chưa được cho ra!"

    # Lưu xe vào bãi
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        "INSERT INTO parking_logs (plate, time_in, status) VALUES (?, ?, 'IN')",
        (plate, now_str)
    )
    conn.commit()
    conn.close()
    return True, "Cho xe vào thành công!"

def check_out(plate: str) -> tuple[bool, str]:
    """
    Cho xe ra khỏi bãi.
    Trả về (thành công?, thông báo lỗi nếu có).
    """
    conn = get_connection()
    cur = conn.cursor()
    
    # Tìm record gần nhất của biển số này đang 'IN'
    cur.execute(
        "SELECT id FROM parking_logs WHERE plate = ? AND status = 'IN' ORDER BY id DESC LIMIT 1",
        (plate,)
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        return False, "Xe này chưa được giữ hoặc đã ra khỏi bãi!"

    log_id = row[0]
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Cập nhật thành 'OUT'
    cur.execute(
        "UPDATE parking_logs SET time_out = ?, status = 'OUT' WHERE id = ?",
        (now_str, log_id)
    )
    conn.commit()
    conn.close()
    return True, "Cho xe ra thành công!"

def get_recent_logs(limit: int = 20) -> list[dict]:
    """
    Lấy danh sách các xe vừa ra/vào gần đây.
    """
    conn = get_connection()
    # Return dict format
    conn.row_factory = sqlite3.Row 
    cur = conn.cursor()
    
    cur.execute(
        "SELECT * FROM parking_logs ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = cur.fetchall()
    conn.close()
    
    # Chuyển đổi thành list of dicts
    return [dict(row) for row in rows]
