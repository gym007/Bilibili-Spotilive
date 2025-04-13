#当前版本v2.0.0
#版本更新日志：
# 1. 加入obs小组件，通过obs_widget.py输出消息到前端html页面，实时展示点歌机动态
# 2. 优化点歌队列逻辑
# 3. 优化点歌请求逻辑
# 4. 优化下一首请求逻辑
# pyinstaller --add-data "widget.html;./templates" --add-data "index.css;./static" --add-data "Rainbow.css;./static" --add-data "socket.io.min.js;./static" --add-data "vibrant_default.js;./static" --add-data "vibrant.js;./static" --add-data "widget.js;./static" --add-data "Spotify.png;./static/images" main.py

import asyncio
import time
from bilibili_api import Credential
from bilibili_api.clients import AioHTTPClient
from bilibili_client import BilibiliClient
from spotify_controller import SpotifyController
from song_queue import SongQueue
from config import load_config
from log_timer import timestamp
from bilibili_api.utils.danmaku import Danmaku
from config_web import load_or_prompt_config
import obs_widget
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit


import json
import os
import threading
import time
import webbrowser
from flask import Flask, request, render_template, redirect, url_for, flash
from werkzeug.serving import make_server

# 配置文件名称，确保这个文件与 main.py 在同一目录中
CONFIG_FILE = 'config.json'
MAX_RETRIES = 3

def load_app_config():
    config = load_config()
    # 可在这里对配置数据进行简单判断，例如
    if not config.get("bilibili", {}).get("room_id"):
        print(f"[WARNING]{timestamp()} Bilibili 配置不完整，请先配置。")
    if not config.get("spotify", {}).get("client_id"):
        print(f"[WARNING]{timestamp()} Spotify 配置不完整，请先配置。")
    return config

def start_obs_widget():
    t = threading.Thread(target=obs_widget.start_server, daemon=True)
    t.start()

spotify_ctrl = None

# 弹幕客户端实例，用于监听弹幕消息
# 点歌队列实例，用于存储普通用户点歌请求的歌曲
client = None

song_queue = SongQueue()
# 点歌列队实例，用于储存大航海用户请求的歌曲
song_queue_guard = SongQueue()

# 用于标识当前播放是否为用户点歌（True: 点歌歌曲；False: 默认歌单歌曲）
current_is_point_requested = False
# 用于标识当前播放是否为大航海用户点歌（True: 点歌歌曲；False: 默认歌单歌曲）
current_is_point_requested_guard = False

