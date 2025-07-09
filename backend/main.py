## main.py
# -*- coding: utf-8 -*-
"""
Still in development, do not use in production.
"""

import asyncio
import threading
from apis.api_server import set_api_spotify_controller, start_api_server
from core.bilibili_client import BilibiliClient, set_danmaku_callback
from core.spotify_controller import SpotifyController
from handler.permission_handler import PermissionHandler
from handler.danmaku_handler import handle_danmaku
from handler.request_handler import set_request_spotify_controller, set_permission_handler
from core.player_loop import set_player_spotify_controller, player_loop
from config.config import load_config

bilibili_client = None
perm_handler = None
spotify_ctrl = None

def start_api():
    t = threading.Thread(target=start_api_server, daemon=True)
    t.start()

async def main():
    global bilibili_client, perm_handler, spotify_ctrl
    config = load_config()
    
    set_danmaku_callback(handle_danmaku)

    perm_handler = PermissionHandler(config)
    set_permission_handler(perm_handler)

    bilibili_client = BilibiliClient(config)
    spotify_ctrl = SpotifyController(config)
    
    set_api_spotify_controller(spotify_ctrl)
    set_player_spotify_controller(spotify_ctrl)
    set_request_spotify_controller(spotify_ctrl)

    # 启动 API 服务器
    start_api()
    await asyncio.sleep(1)  # 等待服务器启动

    await asyncio.gather(
        bilibili_client.connect(),
        player_loop(room_id=14005096)  # 连接到 Bilibili 直播间
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("程序被中断，正在退出...")

