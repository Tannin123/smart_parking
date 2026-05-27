"""
app.py  –  Flask application entry point
"""

from flask import Flask, render_template, redirect, url_for
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


# ── Page routes ──────────────────────────────────────────────────────────
@app.route('/')
def index():
    return redirect(url_for('login'))

# Hỗ trợ cả /login và /login.html
@app.route('/login')
@app.route('/login.html')
def login():
    return render_template('login.html')

# Hỗ trợ cả /Dashboard.html và /dashboard
@app.route('/Dashboard.html')
@app.route('/dashboard')
def dashboard():
    return render_template('Dashboard.html')

# Hỗ trợ cả /detect và /nhandien.html
@app.route('/detect')
@app.route('/nhandien.html')
def detect_page():
    return render_template('nhandien.html')

# Hỗ trợ cả /employee và /employee.html
@app.route('/employee')
@app.route('/employee.html')
def employee():
    return render_template('employee.html')

# Hỗ trợ cả /pricing.html và /pricing
@app.route('/pricing.html')
@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

# Hỗ trợ cả /report.html và /report
@app.route('/report.html')
@app.route('/report')
def report():
    return render_template('report.html')

# Hỗ trợ cả /support.html và /support
@app.route('/support.html')
@app.route('/support')
def support():
    return render_template('support.html')


# ── Run ──────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=config.DEBUG, host='0.0.0.0', port=5000)
