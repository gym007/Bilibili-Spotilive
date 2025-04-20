#当前版本v3.0.2

import asyncio
import time
from bilibili_api import Credential
from bilibili_api.clients import AioHTTPClient,HTTPXClient
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
from dns import namedict, tsigkeyring, versioned
from dns.rdtypes import dnskeybase

import json
import os
import threading
import time
import webbrowser
from flask import Flask, request, render_template, redirect, url_for, flash
from werkzeug.serving import make_server
import sys
import logging
import traceback

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

# spotify和弹幕实例
spotify_ctrl = None
client = None

# 点歌队列实例
song_queue = SongQueue()
song_queue_guard = SongQueue()

# 当前点歌状态标志
current_is_point_requested = False
current_playing_guard = False
current_playing_uid = None


# --- 更新 song_request_handler ---
async def song_request_handler(song_name, user_guard_level, room_id, song_request_permission, user_uid):
    """
    点歌处理器：
      1. 搜索歌曲；
      2. 如果当前未播放点播或播放非点播，则立即播放点播；
      3. 否则，加入大航海或普通队列；
      4. 使用 push_message_update 和 push_playlist_update 分别推送消息与列表。
    """
    global current_is_point_requested, current_playing_uid, current_playing_guard

    # 权限校验
    if not song_request_permission:
        print(f"[{room_id}]{timestamp()}[提示] 点歌权限不足，UID: {user_uid}")
        await push_message_update(room_id, "点亮粉丝图灯牌即可点歌", "点歌失败，权限不足")
        await asyncio.sleep(5)
        await push_playlist_update(room_id)
        return

    # 搜索曲目
    track = await spotify_ctrl.search_song(song_name)
    if not track:
        print(f"[{room_id}]{timestamp()}[提示] 未找到歌曲：{song_name}，UID: {user_uid}")
        await push_message_update(room_id, "未找到符合条件的歌曲", "点歌失败，无匹配")
        await asyncio.sleep(5)
        await push_playlist_update(room_id)
        return

    # 如果未播放点播，立即播放
    if not current_is_point_requested:
        current_is_point_requested = True
        if user_guard_level and user_guard_level > 0:
            current_playing_guard = True
            role_msg = "大航海点歌成功"
            print(f"[{room_id}]{timestamp()}[点歌] 大航海立即播放：{track.get('name')}")
        else:
            role_msg = "普通点歌成功"
            print(f"[{room_id}]{timestamp()}[点歌] 普通用户立即播放：{track.get('name')}")
        await push_message_update(room_id, "当前无点歌，立即播放", role_msg, track)
        await asyncio.sleep(5)
        current_playing_uid = user_uid
        await spotify_ctrl.play_song(track)
        await push_message_update(room_id, "发送：点歌 + 歌名 点歌", "当前正在播放点歌")
    # 否则加入队列
    else:
        if user_guard_level and user_guard_level > 0:
            queue = song_queue_guard
            role = "大航海"
        else:
            queue = song_queue
            role = "普通"
        print(f"[{room_id}]{timestamp()}[队列] 点歌成功，加入{role}队列：{track.get('name')}")
        await queue.add_song(track, user_uid, role)
        await push_message_update(room_id, f"点歌 {track.get('name')}", f"点歌成功，加入{role}队列", track)
        await asyncio.sleep(5)
        await push_playlist_update(room_id)
    
    await asyncio.sleep(1)
    await print_queue_status(room_id)

