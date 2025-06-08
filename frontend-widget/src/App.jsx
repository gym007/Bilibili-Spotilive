import { useEffect, useState, useRef } from 'react';
import io from 'socket.io-client';
import './assets/index.css';
import './assets/Rainbow.css';

const socket = io('http://localhost:5000');
const defaultCover = '/images/Spotify.png';

export default function App() {
  const [queueText, setQueueText] = useState({
    queue1: '目前无点歌',
    queue2: '发送：点歌 + 歌名 即可点歌'
  });
  const [theme, setTheme] = useState({
    background: '#000000',
    titleColor: '#ffffff',
    artistColor: '#aaaaaa'
  });
  const [cover, setCover] = useState(defaultCover);

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

  const extractColors = () => {
    const albumImg = document.querySelector(".cover img");
    if (!window.Vibrant || !albumImg) return;

    window.Vibrant.from(albumImg).getPalette()
      .then(palette => {
        const background = palette.DarkMuted?.getHex() || '#111111';
        const titleColor = palette.LightVibrant?.getHex() || '#ffccff';
        const artistColor = palette.LightMuted?.getHex() || '#66ffff';

        setTheme({ background, titleColor, artistColor });
      })
      .catch(error => {
        console.error("调色板提取失败：", error);
        setTheme({
          background: '#111111',
          titleColor: '#ffccff',
          artistColor: '#66ffff'
        });
      });
  };

  useEffect(() => {
    socket.on('playlist_update', (data) => {
      if (data && data.length > 0) {
        setCover(data[0].albumCover);
        updateDisplayText('playlist', data);
      } else {
        setCover(defaultCover);
        updateDisplayText('playlist', []);
      }
    });

    socket.on('message_update', (data) => {
      if (data.result !== '没有找到匹配歌曲' && data.albumCover) {
        setCover(data.albumCover);
      }
      updateDisplayText('message', data);
    });
  }, []);

  useEffect(() => {
    if (!cover) return;

    const img = document.querySelector(".cover img");
    if (img && img.complete) {
      extractColors();
    } else if (img) {
      img.onload = () => {
        extractColors();
      };
    }
  }, [cover]);

  return (
    <div className="wrapper">
      <div
        id="root"
        className="container background-muted background-darkmuted playing"
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
        <div className="main hide-progress-bar">
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
      <ul id="playlist"></ul>
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
    }, 5000);

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
