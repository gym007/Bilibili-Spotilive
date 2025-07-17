import asyncio
from handler.request_handler import parse_request, request_song_handler, request_next_handler
from apis.api_server import emit_danmaku
from utils.log_timer import timestamp

async def handle_danmaku(danmaku, room_id=None, streamer_uid=None):

    print(f"[{room_id}]{timestamp()}[DANMAKU] {danmaku.uname}: {danmaku.msg}")
    parsed_danmaku = parse_danmaku(danmaku)
    # print(f"[{room_id}]{timestamp()}[DANMAKU PARSED] {parsed_danmaku}")
    emit_danmaku(parsed_danmaku)

    is_streamer = int(danmaku.uid == streamer_uid)

    request = parse_request(danmaku, is_streamer=is_streamer)
    if not request:
        return
    else:
        if request['request']['type'] == 'song':
            await request_song_handler(request)
        elif request['request']['type'] == 'next':
            await request_next_handler(request)

def parse_danmaku(danmaku):
    """解析弹幕数据"""
    return {
        'uname': danmaku.uname,
        'uid': danmaku.uid,
        'face': danmaku.face,
        'msg': danmaku.msg,
        'medal_level': danmaku.medal_level,
        'medal_name': danmaku.medal_name,
        'medal_is_light': danmaku.medal_is_light,
        'privilege_type': danmaku.privilege_type,
        'timestamp': danmaku.timestamp,
    }