# --- next_request_handler ---
async def next_request_handler(username, user_guard_level, room_id, next_request_permission, user_uid):
    global current_is_point_requested, current_playing_uid, current_playing_guard
    
    # 权限校验
    if user_uid == current_playing_uid:
        allow_next = True
    else:
        allow_next = next_request_permission

    if not allow_next:
        print(f"[{room_id}]{timestamp()}[提示] 下一首权限不足")
        await push_message_update(room_id, "加入大航海即可切歌", "下一首失败，权限不足")
        await asyncio.sleep(5)
        await push_playlist_update(room_id)
        return
    
    if not current_is_point_requested:
        print(f"[{room_id}]{timestamp()}[提示] 当前无点歌，恢复默认歌单。")
        current_is_point_requested = False
        current_playing_uid = None
        current_playing_guard = False
        await push_message_update(room_id, "下一首随机播放默认歌单", "当前无点歌")
        await asyncio.sleep(5)
        await spotify_ctrl.restore_default_playlist()
        await push_message_update(room_id, "发送：点歌 + 歌名 点歌", "当前无点歌")
        return

    if current_playing_guard and user_uid != current_playing_uid:

        print(f"[{room_id}]{timestamp()}[提示] 当前正在播放其他大航海点歌，无法切歌。")
        await push_message_update(room_id, "当前正在播放大航海点歌", "下一首失败")
        await asyncio.sleep(5)
        await push_playlist_update(room_id)
        return

    if not song_queue_guard.is_empty():
        queue = song_queue_guard
        current_is_point_requested = True
        current_playing_guard = True
    else:
        queue = song_queue
        current_playing_guard = False

    item = await queue.get_next_song()
    if item:
        track = item["song"]
        req_uid = item["request_uid"]
        current_playing_uid = req_uid

        print(f"[{room_id}]{timestamp()}[切歌] 下一首成功，立即播放下一首")
        await push_message_update(room_id, "立即播放下一首", "下一首成功", track)
        await asyncio.sleep(5)
        await spotify_ctrl.play_song(track)
        await push_playlist_update(room_id)
    else:
        print(f"[{room_id}]{timestamp()}[提示] 当前无点歌，恢复默认歌单。")
        current_is_point_requested = False
        current_playing_uid = None
        current_playing_guard = False
        await push_message_update(room_id, "下一首随机播放默认歌单", "当前无点歌")
        await asyncio.sleep(5)
        await spotify_ctrl.restore_default_playlist()
        await push_message_update(room_id, "发送：点歌 + 歌名 点歌", "当前无点歌")

    await asyncio.sleep(1)
    await print_queue_status(room_id)

# --- update_obs_widget_queue ---
async def update_obs_widget(room_id, result, message, track, push_message, push_playlist):
    """
    同步推送当前播放信息和待播列表给 OBS widget。
    push_message: 是否触发新的 message_data 推送
    push_playlist: 是否触发新的 playlist_data 推送
    """
    songs_guard = await song_queue_guard.list_songs()
    songs = await song_queue.list_songs()
    combined = songs_guard + songs
    # 列表部分
    if push_playlist:
        obs_widget.playlist_data = [{
            "name": f"{item['song'].get('name','未知歌曲')} - {item['song'].get('artists',[{'name':'未知'}])[0]['name']}",
            "albumCover": item['song'].get('album',{}).get('images',[{}])[0].get('url',''),
            "request_uid": item.get('request_uid')
        } for item in combined]
    # 消息部分
    if push_message:
        obs_widget.message_data = {
            "message": message,
            "result": result,
            "albumCover": track.get('album',{}).get('images',[{}])[0].get('url','') if track else '/static/images/Spotify.png'
        }
    obs_widget.new_message = push_message
    obs_widget.new_playlist = push_playlist
    obs_widget.room_id = room_id

# --- push_playlist_update ---
async def push_playlist_update(room_id):
    """单独推送当前待播清单，不修改播放信息，仅更新列表。"""
    global current_is_point_requested

    songs_guard = await song_queue_guard.list_songs()
    songs = await song_queue.list_songs()
    combined = songs_guard + songs
    if combined:
        await update_obs_widget(room_id, None, None, None, False, True)
    elif current_is_point_requested:
        await push_message_update(room_id, "发送：点歌 + 歌名 点歌", "当前正在播放点歌")
    else:
        await push_message_update(room_id, "发送：点歌 + 歌名 点歌", "当前无点歌")

# --- push_message_update ---
async def push_message_update(room_id, result, message, track=None):
    """单独推送播放信息，不修改列表，仅更新 message_data。"""
    await update_obs_widget(room_id, result, message, track, True, False)

# --- player_loop ---
async def player_loop(room_id):
    """
    后台任务：
      持续检测当前点播播放状态，
      如果当前没有点播播放且有待播队列，则优先播放大航海队列，再播放普通队列；
      队列空时恢复默认歌单，并重置点歌状态。
    """
    global current_is_point_requested, current_playing_uid, current_playing_guard

    while True:
        try:
            # 查询 Spotify 播放状态
            current = await asyncio.to_thread(spotify_ctrl.sp.current_playback)
            is_playing = current and current.get("is_playing")

            # 如果当前没在播但有点歌请求
            if not is_playing and current_is_point_requested:
                # 1. 选择队列：大航海优先
                if not song_queue_guard.is_empty():
                    queue = song_queue_guard
                    current_playing_guard = True
                elif not song_queue.is_empty():
                    queue = song_queue
                    current_playing_guard = False
                else:
                    queue = None
                    current_playing_guard = False

                # 2. 播放下一首
                if queue:
                    item = await queue.get_next_song()
                    track = item["song"]
                    req_uid = item["request_uid"]

                    current_is_point_requested = True
                    current_playing_uid = req_uid
                    await spotify_ctrl.play_song(track)
                    await push_playlist_update(room_id)

                # 3. 队列空 -> 恢复默认歌单
                else:
                    current_is_point_requested = False
                    current_playing_uid = None
                    current_playing_guard = False

                    await spotify_ctrl.restore_default_playlist()
                    await push_message_update(room_id, "发送：点歌 + 歌名 点歌", "当前无点歌")

            # 轮询间隔
            await asyncio.sleep(1)

        except Exception as e:
            print(f"[{room_id}]{timestamp()}[ERROR] 后台任务出错：{e}")
            await asyncio.sleep(1)