async def song_request_handler(song_name, user_guard_level, room_id, song_request_permission):
    """
    点歌处理器：
      1. 搜索歌曲；
      2. 如果当前没有播放歌曲，立即播放点歌歌曲；
      3. 如果正在播放歌曲，根据当前播放状态决定是否立即播放或加入队列。
    """
    global current_is_point_requested, current_is_point_requested_guard
    if not song_request_permission:
        print(f"[{room_id}]{timestamp()}[提示] 点歌权限不足，无法点歌。")
        await update_obs_widget_queue(room_id=room_id, result="点亮粉丝图灯牌即可点歌", message="点歌失败，权限不足", track=None, push_message=True, push_playlist=False)
        await asyncio.sleep(5)
        songs_guard = await song_queue_guard.list_songs()
        songs = await song_queue.list_songs()
        queue = songs + songs_guard
        if not queue:
            if not current_is_point_requested:
                await update_obs_widget_queue(room_id=room_id, result="发送：点歌 + 歌名 点歌", message="当前无点歌", track=None, push_message=True, push_playlist=False)
            else:
                await update_obs_widget_queue(room_id=room_id, result="发送：点歌 + 歌名 点歌", message="当前正在播放点歌", track=None, push_message=True, push_playlist=False)
        else:
            track = queue[0]
            await update_obs_widget_queue(room_id=room_id, result="展示列队", message="展示列队", track=track, push_message=False, push_playlist=True)
        return

    track = await spotify_ctrl.search_song(song_name)
    if not track:
        print(f"[{room_id}]{timestamp()}[提示] 未找到歌曲：{song_name}")
        await update_obs_widget_queue(room_id=room_id, result="未找到符合条件的歌曲", message=f"点歌失败 {song_name}", track=None, push_message=True, push_playlist=False)
        await asyncio.sleep(5)
        songs_guard = await song_queue_guard.list_songs()
        songs = await song_queue.list_songs()
        queue = songs + songs_guard
        if not queue:
            if not current_is_point_requested:
                await update_obs_widget_queue(room_id=room_id, result="发送：点歌 + 歌名 点歌", message="当前无点歌", track=None, push_message=True, push_playlist=False)
            else:
                await update_obs_widget_queue(room_id=room_id, result="发送：点歌 + 歌名 点歌", message="当前正在播放点歌", track=None, push_message=True, push_playlist=False)
        else:
            track = queue[0]
            await update_obs_widget_queue(room_id=room_id, result="展示列队", message="展示列队", track=track, push_message=False, push_playlist=True)
        return

    current = await asyncio.to_thread(spotify_ctrl.sp.current_playback)
    is_playing = current and current.get('is_playing')

    if not is_playing or not current_is_point_requested:
        # 当前未播放点歌歌曲，理解播放点歌
        print(f"[{room_id}]{timestamp()}[点歌] 当前无播放，立即播放点歌。")
        current_is_point_requested = True
        if user_guard_level != 0:
            current_is_point_requested_guard = True
            await update_obs_widget_queue(room_id=room_id, result="当前无点歌，立即播放", message=f"大航海点歌 {track['name']} - {track['artists'][0]['name']}", track=track, push_message=True, push_playlist=False)
        else:
            await update_obs_widget_queue(room_id=room_id, result="当前无点歌，立即播放", message=f"普通点歌 {track['name']} - {track['artists'][0]['name']}", track=track, push_message=True, push_playlist=False)
        await spotify_ctrl.play_song(track)
        await asyncio.sleep(5)
        await update_obs_widget_queue(room_id=room_id, result="发送：点歌 + 歌名 点歌", message="当前正在播放点歌", track=None, push_message=True, push_playlist=False)

    elif current_is_point_requested or current_is_point_requested_guard:
        # 当前播放的是点歌歌曲，将新请求加入队列
        queue = song_queue_guard if user_guard_level != 0 else song_queue
        queue_type = "大航海" if user_guard_level != 0 else "普通"
        if user_guard_level != 0:
            current_is_point_requested_guard = True
        current_is_point_requested = True
        print(f"[{room_id}]{timestamp()}[列队] 加入{queue_type}待播队列。")
        await queue.add_song(track)
        await update_obs_widget_queue(room_id=room_id, result=f"{queue_type}点歌成功，加入队列", message=f"{queue_type}点歌 {track['name']} - {track['artists'][0]['name']}", track=track, push_message=True, push_playlist=False)
        await asyncio.sleep(5)
        await update_obs_widget_queue(room_id=room_id, result="展示列队", message="展示列队", track=track, push_message=False, push_playlist=True)
    # 打印队列状态
    await asyncio.sleep(1)
    await print_queue_status(room_id)

