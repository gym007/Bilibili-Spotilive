# spotify_controller.py
import asyncio
import random
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from log_timer import timestamp

class SpotifyController:
    def __init__(self, client_id, client_secret, redirect_uri, scope, default_playlist=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scope = scope
        self.default_playlist = default_playlist

        self.sp_oauth = SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope=self.scope
        )
        self.sp = Spotify(auth_manager=self.sp_oauth)

    def _search_song(self, song_name):
        try:
            query = f"track:{song_name}"
            results = self.sp.search(q=song_name, type='track', limit=5)
            tracks = results.get('tracks', {}).get('items', [])
            if tracks:
                for track in tracks:
                    if song_name.lower() in track['name'].lower():
                        return track
                return tracks[0]  # 没有明显匹配 返回第一个匹配的歌曲
            return None  # 没有找到匹配的歌曲
        except Exception as e:
            print(f"[ERROR] 搜索歌曲出错: {e}")
            return None

    async def search_song(self, song_name: str):
        # 包装为异步函数调用
        return await asyncio.to_thread(self._search_song, song_name)

    def _play_song(self, track):
        try:
            uri = track['uri']
            name = track['name']
            artist = track['artists'][0]['name']
            print(f"[播放] ▶️ 正在播放: {name} - {artist}")
            self.sp.start_playback(uris=[uri])
        except Exception as e:
            print(f"[ERROR] 播放歌曲出错: {e}")

    async def play_song(self, track: dict):
        await asyncio.to_thread(self._play_song, track)

    def _next_song(self):
        try:
            print("[下一首] ▶️ 播放下一首歌曲")
            self.sp.next_track()
        except Exception as e:
            print(f"[ERROR] 播放下一首歌曲出错: {e}")
    
    async def next_song(self):
        await asyncio.to_thread(self._next_song)

    def _restore_default_playlist(self):
        """
        从默认歌单中随机选择一首歌曲播放
        """
        try:
            if not self.default_playlist:
                print("[恢复默认] 默认歌单未设置。")
                return

            # 获取默认歌单信息
            playlist = self.sp.playlist(self.default_playlist)
            total = playlist['tracks']['total']
            if total <= 0:
                print("[恢复默认] 默认歌单为空。")
                return

            random_index = random.randint(0, total - 1)
            print(f"[恢复默认] 恢复默认歌单，从随机位置 {random_index} 开始播放。")
            # 开启随机播放，从指定偏移量开始
            self.sp.start_playback(context_uri=self.default_playlist, offset={"position": random_index})
        except Exception as e:
            print(f"[ERROR] 恢复默认歌单出错: {e}")

    async def restore_default_playlist(self):
        await asyncio.to_thread(self._restore_default_playlist)