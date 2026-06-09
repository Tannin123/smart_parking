from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template
from functools import wraps
import db

# Khởi tạo Blueprint cho Auth
auth_bp = Blueprint('auth', __name__)

# ─── MIDDLEWARE 1: KIỂM TRA ĐÃ ĐĂNG NHẬP CHƯA ────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # Lưu ý: Vì dùng Blueprint, tên route giờ là auth.login_page
            return redirect(url_for('auth.login_page'))
        return f(*args, **kwargs)
    return decorated_function

# ─── MIDDLEWARE 2: KIỂM TRA QUYỀN ADMIN (MỚI) ────────────────────────────
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login_page'))
        
        if session.get('role') != 'admin':
            return jsonify({
                'success': False, 
                'message': 'Lỗi phân quyền: Chỉ Admin mới được thực hiện hành động này!'
            }), 403
            
        return f(*args, **kwargs)
    return decorated_function

# ─── PAGE ROUTES (GIAO DIỆN) ─────────────────────────────────────────────
@auth_bp.route('/login')
@auth_bp.route('/login.html')
def login_page():
    if 'user_id' in session:
        return redirect(url_for('dashboard')) # dashboard nằm bên app.py
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout_page():
    session.clear()
    return redirect(url_for('auth.login_page'))

# ─── API ROUTES (XỬ LÝ DỮ LIỆU) ──────────────────────────────────────────
@auth_bp.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    success, user = db.verify_login(username, password)
    if success:
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        return jsonify({'success': True, 'message': 'Đăng nhập thành công'})
    return jsonify({'success': False, 'message': 'Tài khoản hoặc mật khẩu không đúng'})

@auth_bp.route('/api/logout', methods=['GET', 'POST'])
def api_logout():
    session.clear()
    return jsonify({'success': True})

@auth_bp.route('/api/change_password', methods=['POST'])
@login_required
def api_change_password():
    data = request.json
    old_pwd = data.get('old_password')
    new_pwd = data.get('new_password')
    success, msg = db.change_password(session['user_id'], old_pwd, new_pwd)
    return jsonify({'success': success, 'message': msg})

@auth_bp.route('/api/register', methods=['POST'])
def api_register():
    """
    API Đăng ký tài khoản (Dành cho trang Đăng ký nếu bạn có làm giao diện riêng).
    Lưu ý: Hệ thống này Admin có thể tạo user từ trang employee.html.
    """
    data = request.json
    # Hàm db.add_user của bạn tự động lấy 'username' hoặc 'empId', password mặc định là 123456 nếu rỗng
    success = db.add_user(data)
    if success:
        return jsonify({'success': True, 'message': 'Đăng ký tài khoản thành công'})
    return jsonify({'success': False, 'message': 'Tài khoản đã tồn tại hoặc có lỗi xảy ra'})