from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import json
import yaml
import subprocess
import glob
import sys
import threading
import time
import builtins
from datetime import datetime

app = Flask(__name__, template_folder='templates', static_folder='static')

# Định nghĩa biến lưu log gần đây nhất
log_buffer = []
log_buffer_lock = threading.Lock()
MAX_LOG_LINES = 1000

# Lưu print gốc
original_print = builtins.print

# Thêm filter datetime cho Jinja2
@app.template_filter('datetime')
def format_datetime(value):
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value).strftime('%Y-%m-%d %H:%M:%S')
    return value

# Hàm ghi log
def log_capture(message):
    global log_buffer
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_entry = f"{timestamp} - {message}"
    with log_buffer_lock:
        log_buffer.append(log_entry)
        if len(log_buffer) > MAX_LOG_LINES:
            log_buffer = log_buffer[-MAX_LOG_LINES:]
    original_print(log_entry)  # Tránh vòng lặp vô hạn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/logs')
def view_logs():
    return render_template('logs.html')

@app.route('/api/logs')
def get_logs():
    with log_buffer_lock:
        return jsonify(logs=log_buffer)

@app.route("/storage/<path:filename>")
def serve_storage(filename):
    return send_from_directory("storage", filename)

@app.route("/images")
def images():
    return render_template("images.html", images=load_images_from_storage())

def start_webui():
    """Start the web UI server"""
    log_capture("Web UI starting on port 1010")
    
    def print_override(*args, **kwargs):
        message = " ".join(str(arg) for arg in args)
        log_capture(message)
        original_print(*args, **kwargs)  # Vẫn in ra console
    
    builtins.print = print_override  # Ghi đè print
    
    app.run(host='0.0.0.0', port=1010, debug=False)

if __name__ == '__main__':
    start_webui()
