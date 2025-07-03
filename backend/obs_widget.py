from flask import Flask, render_template, request, jsonify, Response, send_from_directory, redirect
from flask_socketio import SocketIO, emit
import time
import threading
import logging
from log_timer import timestamp
import json
import asyncio
import os

logging.getLogger('werkzeug').disabled = True  # 禁用 Flask 日志

spotify_ctrl = None  # SpotifyController 实例
def set_spotify_controller(controller):
    global spotify_ctrl
    spotify_ctrl = controller

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
app.logger.setLevel(logging.ERROR)
# obs_widget.py
socketio = SocketIO(
    app,
    logger=False,
    engineio_logger=False,
    cors_allowed_origins="*"
)

# 初始待播清单数据
playlist_data = []  # 播放列表初始设为空列表
message_data = {
    "message": "当前无点歌",
    "result": "发送：点歌 + 歌名 点歌",
    "albumCover": "./images/Spotify.png"
}
new_playlist = False
new_message = False

last_playlist_data = playlist_data.copy()
last_message_data = message_data.copy()

room_id = None

@app.route('/queue_widget')
def queue_no_slash():
    return redirect('/queue_widget/')

@app.route('/queue_widget/')
def serve_queue_index():
    return send_from_directory(
        os.path.join('static', 'queue_widget'),
        'index.html'
    )

@app.route('/queue_widget/<path:filename>')
def serve_queue_static(filename):
    return send_from_directory(
        os.path.join('static', 'queue_widget'),
        filename
    )

@app.route('/nowplaying_widget')
def nowplaying_no_slash():
    return redirect('/nowplaying_widget/')

@app.route('/nowplaying_widget/')
def serve_nowplaying_index():
    return send_from_directory(
        os.path.join('static', 'nowplaying_widget'),
        'index.html'
    )

@app.route('/nowplaying_widget/<path:filename>')
def serve_nowplaying_static(filename):
    return send_from_directory(
        os.path.join('static', 'nowplaying_widget'),
        filename
    )

@app.route('/playlist')
def playlist():
    global playlist_data, message_data
    data = {
        "playlist": playlist_data,
        "message": message_data
    }
    return Response(
        json.dumps(data, ensure_ascii=False),  # 中文不转义
        status=200,
        content_type='application/json; charset=utf-8'
    )

@app.route('/nowplayingjson')
def now_playing():
    if spotify_ctrl is None:
        return jsonify({"error": "Spotify controller not ready"}), 500

    info = spotify_ctrl._get_current_playback()
    return Response(
        json.dumps(info or {}, ensure_ascii=False),
        status=200,
        content_type="application/json; charset=utf-8"
    )

@app.route('/update_data', methods=['POST'])
def update_data():
    """
    接收来自 main.py 的数据更新请求
    """
    global playlist_data, message_data
    data = request.json
    if 'playlist' in data:
        playlist_data = data['playlist']
        print(f'收到新的待播清单数据: {playlist_data}')
    if 'message' in data:
        message_data = data['message']
        print(f'收到新的消息数据: {message_data}')
    return jsonify({'status': 'success'}), 200

@socketio.on('connect')
def handle_connect():
    # 客户端连接时，发送最新的播放列表和消息数据
    #print(f'[{room_id}]{timestamp()}[SKIO] 客户端已连接')
    emit('playlist_update', playlist_data)
    emit('message_update', message_data)
    #print(f'[{room_id}]{timestamp()}[SKIO] 已发送最新待播清单和消息数据')

def update_playlist():
    global playlist_data, message_data, new_playlist, new_message, last_playlist_data, last_message_data
    """后台线程函数，用于定时检查数据更新并发送给客户端
    """

    while True:
        # 检查消息数据更新
        if message_data and new_message:
            socketio.emit('message_update', message_data)
            print(f'[{room_id}]{timestamp()}[SKIO] 已发送前端消息更新')
            #print(f'[{room_id}]{timestamp()}[SKIO] 已发送消息更新 {message_data}')
            last_message_data = message_data.copy()
            new_message = False
        
        # 检查播放列表更新
        if playlist_data and new_playlist:
            socketio.emit('playlist_update', playlist_data)
            print(f'[{room_id}]{timestamp()}[SKIO] 已发送待播清单更新')
            #print(f'[{room_id}]{timestamp()}[SKIO] 已发送待播清单更新 {playlist_data}')
            last_playlist_data = playlist_data.copy()
            new_playlist = False
        
        socketio.sleep(0.5)  # 每秒检查一次

def emit_nowplaying_loop():
    """后台线程函数，用于定时发送当前播放信息
    """
    interval = 1
    while True:
        start = time.time()

        info = spotify_ctrl._get_current_playback()
        socketio.emit('nowplaying_update', info)

        elapsed = time.time() - start
        sleep_time = max(0, interval - elapsed)
        socketio.sleep(sleep_time)
        

    # while True:
    #     if spotify_ctrl is not None:
    #         info = spotify_ctrl._get_current_playback()
    #         if info:
    #             socketio.emit('nowplaying_update', info)
    #             #print(f'[{room_id}]{timestamp()}[SKIO] 已发送当前播放信息: {info}')
    #     socketio.sleep(0.25)  # 每秒检查一次

def request_song(song_name):
    # 模拟请求歌曲的处理逻辑
    print(f'请求歌曲: {song_name}')
    # 这里可以添加实际的请求逻辑，例如调用 OBS 的 API 等

def start_server():
    # 启动后台线程
    socketio.start_background_task(target=update_playlist)
    socketio.start_background_task(target=emit_nowplaying_loop)
    # 启动服务器（可通过 http://localhost:5000 访问）
    socketio.run(app, debug=False, host='0.0.0.0', port=5001, use_reloader=False)
    
    
