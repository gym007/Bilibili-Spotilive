import asyncio
import re
from bilibili_api import live, Credential
from bilibili_api.utils.danmaku import Danmaku
from log_timer import timestamp

class BilibiliClient:
    def __init__(self, room_id, credential: Credential, streamer_name: str):
        """
        初始化 BilibiliClient 实例
        :param room_id: 房间号，可以是字符串或数字（内部转换为 int）
        :param credential: 使用 bilibili_api.Credential 创建的登录凭证对象
        :param streamer_name: 主播名称，用于身份判断
        """
        self.room_id = int(room_id)
        self.credential = credential
        self.streamer_name = streamer_name
        
        # 实例化弹幕客户端
        self.live_client = live.LiveDanmaku(self.room_id, credential=self.credential)

        # 发送弹幕的客户端
        self.room = live.LiveRoom(self.room_id, credential=self.credential)
        
        # 注册默认的弹幕消息处理函数
        self.live_client.on('DANMU_MSG')(self.on_danmaku)

        #用于处理弹幕请求“点歌" "下一首” 的外部处理函数
        self.song_request_handler = None
        self.next_request_handler = None

    def set_song_request_handler(self, handler):
        """
        设置点歌请求的处理函数
        :param handler: 异步处理函数，用于处理点歌请求 (参数为 song_name，username, room_id)
        """
        self.song_request_handler = handler
    
    def set_next_request_handler(self, handler):
        """
        设置下一首请求的处理函数
        :param handler: 异步处理函数，用于处理下一首请求 (参数为 username, room_id)
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
                user_is_light = event['data']['info'][0][15]['user']['medal']['is_light']
                user_lgiht_level = event['data']['info'][0][15]['user']['medal']['level']
            else:
                user_guard_level = 0
                user_is_light = 0
                user_lgiht_level = 0

            username = user_info[1]
            userudid = user_info[0]
            user_type = user_info[2] if len(user_info) > 2 else 0
            # full= event #for debug

            # print(f"{timestamp()}[大航海：{user_guard_level}]") debug print
            
            # 判断身份（示例：主播 > 房管 > 舰长 > 粉丝团 > 游客）
            if username == self.streamer_name:
                identity = "主播"
                song_request_permission = True
                next_request_permission = True
            elif user_type == 1:
                identity = "房管"
                song_request_permission = True
                next_request_permission = True
            elif user_guard_level == 1:
                identity = "总督"
                song_request_permission = True
                next_request_permission = True
            elif user_guard_level == 2:
                identity = "提督"
                song_request_permission = True
                next_request_permission = True    
            elif user_guard_level == 3:
                identity = "舰长"
                song_request_permission = True
                next_request_permission = True
            elif user_is_light == 1:
                identity = "粉丝团"
                song_request_permission = True
                next_request_permission = False
            else:
                identity = "未点亮"
                song_request_permission = False
                next_request_permission = False

            print(f"[{self.room_id}]{timestamp()}[弹幕] [用户：{username}][大航海：{user_guard_level}][身份:{identity}][灯牌点亮：{user_is_light}][灯牌等级：{user_lgiht_level}][发送：{text}]")
            # print(f"{full}") #MANMU_MSG 元数据 for debug

            # 如果弹幕以“点歌”开头，解析歌曲名称并调用点歌处理器
            if text.startswith("点歌") and song_request_permission:
                match = re.match(r"点歌\s*(.+)", text)
                if match:
                    song_name = match.group(1).strip()
                    print(f"[{self.room_id}]{timestamp()}[请求] [用户：{username}][请求点歌：{song_name}]")
                    if self.song_request_handler:
                        await self.song_request_handler(song_name, user_guard_level, self.room_id)
                    else:
                        print(f"[{self.room_id}]{timestamp()}[提示] 未注册点歌处理器")
                else:
                    print(f"[{self.room_id}]{timestamp()}[错误] 点歌命令格式错误")
            elif text.startswith("点歌") and not song_request_permission:
                print(f"[{self.room_id}]{timestamp()}[无权] [用户：{username}][无权点歌]")
            
            # 如果弹幕内容正好为“下一首”，调用下一首请求处理器
            if text == "下一首" and next_request_permission:
                print(f"[{self.room_id}]{timestamp()}[请求] [用户：{username}][请求下一首]")
                if self.next_request_handler:
                    await self.next_request_handler(username, self.room_id)
                else:
                    print(f"[{self.room_id}]{timestamp()}[提示] 未注册下一首处理器")
            elif text == "下一首" and not next_request_permission:
                print(f"[{self.room_id}]{timestamp()}[无权] [用户：{username}][无权请求下一首]")
      
        except Exception as e:
            print(f"[{self.room_id}]{timestamp()}[ERROR] 处理弹幕出错: {e}")

    async def send_danmaku(self, message):
        """
        发送弹幕消息到直播间
        :param message: 要发送的弹幕内容
        """
        danmaku = Danmaku(text = message)
        try:
            await self.room.send_danmaku(danmaku = danmaku)
            print(f"[{self.room_id}]{timestamp()}[发送] [弹幕：{message}]")
        except Exception as e:
            print(f"[{self.room_id}]{timestamp()}[ERROR] 发送弹幕失败: {e}")

    async def connect(self):
        """
        连接到 Bilibili 弹幕服务，并开始监听弹幕信息
        """
        print(f"[{self.room_id}]{timestamp()}[INFO] 正在连接 Bilibili 弹幕服务...")
        await self.live_client.connect()

    def register_handler(self, event_type: str, handler):
        """
        外部注册新的事件处理器
        :param event_type: 事件类型（例如 'DANMU_MSG'）
        :param handler: 异步处理函数，用于处理该类型事件
        """
        self.live_client.on(event_type)(handler)
