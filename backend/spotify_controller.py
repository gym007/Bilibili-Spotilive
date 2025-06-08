# spotify_controller.py
import asyncio
import random
import difflib
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from log_timer import timestamp
from opencc import OpenCC

def normalize_text(text: str) -> str:
    """
    将文本转换为简体，然后统一替换常见异体字。
    例如：把简体中的“漂”替换为“飘”
    """
    t2s_converter = OpenCC('t2s')
    simplified = t2s_converter.convert(text)
    normalized = simplified
    return normalized

class SpotifyController:
    def __init__(self, client_id, client_secret, redirect_uri, scope, default_playlist=None, room_id=None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scope = scope
        self.default_playlist = default_playlist
        self.room_id = room_id

        self.sp_oauth = SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope=self.scope
        )
        self.sp = Spotify(auth_manager=self.sp_oauth)

    def _search_song(self, song_name):
        try:
            # 先将用户输入的歌曲名称标准化并转为小写
            query_normalized = normalize_text(song_name).lower()
            
            # 使用 Spotify API 搜索候选结果（limit 可根据需要调整）
            results = self.sp.search(q=song_name, type='track', limit=3)
            tracks = results.get('tracks', {}).get('items', [])
            # print(f"[搜索] 返回的候选歌曲列表: {tracks}") debug print
            
            if tracks:
                matching_tracks = []
                # 遍历候选结果，将候选歌曲名称标准化后转为小写
                for track in tracks:
                    track_name = track.get('name', '')
                    track_normalized = normalize_text(track_name).lower()
                    # 使用 in 判断是否包含查询字符串（忽略大小写）
                    if query_normalized in track_normalized:
                        matching_tracks.append(track)
                        print(f"[{self.room_id}]{timestamp()}[SPOT] [搜索] 匹配歌曲: {track['name']} - {track['artists'][0]['name']} (popularity: {track.get('popularity', 'N/A')})")
                if matching_tracks:
                    # 返回匹配列表中热度最高的那首
                    selected = max(matching_tracks, key=lambda t: t.get('popularity', 0))
                    return selected
                else:
                    # 若没有直接匹配，采用相似度最高的策略
                    filtered_tracks = []
                    for track in tracks:
                        track_name = track.get('name', '')
                        track_normalized = normalize_text(track_name).lower()
                        similarity = difflib.SequenceMatcher(None, query_normalized, track_normalized).ratio()
                        if similarity >= 0.5:
                            filtered_tracks.append((track, similarity))
                    
                    if filtered_tracks:
                        # 按相似度和热度排序，优先选择热度最高的
                        filtered_tracks.sort(key=lambda t: (t[1], t[0].get('popularity', 0)), reverse=True)
                        best_match = filtered_tracks[0][0]
                        print(f"[{self.room_id}]{timestamp()}[SPOT] [搜索] 筛选后热度最高的歌曲: {best_match['name']} - {best_match['artists'][0]['name']} (similarity: {filtered_tracks[0][1]:.2f}, popularity: {best_match.get('popularity', 'N/A')})")
                        return best_match
            return None
        except Exception as e:
            print(f"[{self.room_id}]{timestamp()}[SPOT] [ERROR] 搜索歌曲出错: {e}")
            return None


    async def search_song(self, song_name: str):
        # 包装为异步函数调用
        return await asyncio.to_thread(self._search_song, song_name)

    def _play_song(self, track):
        try:
            uri = track['uri']
            name = track['name']
            artist = track['artists'][0]['name']
            print(f"[{self.room_id}]{timestamp()}[SPOT] [播放] ▶️ 正在播放: {name} - {artist}")
            self.sp.start_playback(uris=[uri])
        except Exception as e:
            print(f"[{self.room_id}]{timestamp()}[SPOT] [ERROR] 播放歌曲出错: {e}")

    async def play_song(self, track: dict):
        await asyncio.to_thread(self._play_song, track)

    def _next_song(self):
        try:
            print(f"[{self.room_id}]{timestamp()}[SPOT] [播放] ▶️ 播放下一首歌曲")
            self.sp.next_track()
        except Exception as e:
            print(f"[{self.room_id}]{timestamp()}[SPOT] [ERROR] 播放下一首歌曲出错: {e}")
    
    async def next_song(self):
        await asyncio.to_thread(self._next_song)

    def _restore_default_playlist(self):
        """
        从默认歌单中随机选择一首歌曲播放
        """
        try:
            if not self.default_playlist:
                print(f"[{self.room_id}]{timestamp()}[SPOT] [播放] 默认歌单未设置。")
                return

            # 获取默认歌单信息
            playlist = self.sp.playlist(self.default_playlist)
            total = playlist['tracks']['total']
            if total <= 0:
                print(f"[{self.room_id}]{timestamp()}[SPOT] [播放] 默认歌单为空。")
                return

            random_index = random.randint(0, total - 1)
            print(f"[{self.room_id}]{timestamp()}[SPOT] [播放] ▶️ 播放默认歌单，从随机位置 {random_index} 开始播放。")
            # 开启随机播放，从指定偏移量开始
            self.sp.start_playback(context_uri=self.default_playlist, offset={"position": random_index})
        except Exception as e:
            print(f"[{self.room_id}]{timestamp()}[SPOT] [ERROR] 恢复默认歌单出错: {e}")

    async def restore_default_playlist(self):
        await asyncio.to_thread(self._restore_default_playlist)