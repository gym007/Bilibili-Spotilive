import { useEffect, useState, useRef } from 'react';
import io from 'socket.io-client';
import './assets/index.css';
import './assets/Rainbow.css';

const socket = io('http://localhost:5001');
const defaultCover = './images/Spotify.png'; // 默认封面图片

export default function App() {
  const [queueText, setQueueText] = useState({
    queue1: '目前无点歌',
    queue2: '发送：点歌 + 歌名 即可点歌'
  });

  const [theme, setTheme] = useState({
    background: '#000000',
    titleColor: '#ffffff',
    artistColor: '#aaaaaa',
    timeColor: '#ffffff',
    progressColor: '#1db954'
  });

  const [cover, setCover] = useState(defaultCover);

  useEffect(() => {
    socket.on('playlist_update', (data) => {
      console.log('Received playlist update:', data);
      if (data && data.length > 0) {
        setCover(data[0].albumCover);
        updateDisplayText('playlist', data);
      } else {
        setCover(defaultCover);
        updateDisplayText('playlist', []);
      }
    });

    socket.on('message_update', (data) => {
      console.log('Received message update:', data);
      if (data.result !== '没有找到匹配歌曲' && data.albumCover) {
        setCover(data.albumCover);
      }
      updateDisplayText('message', data);
    });
  }, []);

  const updateDisplayText = (type, data) => {
    if (type === 'message') {
      const queue1 = data.message || '目前无点歌';
      const queue2 = data.result || '发送：点歌 + 歌名 即可点歌';
      setQueueText({ queue1, queue2 });
    } else if (type === 'playlist') {
      const now = data[0];
      const next = data[1];
      const queue1 = now ? `列队1: ${now.name}` : '目前无点歌';
      const queue2 = next ? `列队2: ${next.name}` : '发送：点歌 + 歌名 即可点歌';
      setQueueText({ queue1, queue2 });
    }
  };

  // 每当封面变更时提取颜色
  useEffect(() => {
    if (!cover) return;

    Vibrant.from(cover).getPalette()
      .then(palette => {
        setTheme({
          background: palette.DarkMuted?.getHex() || '#111111',
          titleColor: palette.LightVibrant?.getHex() || '#ffffff',
          artistColor: palette.LightMuted?.getHex() || '#aaaaaa',
          timeColor: palette.LightVibrant?.getHex() || '#ffffff',
          progressColor: palette.Vibrant?.getHex() || '#1db954'
        });
      })
      .catch(error => {
        console.error("调色板提取失败：", error);
        setTheme({
          background: '#111111',
          titleColor: '#ffffff',
          artistColor: '#aaaaaa',
          timeColor: '#ffffff',
          progressColor: '#1db954'
        });
      });
  }, [cover]);

  return (
    <div className="wrapper">
      <div
        id="root"
        className="container playing"
        style={{ backgroundColor: theme.background }}
      >
        <div className="cover">
          <img
            className="img"
            src={cover}
            alt="专辑封面"
            crossOrigin="anonymous"
          />
        </div>
        <div className="main hide-progress-bar scrolling">
          <ScrollingText
            text={queueText.queue1}
            color={theme.titleColor}
            extraClass="name"
          />
          <ScrollingText
            text={queueText.queue2}
            color={theme.artistColor}
            extraClass="artist"
          />
        </div>
      </div>
    </div>
  );
}

function ScrollingText({ text, color, extraClass = '' }) {
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