# --- print_queue_status ---
async def print_queue_status(room_id):
    songs_guard = await song_queue_guard.list_songs(); songs = await song_queue.list_songs()
    print(f"[{room_id}]{timestamp()}[队列] ----------------------------------------")
    if songs_guard:
        print(f"[{room_id}]{timestamp()}[队列] 当前大航海待播队列：{len(songs_guard)} 首")
        for idx, item in enumerate(songs_guard, start=1):
            t = item['song']; uid = item.get('request_uid'); name = t.get('name','未知歌曲'); art = t.get('artists',[{'name':'未知'}])[0].get('name')
            print(f"[{room_id}]{timestamp()}[队列] {idx}: {name} - {art} (UID: {uid})")
    else:
        print(f"[{room_id}]{timestamp()}[队列] 当前大航海歌曲列表：无")
    if songs:
        print(f"[{room_id}]{timestamp()}[队列] 当前普通待播队列：{len(songs)} 首")
        for idx, item in enumerate(songs, start=1):
            t = item['song']; uid = item.get('request_uid'); name = t.get('name','未知歌曲'); art = t.get('artists',[{'name':'未知'}])[0].get('name')
            print(f"[{room_id}]{timestamp()}[队列] {idx}: {name} - {art} (UID: {uid})")
    else:
        print(f"[{room_id}]{timestamp()}[队列] 当前普通歌曲列表：无")
    print(f"[{room_id}]{timestamp()}[队列] ----------------------------------------")

async def main():
    global spotify_ctrl, current_is_point_requested, current_playing_uid, current_playing_guard
    global client, spotify_ctrl

    print("[VERSION] ----------------------------")
    print("[VERSION] Bilibili-Spotilive 弹幕Spotify点歌机")
    print("[VERSION] 当前版本：v3.0.2")
    print("[VERSION] GitHub仓库地址：")
    print("[VERSION] https://github.com/jo4rchy/Bilibili-Spotilive")
    print("[VERSION] ----------------------------")

    for attempt in range(MAX_RETRIES):
        try:
            config = load_or_prompt_config()
            bilibili_config = config.get("bilibili", {})
            room_id = bilibili_config.get("room_id")
            print(f"[{room_id}]{timestamp()}[INFO] ✅ 初始化成功，准备启动监听...")
            break
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

    config = load_config()

    # 从配置中提取 Bilibili 相关配置
    bilibili_config = config.get('bilibili', {})
    room_id = bilibili_config.get('room_id')

    song_queue.room_id = room_id  # 初始化点歌队列实例，传入房间号
    song_queue_guard.room_id = room_id  # 初始化大航海点歌队列实例，传入房间号
    
    print(f"[{room_id}]{timestamp()}[INFO] Bilibili 配置加载成功！")

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

    # 初始化 BilibiliClient 对象
    client = BilibiliClient()

    # 注册点歌与下一首处理器
    client.set_song_request_handler(song_request_handler)
    client.set_next_request_handler(next_request_handler)
    
    print(f"[{room_id}]{timestamp()}[INFO] ------------------")
    start_obs_widget()
    await asyncio.sleep(1)  # 等待服务器启动
    print(f"[{room_id}]{timestamp()}[INFO] OBS 小组件已启动，访问 http://localhost:5000")
    print(f"[{room_id}]{timestamp()}[INFO] OBS 添加浏览器采集：")
    print(f"[{room_id}]{timestamp()}[INFO] http://localhost:5000")
    print(f"[{room_id}]{timestamp()}[INFO] 即可展示点歌机状态小组件")
    print(f"[{room_id}]{timestamp()}[INFO] ------------------")

    print(f"[{room_id}]{timestamp()}[INFO] 启动 Bilibili 弹幕监听 ...")

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
