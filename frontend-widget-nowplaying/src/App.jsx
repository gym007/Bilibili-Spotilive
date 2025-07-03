import { useEffect, useState, useRef } from 'react';
import io from 'socket.io-client';
import './assets/index.css';
import './assets/Rainbow.css';

const socket = io('http://localhost:5001'); // 根据你的后端端口调整

export default function App() {
  const [playback, setPlayback] = useState(null);
  const [theme, setTheme] = useState({
    background: '#111',
    titleColor: '#fff',
    artistColor: '#ccc'
  });

  const imgRef = useRef();

  // Socket 连接和播放信息监听
  useEffect(() => {
    socket.on('connect', () => {
      console.log('[Socket] 已连接');
    });

    socket.on('nowplaying_update', (data) => {
      console.log('[Socket] 收到 nowplaying_update:', data);
      setPlayback(data);
    });

    socket.on('disconnect', () => {
      console.log('[Socket] 已断开连接');
    });
  }, []);

  // 提取颜色
  useEffect(() => {
    const url = playback?.item?.album?.images?.[0]?.url;
    if (!url) return;

    Vibrant.from(url).getPalette()
      .then(p => {
        setTheme({
          background: p.DarkMuted?.getHex() || '#111',
          titleColor: p.LightVibrant?.getHex() || '#fff',
          artistColor: p.LightMuted?.getHex() || '#ccc',
          timeColor: p.LightVibrant?.getHex() || '#fff',
          progressColor: p.Vibrant?.getHex() || '#1db954'
        });
      })
      .catch(err => {
        console.error('颜色提取失败:', err);
        setTheme({
          background: '#111',
          titleColor: '#fff',
          artistColor: '#ccc'
        });
      });
  }, [playback?.item?.album?.images]);

  // 页面未就绪时提示
  if (!playback || !playback.item) {
    return (
      <div style={{ color: '#fff', fontSize: '24px', padding: '20px' }}>
        {/* 正在等待播放信息... */}
      </div>
    );
  }

  const { is_playing, progress_ms, item } = playback;
  const duration_ms = item.duration_ms;
  const progressRatio = duration_ms ? progress_ms / duration_ms : 0;

  const trackName = item.name;
  const artistName = item.artists.map(a => a.name).join(', ');
  const coverUrl = item.album.images[1]?.url || item.album.images[0]?.url;

  const formatTime = (ms) => {
    const minutes = Math.floor(ms / 60000);
    const seconds = Math.floor((ms % 60000) / 1000).toString().padStart(2, '0');
    return `${minutes}:${seconds}`;
  };

  return (
    <div className="wrapper">
      <div
        id="root"
        className={`container ${
          playback && is_playing === false
            ? 'closed'
            : playback && is_playing
            ? 'playing'
            : 'closed'
        }`}
        style={{ backgroundColor: theme.background }}
      >
        <div className="cover">
          <img ref={imgRef} src={coverUrl} alt="封面" crossOrigin="anonymous" />
        </div>

        <div className="main show-progress-bar scrolling">
          <ScrollingText text={trackName} color={theme.titleColor} extraClass="name" />
          <ScrollingText text={artistName} color={theme.artistColor} extraClass="artist" />

          <div className="progress-container show">
            <div className="time-left" style={{ color: theme.timeColor }}>
              {formatTime(progress_ms)}
            </div>
            <div className="progress-bar">
              <div className="progress" style={{ width: `${progressRatio * 100}%`, background: theme.progressColor }}></div>
            </div>
            <div className="time" style={{ color: theme.timeColor }}>
              {formatTime(duration_ms)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// 跑马灯文字组件
function ScrollingText({ text, color, extraClass }) {
  const wrapperRef = useRef();
  const textRef = useRef();
  const scrollRef = useRef();

  useEffect(() => {
    const el = textRef.current;
    const wrapper = wrapperRef.current;
    if (!el || !wrapper) return;

    cancelAnimationFrame(scrollRef.current);
    el.style.transform = 'translateX(0)';

    const needsScroll = el.scrollWidth > wrapper.offsetWidth;
    if (!needsScroll) return;

    let offset = 0;
    let dir = -1;

    const scroll = () => {
      offset += dir;
      el.style.transform = `translateX(${offset}px)`;
      if (offset <= -el.scrollWidth) dir = 1;
      if (offset >= wrapper.offsetWidth) dir = -1;
      scrollRef.current = requestAnimationFrame(scroll);
    };

    const delayTimer = setTimeout(() => {
      scrollRef.current = requestAnimationFrame(scroll);
    }, 3000);

    return () => {
      clearTimeout(delayTimer);
      cancelAnimationFrame(scrollRef.current);
    };
  }, [text]);

  return (
    <div ref={wrapperRef} className={`scroll-wrapper ${extraClass}`}>
      <div
        ref={textRef}
        className="scroll-text"
        style={{ color }}
      >
        {text}
      </div>
    </div>
  );
}
