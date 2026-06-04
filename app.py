"""
app.py  –  Flask application entry point
"""

from flask import Flask, render_template, redirect, url_for, session, request, jsonify
from functools import wraps
import config

from routers.vehicle import detect_bp
from routers.webcam import webcam_bp

import db

app = Flask(__name__, static_folder='static')
app.secret_key = config.SECRET_KEY

# Khởi tạo DB
db.init_db()

# ── Đăng ký Blueprints ───────────────────────────────────────────────────
app.register_blueprint(detect_bp)
app.register_blueprint(webcam_bp)


# ── Middleware kiểm tra đăng nhập ────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ── Page routes ──────────────────────────────────────────────────────────
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login')
@app.route('/login.html')
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/Dashboard.html')
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('Dashboard.html')

@app.route('/detect')
@app.route('/detect.html')
@login_required
def detect_page():
    return render_template('detect.html')

@app.route('/employee')
@app.route('/employee.html')
@login_required
def employee():
    return render_template('employee.html')

@app.route('/pricing.html')
@app.route('/pricing')
@login_required
def pricing():
    return render_template('pricing.html')

@app.route('/changepassword.html')
@app.route('/changepassword')
@login_required
def changepassword():
    return render_template('changepassword.html')

@app.route('/report.html')
@app.route('/report')
@login_required
def report():
    return render_template('report.html')

@app.route('/support.html')
@app.route('/support')
@login_required
def support():
    return render_template('support.html')


# ── API Routes (Auth) ────────────────────────────────────────────────────
@app.route('/api/login', methods=['POST'])
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

@app.route('/api/logout', methods=['GET', 'POST'])
def api_logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/change_password', methods=['POST'])
@login_required
def api_change_password():
    data = request.json
    old_pwd = data.get('old_password')
    new_pwd = data.get('new_password')
    success, msg = db.change_password(session['user_id'], old_pwd, new_pwd)
    return jsonify({'success': success, 'message': msg})


@app.route('/logout')
@login_required
def logout():
    session.clear()
    return redirect(url_for('login'))


# ── API Routes (Users) ───────────────────────────────────────────────────
@app.route('/api/users', methods=['GET'])
@login_required
def api_get_users():
    users = db.get_users()
    return jsonify({'success': True, 'data': users})

@app.route('/api/users', methods=['POST'])
@login_required
def api_add_user():
    success = db.add_user(request.json)
    return jsonify({'success': success})

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@login_required
def api_update_user(user_id):
    success = db.update_user(user_id, request.json)
    return jsonify({'success': success})

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
def api_delete_user(user_id):
    success = db.delete_user(user_id)
    return jsonify({'success': success})


# ── API Routes (Pricing) ─────────────────────────────────────────────────
@app.route('/api/pricing', methods=['GET'])
@login_required
def api_get_pricing():
    pricing = db.get_pricing()
    return jsonify({'success': True, 'data': pricing})

@app.route('/api/pricing', methods=['POST'])
@login_required
def api_add_pricing():
    success = db.add_pricing(request.json)
    return jsonify({'success': success})

@app.route('/api/pricing/<int:pricing_id>', methods=['PUT'])
@login_required
def api_update_pricing(pricing_id):
    success = db.update_pricing(pricing_id, request.json)
    return jsonify({'success': success})

@app.route('/api/pricing/<int:pricing_id>', methods=['DELETE'])
@login_required
def api_delete_pricing(pricing_id):
    success = db.delete_pricing(pricing_id)
    return jsonify({'success': success})


# ── API Routes (Report) ──────────────────────────────────────────────────
@app.route('/api/report', methods=['GET'])
@login_required
def api_get_report():
    from_date = request.args.get('from', '2020-01-01 00:00:00')
    to_date = request.args.get('to', '2099-12-31 23:59:59')
    
    # Optional: adjust 'T' to space for datetime compatibility if coming from datetime-local input
    from_date = from_date.replace('T', ' ')
    to_date = to_date.replace('T', ' ')
    
    data = db.get_report_data(from_date, to_date)
    return jsonify({'success': True, 'data': data})


# ── Run ──────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=config.DEBUG, host='0.0.0.0', port=5000)
