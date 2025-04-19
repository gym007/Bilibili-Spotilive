import asyncio
import re
from bilibili_api import live, Credential
from bilibili_api.utils.danmaku import Danmaku
from log_timer import timestamp
import json
from config import load_config

class BilibiliClient:
    def __init__(self):
        """
        初始化 BilibiliClient 实例
        :param room_id: 房间号，可以是字符串或数字（内部转换为 int）
        :param credential: 使用 bilibili_api.Credential 创建的登录凭证对象
        :param streamer_name: 主播名称，用于身份判断
        """
        config = load_config()

        bilibili_config = config.get("bilibili", {})
        room_id = bilibili_config.get("room_id")
        credential_data = bilibili_config.get("credential", {})
        sessdata = credential_data.get("sessdata")
        bili_jct = credential_data.get("bili_jct")
        credential = Credential(sessdata=sessdata, bili_jct=bili_jct)

        song_request_permission = bilibili_config.get("song_request_permission",{})
        next_request_permission = bilibili_config.get("next_request_permission",{})

        self.room_id = int(room_id)
        self.credential = credential

        self.song_request_permission_treamer = bool(song_request_permission.get("streamer"))
        self.song_request_permission_admin = bool(song_request_permission.get("room_admin"))
        self.song_request_permission_guard = bool(song_request_permission.get("guard"))
        self.song_request_permission_medal_light = bool(song_request_permission.get("medal_light"))
        self.song_request_permission_medal_level = int(song_request_permission.get("medal_level"))

        self.next_request_permission_treamer = bool(next_request_permission.get("streamer"))
        self.next_request_permission_admin = bool(next_request_permission.get("room_admin"))
        self.next_request_permission_guard = bool(next_request_permission.get("guard"))
        self.next_request_permission_medal_light = bool(next_request_permission.get("medal_light"))
        self.next_request_permission_medal_level = int(next_request_permission.get("medal_level"))

        # 实例化弹幕客户端
        self.live_client = live.LiveDanmaku(self.room_id, credential=self.credential)

        # 发送弹幕的客户端
        self.room = live.LiveRoom(self.room_id, credential=self.credential)

        #用于处理弹幕请求“点歌" "下一首” 的外部处理函数
        self.song_request_handler = None
        self.next_request_handler = None
            
    async def connect(self):
        """
        连接到 Bilibili 弹幕服务，并开始监听弹幕信息
        """

        # 获取主播名称
        self.streamer_name = await self.get_streamer_name()
        print(f"[{self.room_id}]{timestamp()}[INFO] 主播名称: {self.streamer_name}")
        print(f"[{self.room_id}]{timestamp()}[INFO] 房间号: {self.room_id}")

        # 注册弹幕事件处理器
        self.live_client.on('DANMU_MSG')(self.on_danmaku)

        print(f"[{self.room_id}]{timestamp()}[INFO] 正在连接 Bilibili 弹幕服务...")
        await self.live_client.connect()

    async def get_streamer_name(self):
        """
        自动获取主播名称
        """
        room_info = await self.room.get_room_info()
        return room_info['anchor_info']['base_info']['uname']
    
    def set_song_request_handler(self, handler):
        """
        设置点歌请求的处理函数
        :param handler: 异步处理函数，用于处理点歌请求 (参数为 song_name，username, room_id， song_request_permission，user_uid)
        """
        self.song_request_handler = handler
    
    def set_next_request_handler(self, handler):
        """
        设置下一首请求的处理函数
        :param handler: 异步处理函数，用于处理下一首请求 (参数为 username, room_id, next_request_permission，user_uid)
        """
        self.next_request_handler = handler

    async def on_danmaku(self, event):
        """
        默认的弹幕事件处理函数
        解析弹幕消息，提取用户信息和弹幕内容，并打印出来
        """
        try:
            text = event['data']['info'][1]
            user_info = event['data']['info'][2]
            
            medal = event['data']['info'][0][15]['user']['medal']
            if medal is not None:
                user_guard_level = event['data']['info'][0][15]['user']['medal']['guard_level']
                user_medal_is_light = event['data']['info'][0][15]['user']['medal']['is_light']
                user_medal_level = event['data']['info'][0][15]['user']['medal']['level']
            else:
                user_guard_level = None
                user_medal_is_light = None
                user_medal_level = None

            # 提取用户名和 UID
            user_name = user_info[1]
            user_uid = user_info[0]
            user_type = user_info[2] if len(user_info) > 2 else 0

            if user_name == self.streamer_name:
                identity = "主播"
                song_request_permission = self.song_request_permission_treamer
                next_request_permission = self.next_request_permission_treamer
            elif user_type == 1:
                identity = "房管"
                song_request_permission = self.song_request_permission_admin
                next_request_permission = self.next_request_permission_admin
            elif user_guard_level == 1:
                identity = "总督"
                song_request_permission = self.song_request_permission_guard
                next_request_permission = self.next_request_permission_guard
            elif user_guard_level == 2:
                identity = "提督"
                song_request_permission = self.song_request_permission_guard
                next_request_permission = self.next_request_permission_guard  
            elif user_guard_level == 3:
                identity = "舰长"
                song_request_permission = self.song_request_permission_guard
                next_request_permission = self.next_request_permission_guard
            elif user_medal_is_light == 1:
                identity = "粉丝团"
                song_request_permission = self.song_request_permission_medal_light
                next_request_permission = self.next_request_permission_medal_light
            else:
                identity = "未点亮"
                if user_medal_level >= self.song_request_permission_medal_level:
                    song_request_permission = True
                else:
                    song_request_permission = False
                
                if user_medal_level >= self.next_request_permission_medal_level:
                    next_request_permission = True
                else:
                    next_request_permission = False

            print(f"[{self.room_id}]{timestamp()}[弹幕] [用户：{user_name}][大航海：{user_guard_level}][身份:{identity}][灯牌点亮：{user_medal_is_light}][灯牌等级：{user_medal_level}][发送：{text}]")            

            if text.startswith("点歌"):
                match = re.match(r"点歌\s*(.+)", text)
                if match:
                    song_name = match.group(1).strip()
                    print(f"[{self.room_id}]{timestamp()}[请求] [用户：{user_name}][请求点歌：{song_name}]")
                    if self.song_request_handler:
                        await self.song_request_handler(song_name, user_guard_level, self.room_id, song_request_permission, user_uid)
                    else:
                        print(f"[{self.room_id}]{timestamp()}[提示] 未注册点歌处理器")
                else:
                    print(f"[{self.room_id}]{timestamp()}[错误] 点歌命令格式错误")

            
            # 如果弹幕内容正好为“下一首”，调用下一首请求处理器
            if text == "下一首":
                print(f"[{self.room_id}]{timestamp()}[请求] [用户：{user_name}][请求下一首]")
                if self.next_request_handler:
                    await self.next_request_handler(user_name, user_guard_level, self.room_id, next_request_permission, user_uid)
                else:
                    print(f"[{self.room_id}]{timestamp()}[提示] 未注册下一首处理器")
      
        except Exception as e:
            print(f"[{self.room_id}]{timestamp()}[ERROR] 处理弹幕出错: {e}")
    
    async def send_danmaku(self, message: str, color: str = "FFFFFF", font_size: int = 25, mode: int = 1):
        #有问题，不知道怎么修
        """
        发送弹幕消息到直播间
        :param message: 要发送的弹幕内容
        :param color: 弹幕颜色（十六进制字符串，例如 "FFFFFF" 表示白色）
        :param font_size: 弹幕字体大小
        :param mode: 弹幕模式（1 表示滚动弹幕）
        """
        print(f"[{self.room_id}]{timestamp()}[发送] [弹幕：{message}]")
        try:
            danmaku = Danmaku(
                text=message,
                color=color,
                font_size=font_size,
                mode=mode
            )
            await self.room.send_danmaku(danmaku=danmaku)
            print(f"[{self.room_id}]{timestamp()}[发送成功] [弹幕：{message}]")
        except Exception as e:
            print(f"[{self.room_id}]{timestamp()}[ERROR] 发送弹幕失败: {e}")


#for debug ----------------------------------------------------------------
def main():
    client = BilibiliClient()
    asyncio.run(client.connect())

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[提示] 退出程序")