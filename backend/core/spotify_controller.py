import asyncio
import random
import difflib
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from utils.log_timer import timestamp
from opencc import OpenCC
import requests

# 创建自定义 Session，加入 Accept-Language Header
session = requests.Session()
session.headers["Accept-Language"] = "zh-CN,zh;q=0.9"

def normalize_text(text: str) -> str:
    """
    将文本转换为简体，然后统一替换常见异体字。
    """
    t2s_converter = OpenCC('t2s')
    return t2s_converter.convert(text)

class SpotifyController:
    def __init__(self, config):
        spotify_config = config.get('spotify', {})
        self.client_id = spotify_config.get('client_id')
        self.client_secret = spotify_config.get('client_secret')
        self.redirect_uri = spotify_config.get('redirect_uri')
        self.scope = spotify_config.get('scope')
        self.default_playlist = spotify_config.get('default_playlist')
        self.room_id = config.get("bilibili", {}).get("room_id")

        self.sp_oauth = SpotifyOAuth(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            scope=self.scope
        )
        self.sp = Spotify(auth_manager=self.sp_oauth, requests_session=session)

    def _search_song(self, song_name, limit):
        try:
            query_normalized = normalize_text(song_name).lower()
            results = self.sp.search(q=song_name, type='track', limit=limit)
            tracks = results.get('tracks', {}).get('items', [])
            if not tracks:
                return None

            matching_tracks = [
                track for track in tracks
                if query_normalized in normalize_text(track.get('name', '')).lower()
            ]
            for track in matching_tracks:
                print(f"[{self.room_id}]{timestamp()}[SPOT] [搜索] 匹配歌曲: {track['name']} - {track['artists'][0]['name']} (popularity: {track.get('popularity', 'N/A')})")
            if matching_tracks:
                return max(matching_tracks, key=lambda t: t.get('popularity', 0))
                

            filtered_tracks = []
            for track in tracks:
                track_name = track.get('name', '')
                track_normalized = normalize_text(track_name).lower()
                similarity = difflib.SequenceMatcher(None, query_normalized, track_normalized).ratio()
                if similarity >= 0.5:
                    filtered_tracks.append((track, similarity))
            if filtered_tracks:
                filtered_tracks.sort(key=lambda t: (t[1], t[0].get('popularity', 0)), reverse=True)
                best_match = filtered_tracks[0][0]
                print(f"[{self.room_id}]{timestamp()}[SPOT] [搜索] 筛选后热度最高的歌曲: {best_match['name']} - {best_match['artists'][0]['name']} (similarity: {filtered_tracks[0][1]:.2f}, popularity: {best_match.get('popularity', 'N/A')})")
                return best_match
            return None
        except Exception as e:
            print(f"[{self.room_id}]{timestamp()}[SPOT] [ERROR] 搜索歌曲出错: {e}")
            return None

    async def search_song(self, song_name: str, limit: int = 3):
        return await asyncio.to_thread(self._search_song, song_name, limit)
    
    def _api_search_song(self, song_name: str, limit):
        """
        使用 API 搜索歌曲，返回结果为字典格式。
        """
        try:
            results = self.sp.search(q=song_name, type='track', limit=limit)
            tracks = results.get('tracks', {}).get('items', [])
            if not tracks:
                return None
            
            track_list = []
            for track in tracks:
                track_list.append(track)
            
            print(f"[{self.room_id}]{timestamp()}[SPOT] [API搜索] 找到 {len(track_list)} 首歌曲")
            return track_list
        except Exception as e:
            print(f"[{self.room_id}]{timestamp()}[SPOT] [ERROR] API 搜索歌曲出错: {e}")
            return None
        
    async def api_search_song(self, song_name: str, limit: int = 3):
        return await asyncio.to_thread(self._api_search_song, song_name, limit)
        

    def _play_song(self, track):
        try:
            uri = track['uri']
            name = track['name']
            artist = track['artists'][0]['name']
            print(f"[{self.room_id}]{timestamp()}[SPOT] [播放] ▶️ 正在播放: {name} - {artist}")
            self.sp.start_playback(uris=[uri])
        except Exception as e:
            error_msg = str(e)
            if "No active device found" in error_msg:
                print(f"[{self.room_id}]{timestamp()}[SPOT] [ERROR] 播放歌曲出错: 未检测到活跃的播放设备，请先在 Spotify 客户端播放任意歌曲后重试。")
            else:
                print(f"[{self.room_id}]{timestamp()}[SPOT] [ERROR] 播放歌曲出错: {error_msg}")

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
        try:
            if not self.default_playlist:
                print(f"[{self.room_id}]{timestamp()}[SPOT] [播放] 默认歌单未设置。")
                return
            playlist = self.sp.playlist(self.default_playlist)
            total = playlist['tracks']['total']
            if total <= 0:
                print(f"[{self.room_id}]{timestamp()}[SPOT] [播放] 默认歌单为空。")
                return
            random_index = random.randint(0, total - 1)
            print(f"[{self.room_id}]{timestamp()}[SPOT] [播放] ▶️ 播放默认歌单，从随机位置 {random_index} 开始播放。")
            self.sp.start_playback(context_uri=self.default_playlist, offset={"position": random_index})
        except Exception as e:
            error_msg = str(e)
            if "No active device found" in error_msg:
                print(f"[{self.room_id}]{timestamp()}[SPOT] [ERROR] 播放歌曲出错: 未检测到活跃的播放设备，请先在 Spotify 客户端播放任意歌曲后重试。")
            else:
                print(f"[{self.room_id}]{timestamp()}[SPOT] [ERROR] 播放歌曲出错: {error_msg}")

    async def restore_default_playlist(self):
        await asyncio.to_thread(self._restore_default_playlist)

    def _get_current_playback(self):
        try:
            return self.sp.currently_playing(market='HK') or None
        except Exception as e:
            print(f"[{self.room_id}]{timestamp()}[SPOT] [ERROR] 获取当前播放信息出错: {e}")
            return None

    async def get_current_playback(self):
        return await asyncio.to_thread(self._get_current_playback)
