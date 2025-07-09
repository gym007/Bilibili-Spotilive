import asyncio
from handler.request_handler import parse_request, request_song_handler, request_next_handler
from utils.log_timer import timestamp

async def handle_danmaku(danmaku, room_id=None, streamer_uid=None):

    print(f"[{room_id}]{timestamp()}[DANMAKU] {danmaku.uname}: {danmaku.msg}")

    is_streamer = int(danmaku.uid == streamer_uid)

    request = parse_request(danmaku, is_streamer=is_streamer)
    if not request:
        return
    else:
        if request['request']['type'] == 'song':
            await request_song_handler(request)
        elif request['request']['type'] == 'next':
            await request_next_handler(request)

