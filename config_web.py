# config_web.py
import time
import threading
import webbrowser
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from config import load_config, save_config

app = Flask(__name__)
app.secret_key = "secret_key_for_session"  # 请替换为更安全的密钥

@app.route('/', methods=['GET', 'POST'])
def config_page():
    config = load_config()
    if request.method == 'POST':
        # 更新 bilibili 配置
        config['bilibili']['credential']['sessdata'] = request.form.get('sessdata', '').strip()
        config['bilibili']['credential']['bili_jct'] = request.form.get('bili_jct', '').strip()
        config['bilibili']['room_id'] = request.form.get('room_id', '').strip()
        config['bilibili']['streamer_name'] = request.form.get('streamer_name', '').strip()
        # 更新 spotify 配置
        config['spotify']['client_id'] = request.form.get('spotify_client_id', '').strip()
        config['spotify']['client_secret'] = request.form.get('spotify_client_secret', '').strip()
        config['spotify']['redirect_uri'] = request.form.get('spotify_redirect_uri', '').strip()
        config['spotify']['default_playlist'] = request.form.get('default_playlist', '').strip()
        save_config(config)
        flash("配置已保存！")
        return redirect(url_for('config_page'))
    return render_template("config.html", config=config)

@app.route('/api/status')
def status():
    data = {
        "current_song": "示例歌曲",
        "queue": []
    }
    return jsonify(data)

def run_config_server():
    """封装 Flask 服务的启动函数，供外部调用"""
    # 注意：关闭 debug 和自动重载功能，确保在线程中运行稳定
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)

def open_config_browser():
    """延时 1 秒后自动打开默认浏览器访问配置页面"""
    time.sleep(1)
    webbrowser.open("http://127.0.0.1:5000")
