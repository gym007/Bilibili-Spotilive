import os
import sys
import subprocess
import logging
from flask import Flask, jsonify, request

# Suppress Flask/werkzeug startup and access logs
logging.getLogger('werkzeug').setLevel(logging.ERROR)
logging.getLogger('werkzeug').disabled = True

# Hide server banner (Flask 2.2+)
try:
    from flask.cli import show_server_banner
    show_server_banner = lambda *args, **kwargs: None
except ImportError:
    pass

app = Flask(__name__)
app.logger.disabled = True

# main.py 脚本路径
MAIN_SCRIPT = os.path.join(os.path.dirname(__file__), 'main.py')
# 全局进程句柄
player_process = None

@app.route('/api/status/start', methods=['POST'])
def start():
    """启动 main.py 作为子进程"""
    global player_process
    if player_process and player_process.poll() is None:
        return jsonify(status='already running'), 200
    try:
        print(f"开始启动点歌机")
        player_process = subprocess.Popen([sys.executable, MAIN_SCRIPT])
        return jsonify(status='started'), 200
    except Exception as e:
        return jsonify(status='error', message=str(e)), 500

@app.route('/api/status/stop', methods=['POST'])
def stop():
    """停止 main.py 子进程"""
    global player_process
    if not player_process or player_process.poll() is not None:
        return jsonify(status='not running'), 200
    player_process.terminate()
    try:
        player_process.wait(timeout=5)
        print(f"点歌机已停止")
    except subprocess.TimeoutExpired:
        player_process.kill()
    return jsonify(status='stopped'), 200

@app.route('/api/status', methods=['GET'])
def status():
    """查询 main.py 子进程运行状态"""
    running = player_process is not None and player_process.poll() is None
    return jsonify(running=running), 200

if __name__ == '__main__':
    api_port = int(os.getenv('API_PORT', 5002))
    # 禁止调试模式、禁用自动重载，以避免额外日志
    app.run(host='0.0.0.0', port=api_port, debug=False, use_reloader=False)
