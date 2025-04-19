from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import time
import threading
import logging
from log_timer import timestamp

logging.getLogger('werkzeug').disabled = True  # 禁用 Flask 日志

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
app.logger.setLevel(logging.ERROR)
# obs_widget.py
socketio = SocketIO(app, logger=False, engineio_logger=False)


# 初始待播清单数据
playlist_data = []  # 播放列表初始设为空列表
message_data = {
    "message": "当前无点歌",
    "result": "发送：点歌 + 歌名 点歌",
    "albumCover": "/static/images/Spotify.png"
}
new_playlist = False
new_message = False

last_playlist_data = playlist_data.copy()
last_message_data = message_data.copy()

room_id = None

@app.route('/')
def widget():
    # 渲染模板（widget.html 位于 templates 目录下）
    return render_template('widget.html')

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
    #print('客户端已连接')
    # 连接时直接发送当前列表数据
    emit('playlist_update', last_playlist_data)
    emit('message_update', last_message_data)


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

def request_song(song_name):
    # 模拟请求歌曲的处理逻辑
    print(f'请求歌曲: {song_name}')
    # 这里可以添加实际的请求逻辑，例如调用 OBS 的 API 等

def start_server():
    # 启动后台线程
    socketio.start_background_task(target=update_playlist)
    # 启动服务器（可通过 http://localhost:5000 访问）
    socketio.run(app, debug=False, host='0.0.0.0', port=5000, use_reloader=False)
    
    
