# song_queue.py
import asyncio

class SongQueue:
    def __init__(self):
        # 使用 asyncio.Queue 实现异步队列
        self._queue = asyncio.Queue()

    async def add_song(self, song: dict) -> None:
        """
        将一首歌曲添加到队列中。

        参数:
            song: 包含歌曲信息的字典，例如 {'name': 'Song Name', 'artists': [{'name': 'Artist Name'}, ...]}。
        """
        await self._queue.put(song)
        song_info = f"{song.get('name', 'Unknown')} - {song.get('artists', [{'name': 'Unknown'}])[0].get('name', 'Unknown')}"
        print(f"[队列] 歌曲 '{song_info}' 已添加到队列中。")

    async def get_next_song(self) -> dict:
        """
        从队列中获取下一首歌曲并删除。

        返回:
            歌曲字典，如果队列为空则返回 None。
        """
        if self._queue.empty():
            return None
        song = await self._queue.get()
        return song

    def is_empty(self) -> bool:
        """
        检查队列是否为空。

        返回:
            True 表示队列为空，否则为 False。
        """
        return self._queue.empty()

    def qsize(self) -> int:
        """
        返回队列中待播歌曲的数量。
        """
        return self._queue.qsize()

    async def list_songs(self) -> list:
        """
        返回当前队列中所有歌曲的列表。
        注意：这直接访问内部 _queue（一个 deque 对象），仅适用于查看调试用途。
        """
        # 返回一个列表拷贝，防止直接修改内部队列
        return list(self._queue._queue)

    def clear(self) -> None:
        """
        清空队列。
        """
        while not self._queue.empty():
            self._queue.get_nowait()
        print("[队列] 已清空所有待播歌曲。")

# 测试代码：直接运行该模块可以进行简单测试
if __name__ == '__main__':
    async def test_song_queue():
        sq = SongQueue()
        # 定义两首测试歌曲
        track1 = {"name": "Song One", "artists": [{"name": "Artist A"}]}
        track2 = {"name": "Song Two", "artists": [{"name": "Artist B"}]}
        await sq.add_song(track1)
        await sq.add_song(track2)
        songs = await sq.list_songs()
        print("当前队列中的歌曲：", songs)
        next_song = await sq.get_next_song()
        print("获取下一首歌：", next_song)
        print("队列剩余数量：", sq.qsize())
        sq.clear()
        print("清空后，队列是否为空：", sq.is_empty())

    asyncio.run(test_song_queue())
