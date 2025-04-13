import json
import os
import threading
import time
import webbrowser
from flask import Flask, request, render_template_string, redirect, url_for, flash
from werkzeug.serving import make_server

CONFIG_FILE = 'config.json'
app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

DEFAULT_SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
DEFAULT_SPOTIFY_SCOPE = "user-read-playback-state user-modify-playback-state"
DEFAULT_PLAYLIST_URI = "https://open.spotify.com/playlist/2sOt8rRBaecTxgc7LFidrm?si=80e4759b8eeb43b2"

CONFIG_HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>配置管理</title>
</head>
<body>
    <h1>配置管理</h1>
    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <ul>
          {% for message in messages %}
            <li style="color: green;">{{ message }}</li>
          {% endfor %}
        </ul>
      {% endif %}
    {% endwith %}
    <form method="post" action="/">
        <h2>Bilibili 配置</h2>
        <label>sessdata:
            <input type="text" name="sessdata" value="{{ config['bilibili']['credential']['sessdata'] }}" style="width: 600px;">
        </label>
        <br>
        <label>bili_jct:
            <input type="text" name="bili_jct" value="{{ config['bilibili']['credential']['bili_jct'] }}" style="width: 600px;">
        </label>
        <br>
        <label>房间号:
            <input type="text" name="room_id" value="{{ config['bilibili']['room_id'] }}">
        </label>
        <br>
        <label>主播名称:
            <input type="text" name="streamer_name" value="{{ config['bilibili']['streamer_name'] }}">
        </label>
        <br>
        <h2>Spotify 配置</h2>
        <label>client_id:
            <input type="text" name="spotify_client_id" value="{{ config['spotify']['client_id'] }}">
        </label>
        <br>
        <label>client_secret:
            <input type="text" name="spotify_client_secret" value="{{ config['spotify']['client_secret'] }}">
        </label>
        <br>
        <label>redirect_uri:
            <input type="text" name="spotify_redirect_uri" value="{{ config['spotify']['redirect_uri'] }}">
        </label>
        <br>
        <label>default_playlist:
            <input type="text" name="default_playlist" value="{{ config['spotify']['default_playlist'] }}">
        </label>
        <br><br>
        <button type="submit">保存配置</button>
    </form>
</body>
</html>
"""

default_config = {
    "bilibili": {
        "room_id": "",
        "streamer_name": "",
        "credential": {
            "sessdata": "",
            "bili_jct": ""
        }
    },
    "spotify": {
        "client_id": "",
        "client_secret": "",
        "redirect_uri": DEFAULT_SPOTIFY_REDIRECT_URI,
        "scope": DEFAULT_SPOTIFY_SCOPE,
        "default_playlist": DEFAULT_PLAYLIST_URI
    }
}

@app.route('/', methods=['GET', 'POST'])
def configure():
    config = default_config.copy()

    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)

    if request.method == 'POST':
        config['bilibili']['credential']['sessdata'] = request.form['sessdata']
        config['bilibili']['credential']['bili_jct'] = request.form['bili_jct']
        config['bilibili']['room_id'] = request.form['room_id']
        config['bilibili']['streamer_name'] = request.form['streamer_name']
        config['spotify']['client_id'] = request.form['spotify_client_id']
        config['spotify']['client_secret'] = request.form['spotify_client_secret']

        default_playlist_input = request.form['default_playlist'].strip()
        config['spotify']['default_playlist'] = (
            default_playlist_input if default_playlist_input else DEFAULT_PLAYLIST_URI
        )

        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)

        flash("配置已成功保存！")
        return redirect(url_for('configure'))

    return render_template_string(CONFIG_HTML_TEMPLATE, config=config)

class ServerThread(threading.Thread):
    def __init__(self, app, host='127.0.0.1', port=5000):
        threading.Thread.__init__(self)
        self.srv = make_server(host, port, app)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        print("[CONFIG] 🌐 Flask 配置网页启动中...")
        self.srv.serve_forever()

    def shutdown(self):
        print("[CONFIG] 🛑 Flask 配置网页已关闭。")
        self.srv.shutdown()

server_thread = None

def is_config_valid(config):
    try:
        bili = config["bilibili"]
        spotify = config["spotify"]
        return all([
            bili["credential"]["sessdata"],
            bili["credential"]["bili_jct"],
            bili["room_id"],
            bili["streamer_name"],
            spotify["client_id"],
            spotify["client_secret"]
        ])
    except KeyError:
        return False

def load_or_prompt_config():
    config_ready_event = threading.Event()

    def wait_for_valid_config_and_set_event():
        while True:
            if os.path.exists(CONFIG_FILE):
                try:
                    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        if is_config_valid(config):
                            print("[CONFIG] ✅ 检测到有效配置，继续初始化主程序...")
                            config_ready_event.set()
                            server_thread.shutdown()
                            return
                        else:
                            print("[CONFIG] ⚠️ 配置无效，等待中...")
                except Exception:
                    print("[CONFIG] ⚠️ 配置解析失败，等待中...")
            else:
                print("[CONFIG] 🔍 配置文件不存在，等待中...")
            time.sleep(2)

    need_config = True
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                if is_config_valid(config):
                    need_config = False
        except Exception:
            pass

    if need_config:
        print("[CONFIG] 启动配置网页...")
        threading.Thread(target=lambda: webbrowser.open('http://localhost:5000')).start()
        global server_thread
        server_thread = ServerThread(app)
        server_thread.start()

        checker_thread = threading.Thread(target=wait_for_valid_config_and_set_event)
        checker_thread.start()

        config_ready_event.wait()

    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)

    config['spotify']['redirect_uri'] = DEFAULT_SPOTIFY_REDIRECT_URI
    config['spotify']['scope'] = DEFAULT_SPOTIFY_SCOPE
    if not config['spotify'].get('default_playlist'):
        config['spotify']['default_playlist'] = DEFAULT_PLAYLIST_URI

    print("[CONFIG] 配置加载成功！")
    return config

if __name__ == '__main__':
    load_or_prompt_config()