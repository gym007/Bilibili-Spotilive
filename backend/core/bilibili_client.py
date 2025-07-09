import asyncio
import re
from bilibili_api import live, Credential
from model.model import DanmakuMessage
from utils.log_timer import timestamp
import json

danmaku_callback = None
room_info = {
    "room_id": None,
    "streamer_name": None,
    "streamer_uid": None
}

def set_danmaku_callback(callback):
    """
    设置弹幕回调函数
    :param callback: 弹幕回调函数，接受 DanmakuMessage 对象和其他参数
    """
    global danmaku_callback
    danmaku_callback = callback

class BilibiliClient:
    def __init__(self, config):

        """
        初始化 BilibiliClient 实例
        :param room_id: 房间号，可以是字符串或数字（内部转换为 int）
        :param credential: 使用 bilibili_api.Credential 创建的登录凭证对象      
        """
        bilibili_config = config.get("bilibili", {})
        room_id = bilibili_config.get("room_id")
        credential_data = bilibili_config.get("credential", {})
        sessdata = credential_data.get("sessdata")
        bili_jct = credential_data.get("bili_jct")

        crendential = Credential(sessdata=sessdata, bili_jct=bili_jct)

        self.room_id = int(room_id)
        self.credential = crendential

        self.live_client = live.LiveDanmaku(self.room_id, credential=self.credential)
        self.live_room = live.LiveRoom(self.room_id, credential=self.credential)

        self.danmaku_callback = danmaku_callback

    async def connect(self):
        """
        连接到 Bilibili 直播间
        """
        global room_info
        self.streamer_name = await self.get_streamer_name()
        self.streamer_uid = await self.get_streamer_uid()

        print(f"[{self.room_id}]{timestamp()}[INFO] 主播名称: {self.streamer_name}")
        print(f"[{self.room_id}]{timestamp()}[INFO] 主播 UID: {self.streamer_uid}")
        print(f"[{self.room_id}]{timestamp()}[INFO] 主播房间号: {self.room_id}")
        print(f"[{self.room_id}]{timestamp()}[INFO] ──────────────────────────────\n")        

        # 更新全局房间信息
        room_info = {
            "room_id": self.room_id,
            "streamer_name": self.streamer_name,
            "streamer_uid": self.streamer_uid
        }

        # 注册弹幕事件处理器
        self.live_client.on('DANMU_MSG')(self.on_danmaku)

        print(f"[{self.room_id}]{timestamp()}[INFO] ──────────────────────────────")
        print(f"[{self.room_id}]{timestamp()}[INFO] 正在连接 Bilibili 弹幕服务...")
        await self.live_client.connect()
    
    async def disconnect(self):
        """
        断开与 Bilibili 直播间的连接
        """
        print(f"[{self.room_id}]{timestamp()}[INFO] 正在断开 Bilibili 弹幕服务连接...")
        await self.live_client.disconnect()
        print(f"[{self.room_id}]{timestamp()}[INFO] 已断开连接")

    async def get_streamer_name(self):
        """
        自动获取主播名称
        """
        room_info = await self.live_room.get_room_info()
        return room_info['anchor_info']['base_info']['uname']

    async def get_streamer_uid(self):
        """
        自动获取主播 UID
        """
        room_info = await self.live_room.get_room_info()
        return room_info['room_info']['uid'] 

    async def on_danmaku(self, event):
        try:
            danmaku_message = DanmakuMessage.from_command(event['data']['info'])
            if self.danmaku_callback:
                await self.danmaku_callback(danmaku_message, room_id = self.room_id, streamer_uid = self.streamer_uid)
        except Exception as e:
            print(f"[{self.room_id}]{timestamp()}[ERROR] 弹幕处理出错: {e}")