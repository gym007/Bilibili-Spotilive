import asyncio
from utils.log_timer import timestamp
from handler.queue_manager import song_queue, song_queue_guard, song_queue_streamer
from apis.obs_widget import create_message_message, create_queue_message
from apis.api_server import emit_message, emit_queue, clear_queue, emit_request
from typing import Optional, Dict

spotify_ctrl = None
current_request: Optional[Dict] = None

def set_player_spotify_controller(controller):
    global spotify_ctrl
    spotify_ctrl = controller


# Emit functions ------------------------------------------------------------
async def emit_message_to_widget(message_data):
    emit_message(message_data)

async def emit_queue_to_widget(playlist_data):
    emit_queue(playlist_data)

async def emit_request_to_electron(request_data):
    emit_request(request_data)

async def _emit_simple(text: str, subtext: str = "", song: Optional[Dict] = None):
    msg = create_message_message(text, subtext, song)
    await emit_message_to_widget(msg)

async def _emit_queue_status():
    queue_msg = await create_queue_message()
    if queue_msg:
        await emit_queue_to_widget(queue_msg)
    else:
        guide_msg = create_message_message("点歌队列空", "发送：点歌 + 歌名 即可点歌")
        clear_queue()
        await emit_message_to_widget(guide_msg)

async def _feedback_and_update(text: str, subtext: str = "", song: Optional[Dict] = None, delay: float = 3.0):
    await _emit_simple(text, subtext, song)
    await asyncio.sleep(delay)
    await _emit_queue_status()

# Emit functions ------------------------------------------------------------

async def get_next_item() -> Optional[Dict]:
    for queue in (song_queue_streamer, song_queue_guard, song_queue):
        if not queue.is_empty():
            return await queue.get_next_song()
    return None

async def _play_song_item(item: Dict, room_id: str = ""):
    global current_request
    current_request = item
    song = item["song"]
    user = item["request"]["user"]
    print(f"[{room_id}]{timestamp()} 播放点歌 → {song.get('name')} (点歌人: {user['uname']})")
    await spotify_ctrl.play_song(song)
    await _emit_queue_status()

async def player_loop(room_id: str):
    global current_request
    if spotify_ctrl is None:
        raise RuntimeError("请先调用 set_player_spotify_controller() 注入控制器")

    while True:
        try:
            status = await spotify_ctrl.get_current_playback()
            is_playing = bool(status and status.get("is_playing"))

            if not is_playing:
                if current_request:
                    current_request = None
                    print(f"[{room_id}]{timestamp()} 清除当前点歌")
                    await _emit_queue_status()

                next_item = await get_next_item()
                if next_item:
                    await _play_song_item(next_item, room_id)
                else:
                    print(f"[{room_id}]{timestamp()} 恢复默认歌单")
                    await spotify_ctrl.restore_default_playlist()
                    await _emit_queue_status()
            await asyncio.sleep(1)
        except Exception as e:
            print(f"[{room_id}]{timestamp()} LOOP 错误：{e}")
            await asyncio.sleep(2)

async def play_next_song() -> bool:
    global current_request
    if spotify_ctrl is None:
        raise RuntimeError("play_next_song: spotify_ctrl 未设置")

    next_item = await get_next_item()
    if next_item:
        song = next_item["song"]
        user = next_item["request"]["user"]
        await _feedback_and_update(
            f"切歌: {song['name']}",
            f"由: {user['uname']}",
            song
        )
        print(f"[]{timestamp()} 自动播放下一首：{song['name']} (点歌人 {user['uname']})")
        await _play_song_item(next_item)
    else:
        current_request = None
        await _feedback_and_update(
            "切歌成功",
            "点歌列表空，播放默认歌单"
        )
        print(f"[]{timestamp()} 恢复默认歌单")
        await spotify_ctrl.restore_default_playlist()
    return True

async def next_song(request: Dict, next_perm: bool) -> bool:
    global current_request
    user = request["user"]

    if current_request is None:
        if next_perm:
            return await play_next_song()
        else:
            await _feedback_and_update("切歌权限不足", "切歌失败")
            return False

    requester = current_request["request"]["user"]
    has_perm = (
        user["uid"] == requester["uid"]
        or user.get("is_streamer")
        or (
            user.get("privilege_type", 0) > 0
            and not requester.get("is_streamer")
            and requester.get("privilege_type", 0) == 0
        )
    )
    if has_perm:
        return await play_next_song()

    await _feedback_and_update("无法跳过大航海点歌", "切歌失败")
    return False

async def request_song(request: Dict, request_perm: bool) -> bool:
    global current_request
    user = request["user"]
    keyword = request.get("request", {}).get("keyword", "")

    if not request_perm:
        await _feedback_and_update("点歌失败", "权限不足，点亮灯牌即可点歌")
        return False

    try:
        song = await spotify_ctrl.search_song(keyword)
        if not song:
            await _feedback_and_update("点歌失败", "未找到匹配的歌曲")
            return False

        artist = song.get("artists", [{}])[0].get("name", "")
        text = f"点歌成功: {song.get('name', 'Unknown')} - {artist}"

        if current_request is None:
            await _feedback_and_update(text, "立即播放", song)
            print(f"[{user['uname']}] 播放点歌 → {song.get('name')}")
            await _play_song_item({"song": song, "request": request})
        else:
            queue_item = {"song": song, "request": request}
            if user.get("is_streamer"):
                await song_queue_streamer.add_song(queue_item)
                btn = "加入主播队列"
            elif user.get("privilege_type", 0) > 0:
                await song_queue_guard.add_song(queue_item)
                btn = "加入大航海队列"
            else:
                await song_queue.add_song(queue_item)
                btn = "加入普通队列"
            await _feedback_and_update(text, btn, song)

        return True
    except Exception as e:
        await _feedback_and_update("点歌失败", f"搜索错误: {e}")
        return False