async def next_request_handler(username, room_id, next_request_permission):
    """
    处理“下一首”请求：
      如果待播队列有歌曲，则播放下一首；否则恢复默认歌单播放，并标记当前为默认模式。
    """
    global current_is_point_requested, current_is_point_requested_guard
    if not next_request_permission:
        print(f"[{room_id}]{timestamp()}[提示] 下一首权限不足，无法跳过。")
        await update_obs_widget_queue(room_id=room_id, result="加入大航海即可切歌", message="下一首失败，权限不足", track=None, push_message=True, push_playlist=False)
        await asyncio.sleep(5)
        songs_guard = await song_queue_guard.list_songs()
        songs = await song_queue.list_songs()
        queue = songs + songs_guard
        if not queue:
            if not current_is_point_requested:
                await update_obs_widget_queue(room_id=room_id, result="发送：点歌 + 歌名 点歌", message="当前无点歌", track=None, push_message=True, push_playlist=False)
            else:
                await update_obs_widget_queue(room_id=room_id, result="发送：点歌 + 歌名 点歌", message="当前正在播放点歌", track=None, push_message=True, push_playlist=False)
        else:
            track = queue[0]
            await update_obs_widget_queue(room_id=room_id, result="展示列队", message="展示列队", track=track, push_message=False, push_playlist=True)
        return

    if current_is_point_requested and not current_is_point_requested_guard:
        next_track = await song_queue.get_next_song()
        if next_track:
            song_info = f"{next_track['name']} - {next_track['artists'][0]['name']}"
            print(f"[{room_id}]{timestamp()}[队列] 播放普通队列中的下一首：{song_info}")
            await update_obs_widget_queue(room_id=room_id, result="播放下一首", message=f"播放下一首点歌 {song_info}", track=next_track, push_message=True, push_playlist=False)
            await asyncio.sleep(5)
            await spotify_ctrl.play_song(next_track)
            if not song_queue.is_empty():
                song_list = await song_queue.list_songs()
                track = song_list[0]
                await update_obs_widget_queue(room_id=room_id, result="展示列队", message="展示列队", track=track, push_message=False, push_playlist=True)
            elif song_queue.is_empty():
                await update_obs_widget_queue(room_id=room_id, result="发送：点歌 + 歌名 点歌", message="当前正在播放点歌", track=None, push_message=True, push_playlist=False)
        else:
            print(f"[{room_id}]{timestamp()}[提示] 普通队列已空，恢复默认歌单。")
            await update_obs_widget_queue(room_id=room_id, result="播放默认歌单", message="下一首无点歌", track=None, push_message=True, push_playlist=False)
            await spotify_ctrl.restore_default_playlist()
            await asyncio.sleep(5)
            await update_obs_widget_queue(room_id=room_id, result="发送：点歌 + 歌名 点歌", message="当前无点歌", track=None, push_message=True, push_playlist=False)
            current_is_point_requested = False
    elif current_is_point_requested_guard:
        print(f"[{room_id}]{timestamp()}[队列] 当前播放大航海点歌，无法跳过。")
        if not song_queue_guard.is_empty():
            queue_list = await song_queue_guard.list_songs()
            track = queue_list[0]
            await update_obs_widget_queue(room_id=room_id, result="无法跳过", message=f"当前正在播放大航海点歌", track=track, push_message=True, push_playlist=False)
            await asyncio.sleep(5)
            await update_obs_widget_queue(room_id=room_id, result="无法跳过", message=f"当前正在播放大航海点歌", track=track, push_message=False, push_playlist=True)
        elif not song_queue.is_empty():
            song_list = await song_queue.list_songs()
            track = song_list[0]
            await update_obs_widget_queue(room_id=room_id, result="无法跳过", message=f"当前正在播放大航海点歌", track=track, push_message=True, push_playlist=False)
            await asyncio.sleep(5)
            await update_obs_widget_queue(room_id=room_id, result="无法跳过", message=f"当前正在播放大航海点歌", track=track, push_message=False, push_playlist=True)
        else:
            await update_obs_widget_queue(room_id=room_id, result="无法跳过", message="当前正在播放大航海点歌", track=None, push_message=True, push_playlist=False)
            asyncio.sleep(5)
            await update_obs_widget_queue(room_id=room_id, result="发送：点歌 + 歌名 点歌", message="当前无点歌", track=None, push_message=True, push_playlist=False)
    else:
        print(f"[{room_id}]{timestamp()}[提示] 所有队列已空，恢复默认歌单。")
        await update_obs_widget_queue(room_id=room_id, result="播放默认歌单", message="下一首无点歌", track=None, push_message=True, push_playlist=False)
        await spotify_ctrl.restore_default_playlist()
        current_is_point_requested = False
        await asyncio.sleep(5)
        await update_obs_widget_queue(room_id=room_id, result="发送：点歌 + 歌名 点歌", message="当前无点歌", track=None, push_message=True, push_playlist=False)

    # 打印队列状态
    await asyncio.sleep(1)
    await print_queue_status(room_id)

