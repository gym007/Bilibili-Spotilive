#import threading
import asyncio
#import json
#import os
#import time
from bilibili_api import Credential
from bilibili_api.clients import AioHTTPClient
from bilibili_client import BilibiliClient
from spotify_controller import SpotifyController
from song_queue import SongQueue
from config import load_config
#import config_web
from log_timer import timestamp

# 配置文件名称，确保这个文件与 main.py 在同一目录中
CONFIG_FILE = 'config.json'

def load_app_config():
    config = load_config()
    # 可在这里对配置数据进行简单判断，例如
    if not config.get("bilibili", {}).get("room_id"):
        print(f"[WARNING]{timestamp()} Bilibili 配置不完整，请先配置。")
    if not config.get("spotify", {}).get("client_id"):
        print(f"[WARNING]{timestamp()} Spotify 配置不完整，请先配置。")
    return config

# 全局变量：SpotifyController 实例、点歌队列和当前播放状态标识
spotify_ctrl = None

# 点歌队列实例，用于存储普通用户点歌请求的歌曲
song_queue = SongQueue()
# 点歌列队实例，用于储存大航海用户请求的歌曲
song_queue_guard = SongQueue()

# 用于标识当前播放是否为用户点歌（True: 点歌歌曲；False: 默认歌单歌曲）
current_is_point_requested = False
# 用于标识当前播放是否为大航海用户点歌（True: 点歌歌曲；False: 默认歌单歌曲）
current_is_point_requested_guard = False

async def song_request_handler(song_name, user_guard_level, room_id):
    """
    点歌处理器：
      1. 利用 SpotifyController 搜索歌曲；
      2. 如果当前没有播放歌曲，立即播放点歌歌曲，并标记为点歌歌曲；
      3. 如果正在播放歌曲，则判断：
          - 若当前播放的是默认歌单歌曲，则打断默认播放，直接播放新请求的点歌歌曲；
          - 若当前播放的是点歌歌曲，则将新请求加入待播队列。
    """
    global current_is_point_requested, current_is_point_requested_guard
    # print(f"[{room_id}]{timestamp()}[处理点歌] 用户 {username} 请求点歌：{song_name}") debug print
    track = await spotify_ctrl.search_song(song_name)
    if track:
        current = await asyncio.to_thread(spotify_ctrl.sp.current_playback)
        if current is None or not current.get('is_playing'):
            # 当前没有播放，直接播放点歌歌曲
            print(f"[{room_id}]{timestamp()}[点歌] 当前无播放，立即播放点歌。")
            current_is_point_requested = True # 标记为点歌歌曲
            if user_guard_level != 0:
                current_is_point_requested_guard = True # 标记为大航海歌曲
            # 直接播放点歌歌曲
            await spotify_ctrl.play_song(track)
        else:   # 当前有播放
            if not current_is_point_requested:
                # 当前播放的是默认歌单中的歌曲，打断后立即播放新点歌歌曲
                print(f"[{room_id}]{timestamp()}[点歌] 当前无点歌，立即播放点歌。")
                current_is_point_requested = True
                if user_guard_level != 0:
                    current_is_point_requested_guard = True
                await spotify_ctrl.play_song(track)
            # 如果当前播放的是点歌歌曲
            else:
                if user_guard_level != 0:
                    # 当前播放的是大航海歌曲，直接加入大航海待播队列
                    print(f"[{room_id}]{timestamp()}[列队] 加入大航海待播队列。")
                    await song_queue_guard.add_song(track)
                    current_is_point_requested_guard = True
                else:
                    # 当前播放的是普通歌曲，直接加入普通待播队列
                    print(f"[{room_id}]{timestamp()}[列队] 加入普通待播队列。")
                    await song_queue.add_song(track)

        songs = await song_queue.list_songs()
        songs_guard = await song_queue_guard.list_songs()

        if len(songs_guard) > 0:   
            print(f"[{room_id}]{timestamp()}[队列] 当前大航海待播队列：{len(songs_guard)} 首------------------")
            for index, song in enumerate(songs_guard, start=1):
                song_info = f"{song['name']} - {song['artists'][0]['name']}"
                print(f"[{room_id}]{timestamp()}[列队] {index}: {song_info}")
            print(f"[{room_id}]{timestamp()}[列队] ------------------------------------")
        else:
            print(f"[{room_id}]{timestamp()}[列队] 当前大航海歌曲列表：无")

        if len(songs) > 0:
            print(f"[{room_id}]{timestamp()}[队列] 当前普通待播队列：{len(songs)} 首------------------")
            for index, song in enumerate(songs, start=1):
                song_info = f"{song['name']} - {song['artists'][0]['name']}"
                print(f"[{room_id}]{timestamp()}[列队] {index}: {song_info}")
            print(f"[{room_id}]{timestamp()}[列队] ----------------------------------------")
        else:
            print(f"[{room_id}]{timestamp()}[列队] 当前普通歌曲列表：无")
    else:
        print(f"[{room_id}]{timestamp()}[提示] 没有找到歌曲：{song_name}")

