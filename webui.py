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

@app.route('/config', methods=['GET', 'POST'])
def config_editor():
    """Config editor page"""
    config_file = '/config/config.yml' if os.path.exists('/config/config.yml') else 'config.yml'
    
    if request.method == 'POST':
        # Save new configuration
        try:
            new_config = request.form.get('config')
            # Validate YAML format
            yaml_config = yaml.safe_load(new_config)
            
            with open(config_file, 'w') as f:
                f.write(new_config)
            
            # Restart service
            try:
                if os.path.exists('/etc/systemd/system/gesturesensor.service'):
                    subprocess.run(['sudo', 'systemctl', 'restart', 'gesturesensor.service'], check=True)
                    return jsonify({'success': True, 'message': 'Configuration saved and service restarted'})
                else:
                    # For docker environment or when running directly, exit to trigger container restart
                    os._exit(0)
            except Exception as e:
                return jsonify({'success': False, 'message': f'Configuration saved but failed to restart service: {str(e)}'})
                
        except Exception as e:
            return jsonify({'success': False, 'message': f'Failed to save configuration: {str(e)}'})
    
    # Read current config
    try:
        with open(config_file, 'r') as f:
            current_config = f.read()
        return render_template('config.html', config=current_config)
    except Exception as e:
        return render_template('config.html', config='# Error loading configuration\n# ' + str(e))

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

def load_images_from_storage():
    """Load image files from storage directory with metadata"""
    storage_path = "storage"
    if not os.path.exists(storage_path):
        return []
    
    image_files = glob.glob(f"{storage_path}/*.jpg") + glob.glob(f"{storage_path}/*.png")
    images = []
    
    for img_path in sorted(image_files, reverse=True):
        # Get relative path for displaying in UI
        rel_path = os.path.basename(img_path)
        
        # Try to load metadata if available
        metadata = None
        json_path = os.path.splitext(img_path)[0] + ".json"
        if os.path.exists(json_path):
            try:
                with open(json_path, 'r') as f:
                    metadata = json.load(f)
            except Exception as e:
                print(f"Error loading metadata for {rel_path}: {str(e)}")
        
        # Get file timestamp
        try:
            timestamp = os.path.getmtime(img_path)
        except:
            timestamp = 0
            
        images.append({
            "path": rel_path,
            "timestamp": timestamp,
            "metadata": metadata
        })
    
    # Sort by timestamp, newest first
    images.sort(key=lambda x: x["timestamp"], reverse=True)
    return images

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