async def update_obs_widget_queue(room_id, result, message, track, push_message, push_playlist):
    """
    更新 OBS widget 的队列数据
    优先从大航海队列（song_queue_guard）中选取，
    然后从普通队列（song_queue）中补充。
    """
    # 获取大航海队列和普通队列的所有待播歌曲
    songs_guard = await song_queue_guard.list_songs()
    songs = await song_queue.list_songs()

    # 合并队列并格式化为 OBS widget 所需的数据
    obs_widget.playlist_data = [
        {
            "name": f"{song.get('name', '未知歌曲')} - {song.get('artists', [{'name': '未知'}])[0].get('name', '未知')}",
            "albumCover": song.get('album', {}).get('images', [{}])[0].get('url', '')
        }
        for song in songs_guard + songs
    ]

    # 更新当前播放信息
    obs_widget.message_data = {
        "message": message,
        "result": result,
        "albumCover": track.get('album', {}).get('images', [{}])[0].get('url', '') if track else '/static/images/Spotify.png',
    }

    obs_widget.new_message = push_message
    obs_widget.new_playlist = push_playlist
    obs_widget.room_id = room_id

    # 调试输出
    #print(f"[{room_id}]{timestamp()}[OBS Widget] Playlist: {obs_widget.playlist_data}")
    #print(f"[{room_id}]{timestamp()}[OBS Widget] Message: {obs_widget.message_data}")

async def player_loop(room_id):
    """
    后台任务：
      持续检测当前点播播放状态，
      如果当前没有点播播放且待播队列为空，则恢复默认歌单播放，并将播放标识设置为默认模式（False）。
    """
    global current_is_point_requested, current_is_point_requested_guard

    while True:
        try:
            current = await asyncio.to_thread(spotify_ctrl.sp.current_playback)
            is_playing = current and current.get('is_playing')

            if not is_playing and current_is_point_requested:
                if not song_queue_guard.is_empty():
                    next_track = await song_queue_guard.get_next_song()
                    if next_track:
                        await update_obs_widget_queue(room_id, result="播放下一首", message=f"播放下一首点歌 {next_track['name']} - {next_track['artists'][0]['name']}", track=next_track, push_message=True, push_playlist=False)
                        await asyncio.sleep(5)
                        await spotify_ctrl.play_song(next_track)
                        if not song_queue_guard.is_empty():
                            queue_list = await song_queue_guard.list_songs()
                            track = queue_list[0]
                            await update_obs_widget_queue(room_id, result="展示列队", message="展示列队", track=track, push_message=False, push_playlist=True)
                        elif song_queue_guard.is_empty():
                            if not song_queue.is_empty():
                                queue_list = await song_queue.list_songs()
                                track = queue_list[0]
                                await update_obs_widget_queue(room_id, result="展示列队", message="展示列队", track=track, push_message=False, push_playlist=True)
                            elif song_queue.is_empty():
                                await update_obs_widget_queue(room_id, result="发送：点歌 + 歌名 点歌", message="当前正在播放点歌", track=None, push_message=True, push_playlist=False)
                elif not song_queue.is_empty():
                    current_is_point_requested_guard = False
                    next_track = await song_queue.get_next_song()
                    if next_track:
                        await update_obs_widget_queue(room_id, result="播放下一首", message=f"播放下一首点歌 {next_track['name']} - {next_track['artists'][0]['name']}", track=next_track, push_message=True, push_playlist=False)
                        await asyncio.sleep(5)
                        await spotify_ctrl.play_song(next_track)
                        if not song_queue.is_empty():
                            queue_list = await song_queue.list_songs()
                            track = queue_list[0]
                            await update_obs_widget_queue(room_id, result="展示列队", message="展示列队", track=track, push_message=False, push_playlist=True)
                        elif song_queue.is_empty():
                            await update_obs_widget_queue(room_id, result="发送：点歌 + 歌名 点歌", message="当前正在播放点歌", track=None, push_message=True, push_playlist=False)
                            current_is_point_requested = False
                else:
                    # 所有队列均为空，恢复默认歌单播放
                    await update_obs_widget_queue(room_id, result="播放默认歌单", message="下一首无点歌", track=None, push_message=True, push_playlist=False)
                    await spotify_ctrl.restore_default_playlist()
                    current_is_point_requested = False
                    current_is_point_requested_guard = False
                    await asyncio.sleep(5)
                    await update_obs_widget_queue(room_id, result="发送：点歌 + 歌名 点歌", message="当前无点歌", track=None, push_message=True, push_playlist=False)
                    
            await asyncio.sleep(1)
        except Exception as e:
            print(f"[{room_id}]{timestamp()}[ERROR] 后台任务出错：{e}")
            await asyncio.sleep(1)

