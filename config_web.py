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
    <style>
        body { font-family: Arial, sans-serif; background: #f0f2f5; margin: 0; padding: 0; }
        .container { max-width: 800px; margin: 40px auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        h1 { text-align: center; color: #333; }
        form { display: flex; flex-direction: column; }
        label { display: flex; justify-content: space-between; margin-bottom: 12px; color: #555; }
        input[type=text], input[type=url] { flex: 1; padding: 8px; border: 1px solid #ccc; border-radius: 4px; }
        fieldset { border: 1px solid #ddd; padding: 15px; margin-bottom: 20px; border-radius: 6px; }
        legend { font-weight: bold; color: #444; }
        .checkbox-group { display: flex; flex-wrap: wrap; gap: 10px; }
        .checkbox-group label { display: flex; align-items: center; justify-content: flex-start; }
        .checkbox-group input[type=checkbox] { margin-right: 6px; }
        button { width: 150px; padding: 10px; border: none; border-radius: 4px; background: #007bff; color: #fff; font-size: 16px; cursor: pointer; align-self: center; }
        button:hover { background: #0056b3; }
        .messages { margin-bottom: 20px; }
        .messages li { background: #d4edda; padding: 10px; border: 1px solid #c3e6cb; border-radius: 4px; color: #155724; margin-bottom: 8px; }
    </style>
</head>
<body>
    <div class="container">
      <h1>Spotify弹幕点歌机配置管理</h1>
      {% with messages = get_flashed_messages() %}
        {% if messages %}
          <ul class="messages">
            {% for message in messages %}
              <li>{{ message }}</li>
            {% endfor %}
          </ul>
        {% endif %}
      {% endwith %}
      <form method="post" action="/">
        <fieldset>
          <legend>Bilibili 配置</legend>
          <label>sessdata:
            <input type="text" name="sessdata" value="{{ config['bilibili']['credential']['sessdata'] }}">
          </label>
          <label>bili_jct:
            <input type="text" name="bili_jct" value="{{ config['bilibili']['credential']['bili_jct'] }}">
          </label>
          <label>房间号:
            <input type="text" name="room_id" value="{{ config['bilibili']['room_id'] }}">
          </label>
          <label>sessdata 和 bili_jct 可在浏览器的开发者工具中找到，具体请参考:</label>
          <label><a href="https://nemo2011.github.io/bilibili-api/#/get-credential" target="_blank">https://nemo2011.github.io/bilibili-api/#/get-credential</a> </label>
        </fieldset>
        <fieldset>
          <legend>点歌权限 (弹幕发送 点歌+歌名+歌手(可选) 即可点歌)</legend>
          {% set song_names = {'streamer':'主播','room_admin':'房管','guard':'大航海','medal_light':'粉丝团','medal_level':'灯牌等级'} %}
          <div class="checkbox-group">
            {% for key, val in config['bilibili']['song_request_permission'].items() %}
              <label>
                {% if val is boolean %}
                  <input type="checkbox" name="song_request_{{ key }}" {% if val %}checked{% endif %}> {{ song_names[key] if key in song_names else key }}
                {% else %}
                  {{ song_names[key] if key in song_names else key }}: <input type="text" name="song_request_{{ key }}" value="{{ val }}"> 
                {% endif %}
              </label>
            {% endfor %}
            <label>灯牌等级：即使粉丝图熄灭，到达粉丝团等级也能点歌。(默认点亮过灯牌即可点歌)</label>
          </div>
        </fieldset>
        <fieldset>
          <legend>切歌权限 (弹幕发送 下一首 即可切歌)</legend>
          {% set song_names = {'streamer':'主播','room_admin':'房管','guard':'大航海','medal_light':'粉丝团','medal_level':'灯牌等级'} %}
          <div class="checkbox-group">
            {% for key, val in config['bilibili']['next_request_permission'].items() %}
              <label>
                {% if val is boolean %}
                  <input type="checkbox" name="next_request_{{ key }}" {% if val %}checked{% endif %}> {{ song_names[key] if key in song_names else key }}
                {% else %}
                  {{ song_names[key] if key in song_names else key }}: <input type="text" name="next_request_{{ key }}" value="{{ val }}"> 
                {% endif %}
              </label>
            {% endfor %}
            <label>灯牌等级：即使粉丝图熄灭，到达粉丝团等级也能切歌。(默认大航海一下不能点歌)</label>
          </div>
        </fieldset>
        <fieldset>
          <legend>Spotify 配置</legend>
          <label>Spotify API Client ID:
            <input type="text" name="spotify_client_id" value="{{ config['spotify']['client_id'] }}">
          </label>
          <label>Spotify API Client secret:
            <input type="text" name="spotify_client_secret" value="{{ config['spotify']['client_secret'] }}">
          </label>
          <label>Redirect URIs:
            <input type="url" name="spotify_redirect_uri" value="{{ config['spotify']['redirect_uri'] }}">
          </label>
          <label>默认播放列表:
            <input type="url" name="default_playlist" value="{{ config['spotify']['default_playlist'] }}">
          </label>
          <label>Spotify API client_id 和 client_secret 需要前往Spotify开发者中心申请获取(一分钟):</label>
          <label><a href="https://developer.spotify.com/dashboard/applications" target="_blank">https://developer.spotify.com/dashboard/applications</a>
        </fieldset>
        <button type="submit">保存配置</button>
      </form>
    </div>
</body>
</html>
"""

default_config = {
    "bilibili": {
        "room_id": "",
        "credential": {
            "sessdata": "",
            "bili_jct": ""
        },
        "song_request_permission": {
            "streamer": True,
            "room_admin": True,
            "guard": True,
            "medal_light": True,
            "medal_level": "1"
        },
        "next_request_permission": {
            "streamer": True,
            "room_admin": True,
            "guard": True,
            "medal_light": False,
            "medal_level": "100"
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
        # Bilibili Cookie
        config['bilibili']['credential']['sessdata'] = request.form.get('sessdata', '')
        config['bilibili']['credential']['bili_jct'] = request.form.get('bili_jct', '')
        # Bilibili 基本
        config['bilibili']['room_id'] = request.form.get('room_id', '')
        config['bilibili']['streamer_name'] = request.form.get('streamer_name', '')
        # 点歌权限
        for key in config['bilibili']['song_request_permission']:
            form_key = f"song_request_{key}"
            if isinstance(config['bilibili']['song_request_permission'][key], bool):
                config['bilibili']['song_request_permission'][key] = form_key in request.form
            else:
                config['bilibili']['song_request_permission'][key] = request.form.get(form_key, '')
        # 切歌权限
        for key in config['bilibili']['next_request_permission']:
            form_key = f"next_request_{key}"
            if isinstance(config['bilibili']['next_request_permission'][key], bool):
                config['bilibili']['next_request_permission'][key] = form_key in request.form
            else:
                config['bilibili']['next_request_permission'][key] = request.form.get(form_key, '')
        # Spotify
        config['spotify']['client_id'] = request.form.get('spotify_client_id', '')
        config['spotify']['client_secret'] = request.form.get('spotify_client_secret', '')
        default_playlist_input = request.form.get('default_playlist', '').strip()
        config['spotify']['default_playlist'] = default_playlist_input if default_playlist_input else DEFAULT_PLAYLIST_URI

        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        flash("配置已成功保存！")
        return redirect(url_for('configure'))

    return render_template_string(CONFIG_HTML_TEMPLATE, config=config)

class ServerThread(threading.Thread):
    def __init__(self, app, host='127.0.0.1', port=5001):
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
        threading.Thread(target=lambda: webbrowser.open('http://localhost:5001')).start()
        print("[CONFIG] 🌐 请在浏览器中打开 http://localhost:5001 进行配置。")
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