from flask import Flask, render_template, request, jsonify, Response, send_from_directory, redirect
from flask_socketio import SocketIO, emit
import time
import threading
import logging
from utils.log_timer import timestamp
import json
import asyncio
import os
import logging

# Handlers & controllers
from config.config import load_config, save_config
from handler.status_handler import start as start_machine, stop as stop_machine, is_running
from handler.queue_manager import song_queue_streamer, song_queue_guard, song_queue

logging.getLogger('werkzeug').setLevel(logging.ERROR)

spotify_controller = None
song_queue = None
default_mesage = {
            "message": "点歌队列空",
            "result": "发送：点歌 + 歌名 即可点歌",
            "albumCover": './images/Spotify.png'
        }

def set_api_spotify_controller(controller):
    global spotify_controller
    spotify_controller = controller

BASE = os.path.dirname(os.path.dirname(__file__))  # apis/ 上两层 -> backend/
STATIC_DIR = os.path.join(BASE, 'static')

app = Flask(
    __name__,
    static_folder=STATIC_DIR,    # 指向 backend/static
    static_url_path=''           # 静态资源不再使用 /static 前缀
)

app.config['SECRET_KEY'] = 'secret!'
app.config['JSON_AS_ASCII'] = False
app.logger.setLevel(logging.ERROR)

socketio = SocketIO(
    app,
    logger=False,
    engineio_logger=False,
    cors_allowed_origins="*",
    log_output=False  # 禁止命令行输出 GET/POST 等日志
)

# --- Configuration API ---
@app.route('/api/config', methods=['GET', 'POST'])
def config_api():
    if request.method == 'GET':
        config = load_config()
        return jsonify(config)
    else:
        save_config(request.json)
        return jsonify({'status': 'updated'})

# --- Status API ---
@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({'running': is_running()})

@app.route('/api/status/start', methods=['POST'])
def api_start():
    start_machine()
    return jsonify({'status': 'started'})

@app.route('/api/status/stop', methods=['POST'])
def api_stop():
    stop_machine()
    return jsonify({'status': 'stopped'})

# --- Queue API ---
@app.route('/api/queue/<queue_type>', methods=['GET'])
def get_queue(queue_type):
    queues = {
        'streamer': asyncio.run(song_queue_streamer.list_songs()),
        'guard':    asyncio.run(song_queue_guard.list_songs()),
        'normal':   asyncio.run(song_queue.list_songs()),
    }
    return jsonify({'queues': queues})

@app.route('/api/queue/<queue_type>/reorder', methods=['POST'])
def reorder_queue(queue_type):
    new_order = request.json.get('queue')
    if queue_type == 'streamer':
        asyncio.run(song_queue_streamer._queue.put(None))  # placeholder
    # TODO: implement update in SongQueue
    return jsonify({'status': 'ok'})

@app.route('/api/queue/<queue_type>/delete/<int:index>', methods=['DELETE'])
def delete_queue_item(queue_type, index):
    qmap = {
        'streamer': song_queue_streamer,
        'guard':    song_queue_guard,
        'normal':   song_queue,
    }
    queue = qmap.get(queue_type)
    if not queue:
        return jsonify({'error': 'invalid queue type'}), 400
    removed = asyncio.run(queue.remove_at(index))  # assume remove_at method
    return jsonify({'removed': bool(removed)})

@app.route('/api/spotify/search', methods=['GET'])
def spotify_search():
    q = request.args.get('q', '').strip()
    if not q:
        return jsonify({'error': 'empty query'}), 400
    track = asyncio.run(spotify_controller.search_song(q))
    if not track:
        return jsonify({'error': 'not found'}), 404
    return jsonify(track)

@app.route('/nowplayingjson')
def now_playing():
    if spotify_controller is None:
        return jsonify({"error": "Spotify controller not ready"}), 500

    info = spotify_controller._get_current_playback()
    return Response(
        json.dumps(info or {}, ensure_ascii=False),
        status=200,
        content_type="application/json; charset=utf-8"
    )

@app.route('/nowplaying_widget')
def np_no_slash():
    return redirect('/nowplaying_widget/')  # 注意：重定向到带斜杠的路由

# 2) 让 /nowplaying_widget/ 能直接返回 index.html
@app.route('/nowplaying_widget/')
def np_index():
    return app.send_static_file('nowplaying_widget/index.html')

@app.route('/queue_widget')
def qw_no_slash():
    return redirect('/queue_widget/')  # 注意：重定向到带斜杠的路由

# 2) 让 /nowplaying_widget/ 能直接返回 index.html
@app.route('/queue_widget/')
def qw_index():
    return app.send_static_file('queue_widget/index.html')


@socketio.on('connect')
def handle_connect():
    global song_queue
    if song_queue:
        socketio.emit('playlist_update', song_queue)
    else:
        # 如果没有队列数据，发送默认消息
        socketio.emit('message_update', default_mesage)

def emit_nowplaying_loop():
    """后台线程函数，用于定时发送当前播放信息
    """
    interval = 1
    while True:
        start = time.time()

        info = spotify_controller._get_current_playback()
        socketio.emit('nowplaying_update', info)

        elapsed = time.time() - start
        sleep_time = max(0, interval - elapsed)
        socketio.sleep(sleep_time)

def emit_message(data):
    socketio.emit('message_update', data)

def emit_queue(data):
    global song_queue
    socketio.emit('playlist_update', data)
    song_queue = data  # 更新全局变量，供其他地方使用

def clear_queue():
    """清空当前队列"""
    global song_queue
    song_queue = []
    return True

def start_api_server():
    """启动 API 服务器"""
    socketio.start_background_task(emit_nowplaying_loop)
    socketio.run(app, debug=False, host='0.0.0.0', port=5001, use_reloader=False)

# --- Run Server ---
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001, debug=False, use_reloader=False)