async def print_queue_status(room_id):
    """
    打印当前普通队列和大航海队列的状态。
    """
    songs_guard = await song_queue_guard.list_songs()
    songs = await song_queue.list_songs()

    if songs_guard:
        print(f"[{room_id}]{timestamp()}[队列] 当前大航海待播队列：{len(songs_guard)} 首")
        for index, song in enumerate(songs_guard, start=1):
            print(f"[{room_id}]{timestamp()}[列队] {index}: {song['name']} - {song['artists'][0]['name']}")
    else:
        print(f"[{room_id}]{timestamp()}[队列] 当前大航海歌曲列表：无")

    if songs:
        print(f"[{room_id}]{timestamp()}[队列] 当前普通待播队列：{len(songs)} 首")
        for index, song in enumerate(songs, start=1):
            print(f"[{room_id}]{timestamp()}[列队] {index}: {song['name']} - {song['artists'][0]['name']}")
    else:
        print(f"[{room_id}]{timestamp()}[队列] 当前普通歌曲列表：无")

async def main():
    global spotify_ctrl, current_is_point_requested, current_is_point_requested_guard
    global client, spotify_ctrl

    # 启动 OBS Widget 服务器
    start_obs_widget()

    await asyncio.sleep(1)  # 等待服务器启动

    print("[VERSION] ----------------------------")
    print("[VERSION] Bilibili-Spotilive 弹幕Spotify点歌机")
    print("[VERSION] 当前版本：v2.0.0")
    print("[VERSION] GitHub仓库地址：")
    print("[VERSION] https://github.com/jo4rchy/Bilibili-Spotilive")
    print("[VERSION] ----------------------------")

    # 加载配置数据
    for attempt in range(MAX_RETRIES):
        try:
            config = load_or_prompt_config()

            # 提取 Bilibili 配置
            bilibili_config = config.get("bilibili", {})
            room_id = bilibili_config.get("room_id")
            streamer_name = bilibili_config.get("streamer_name")
            credential_data = bilibili_config.get("credential", {})
            sessdata = credential_data.get("sessdata")
            bili_jct = credential_data.get("bili_jct")

            credential = Credential(sessdata=sessdata, bili_jct=bili_jct)
            client = BilibiliClient(room_id=room_id, credential=credential, streamer_name=streamer_name)
            song_queue.room_id = room_id
            song_queue_guard.room_id = room_id

            # 提取 Spotify 配置
            spotify_config = config.get("spotify", {})
            spotify_ctrl = SpotifyController(
                client_id=spotify_config["client_id"],
                client_secret=spotify_config["client_secret"],
                redirect_uri=spotify_config["redirect_uri"],
                scope=spotify_config["scope"],
                default_playlist=spotify_config["default_playlist"],
                room_id=room_id,
            )

            print(f"[{room_id}]{timestamp()}[INFO] ✅ 初始化成功，准备启动监听...")
            break  # 成功退出重试循环

        except Exception as e:
            print(f"❌ 第 {attempt+1} 次初始化失败：{e}")
            if attempt < MAX_RETRIES - 1:
                print("🔁 重新打开配置网页以修改配置...")
                if os.path.exists(CONFIG_FILE):
                    os.remove(CONFIG_FILE)
                time.sleep(1)  # 等待一点时间再打开网页
            else:
                print("🚫 多次尝试初始化失败，程序终止。")
                return
    
    # 从配置中提取 Bilibili 相关配置
    bilibili_config = config.get('bilibili', {})
    room_id = bilibili_config.get('room_id')
    streamer_name = bilibili_config.get('streamer_name')
    credential_data = bilibili_config.get('credential', {})
    sessdata = credential_data.get('sessdata')
    bili_jct = credential_data.get('bili_jct')

    song_queue.room_id = room_id  # 初始化点歌队列实例，传入房间号
    song_queue_guard.room_id = room_id  # 初始化大航海点歌队列实例，传入房间号
    
    # 使用从配置中获取的 sessdata 和 bili_jct 创建 Credential 对象
    credential = Credential(sessdata=sessdata, bili_jct=bili_jct)
    
    print(f"[{room_id}]{timestamp()}[INFO] Bilibili 配置加载成功！")
    print(f"[{room_id}]{timestamp()}[INFO] 房间号: {room_id}")
    print(f"[{room_id}]{timestamp()}[INFO] 主播名称: {streamer_name}")  

    # 提取 spotify 配置
    spotify_config = config.get('spotify', {})
    spotify_client_id = spotify_config.get('client_id')
    spotify_client_secret = spotify_config.get('client_secret')
    spotify_redirect_uri = spotify_config.get('redirect_uri')
    spotify_scope = spotify_config.get('scope')
    spotify_default_playlist = spotify_config.get('default_playlist')

    # 初始化 SpotifyController 对象
    spotify_ctrl = SpotifyController(
        client_id=spotify_client_id,
        client_secret=spotify_client_secret,
        redirect_uri=spotify_redirect_uri,
        scope=spotify_scope,
        default_playlist=spotify_default_playlist,
        room_id=room_id
    )
    print(f"[{room_id}]{timestamp()}[INFO] Spotify 配置加载成功！")

    # 初始化 BilibiliClient 对象（在 bilibili_client.py 中定义，见 :contentReference[oaicite:0]{index=0}）

    client = BilibiliClient(room_id=room_id, credential=credential, streamer_name=streamer_name)

    # 注册点歌与下一首处理器
    client.set_song_request_handler(song_request_handler)
    client.set_next_request_handler(next_request_handler)
    
    print(f"[{room_id}]{timestamp()}[INFO] 启动 Bilibili 弹幕监听 ...")

    print(f"[{room_id}]{timestamp()}[INFO] ------------------")
    print(f"[{room_id}]{timestamp()}[INFO] OBS 小组件已启动，访问 http://localhost:5000")
    print(f"[{room_id}]{timestamp()}[INFO] ------------------")

    # 调用 connect() 方法连接弹幕服务，这个方法是异步的，会一直监听直到程序关闭
    await asyncio.gather(
        client.connect(),
        player_loop(room_id)
    )
    
if __name__ == '__main__':
    try:
        # asyncio.run() 启动异步主函数
        asyncio.run(main())
    except KeyboardInterrupt:
        # 当按下 Ctrl+C 时，退出程序
        print("程序已停止。")
