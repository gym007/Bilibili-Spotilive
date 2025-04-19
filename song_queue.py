# song_queue.py
import asyncio
from log_timer import timestamp

class SongQueue:
    def __init__(self, room_id=None):
        # 使用 asyncio.Queue 实现异步队列
        self._queue = asyncio.Queue()
        self.room_id = room_id

    async def add_song(self, song: dict, request_uid, role) -> None:
        """
        将一首歌曲添加到队列中。

        参数:
            song: 包含歌曲信息的字典，例如 {'name': 'Song Name', 'artists': [{'name': 'Artist Name'}, ...]}。
            request_uid: 提交请求的用户 UID。
        """
        await self._queue.put({"song": song, "request_uid": request_uid})
        #print(f"{song}")
        song_name = song.get('name', 'Unknown')
        artist_names = ', '.join(artist.get('name', 'Unknown') for artist in song.get('artists', []))
        song_info = f"{song_name} - {artist_names if artist_names else 'Unknown'}"
        print(f"[{self.room_id}]{timestamp()}[队列] 点歌成功，加入{role}队列： '{song_info}' ")

    async def get_next_song(self) -> dict:
        """
        从队列中获取下一首歌曲并删除。

        返回:
            包含 'song' 和 'request_uid' 键的字典，如果队列为空则返回 None。
        """
        if self._queue.empty():
            return None
        item = await self._queue.get()
        song = item['song']
        uid = item['request_uid']
        song_name = song.get('name', 'Unknown')
        artist_names = ', '.join(artist.get('name', 'Unknown') for artist in song.get('artists', []))
        #print(f"[{self.room_id}]{timestamp()}[队列] 播放下一首：'{song_name} - {artist_names}'，请求者 UID: {uid}")
        return item

    def is_empty(self) -> bool:
        """
        检查队列是否为空。

        返回:
            True 表示队列为空，否则为 False。
        """
        return self._queue.empty()

    def qsize(self) -> int:
        """
        返回队列中待播项的数量。
        """
        return self._queue.qsize()

    async def list_songs(self) -> list:
        """
        返回当前队列中所有待播项，每项为包含 'song' 和 'request_uid' 的字典。
        注意：仅供调试使用。
        """
        return list(self._queue._queue)

    def clear(self) -> None:
        """
        清空队列。
        """
        while not self._queue.empty():
            self._queue.get_nowait()
        print(f"[{self.room_id}]{timestamp()}[队列] 已清空所有待播歌曲。")