async def next_request_handler(username, room_id):
    """
    处理“下一首”请求：
      如果待播队列有歌曲，则播放下一首；否则恢复默认歌单播放，并标记当前为默认模式。
    """
    global current_is_point_requested, current_is_point_requested_guard

    if current_is_point_requested and not current_is_point_requested_guard:
        next_track = await song_queue.get_next_song()
        if next_track:
            song_info = f"{next_track['name']} - {next_track['artists'][0]['name']}"
            print(f"[{room_id}]{timestamp()}[队列] 播放普通队列中的下一首：{song_info}")
            await spotify_ctrl.play_song(next_track)

            songs = await song_queue.list_songs()
            songs_guard = await song_queue_guard.list_songs()

            if len(songs_guard) > 0:   
                print(f"[{room_id}]{timestamp()}[队列] 当前大航海待播队列：{len(songs_guard)} 首------------------")
                for index, song in enumerate(songs_guard, start=1):
                    song_info = f"{song['name']} - {song['artists'][0]['name']}"
                    print(f"[{room_id}]{timestamp()}[列队] {index}: {song_info}")
                print(f"[{room_id}]{timestamp()}[列队] ---------------------------------------")
            else:
                print(f"[{room_id}]{timestamp()}[列队] 当前大航海歌曲列表：无")

            if len(songs) > 0:
                print(f"[{room_id}]{timestamp()}[队列] 当前普通待播队列：{len(songs)} 首------------------")
                for index, song in enumerate(songs, start=1):
                    song_info = f"{song['name']} - {song['artists'][0]['name']}"
                    print(f"[{room_id}]{timestamp()}[列队] {index}: {song_info}")
                print(f"[{room_id}]{timestamp()}[列队] -------------------------------------")
            else:
                print(f"[{room_id}]{timestamp()}[列队] 当前普通歌曲列表：无")
        else:
            print(f"[{room_id}]{timestamp()}[提示] 所有队列已空，恢复默认歌单。")
            current_is_point_requested = False
            await spotify_ctrl.restore_default_playlist()
    elif current_is_point_requested_guard:
        print(f"[{room_id}]{timestamp()}[队列] 当前播放大航海点歌，无法跳过。")
    else:
        print(f"[{room_id}]{timestamp()}[队列] 所有队列已空，恢复默认歌单。")
        current_is_point_requested = False
        await spotify_ctrl.restore_default_playlist()

async def player_loop(room_id):
    """
    后台任务：
      持续检测当前点播播放状态，
      如果当前没有点播播放且待播队列为空，则恢复默认歌单播放，并将播放标识设置为默认模式（False）。
    """
    global current_is_point_requested, current_is_point_requested_guard

    # 进入后台任务循环
    # 这里使用了 asyncio.to_thread() 来在后台线程中运行 Spotify 的 current_playback 方法
    # 这样可以避免在主线程中阻塞，保持异步执行
    # 你可以根据需要调整 sleep 的时间间隔
    while True:
        current = await asyncio.to_thread(spotify_ctrl.sp.current_playback)
        if current is None or not current.get('is_playing'):
            if not song_queue_guard.is_empty():
                next_track = await song_queue_guard.get_next_song()
                if next_track:
                    song_info = f"{next_track['name']} - {next_track['artists'][0]['name']}"
                    print(f"[{room_id}]{timestamp()}[队列] 自动播放大航海队列中的下一首：{song_info}")
                    await spotify_ctrl.play_song(next_track)
            elif song_queue_guard.is_empty() and not song_queue.is_empty():
                current_is_point_requested_guard = False
                next_track = await song_queue.get_next_song()
                if next_track:
                    song_info = f"{next_track['name']} - {next_track['artists'][0]['name']}"
                    print(f"[{room_id}]{timestamp()}[队列] 自动播放普通队列中的下一首：{song_info}")
                    await spotify_ctrl.play_song(next_track)    
            else:
                # 若队列空且当前无播放，恢复默认歌单播放，标记播放状态为默认模式
                if current_is_point_requested:
                    print(f"[{room_id}]{timestamp()}[队列] 点歌已结束，恢复默认歌单。")
                    current_is_point_requested = False
                    await spotify_ctrl.restore_default_playlist()    
        await asyncio.sleep(3)

async def main():
    global spotify_ctrl, current_is_point_requested, current_is_point_requested_guard

    # 在后台启动配置网页服务
    #threading.Thread(target=config_web.run_config_server, daemon=True).start()
    #threading.Thread(target=config_web.open_config_browser, daemon=True).start()

    #time.sleep(2)  # 等待配置网页启动
    print("当前版本：v1.0.2")
    # 加载配置数据
    config = load_app_config()
    
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
    global spotify_ctrl
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
