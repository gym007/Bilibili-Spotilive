import React, { useState, useEffect } from 'react';
import { HashRouter as Router, Routes, Route } from 'react-router-dom';
import './App.css';
import Sidebar from './components/Sidebar';
import QueuePage from './components/QueuePage';
import ConfigPage from './components/ConfigPage';
import HistoryPage from './components/HistoryPage';
import SearchPage from './components/SearchPage';
import {
  getConfig,
  getQueue,
  deleteQueueItem,
  reorderQueue,
  searchTrack,
  socket,
  addSongToQueue,
  playSong
} from './api';

function App() {
  // State for all pages
  const [config, setConfig] = useState(null);
  const [queues, setQueues] = useState({ streamer: [], guard: [], normal: [] });
  const [requests, setRequests] = useState([]);
  const [danmakuHistory, setDanmakuHistory] = useState([]);
  const [searchResults, setSearchResults] = useState([]);
  const [error, setError] = useState({ config: null, queue: null, search: null });
  const [toast, setToast] = useState({ message: '', type: '' }); // For toast notifications

  // Function to show toast messages
  const showToast = (message, type) => {
    setToast({ message, type });
    setTimeout(() => setToast({ message: '', type: '' }), 3000); // Hide after 3 seconds
  };

  // Queue type localization map
  const queueTypeMap = {
    streamer: '主播队列',
    guard: '大航海队列',
    normal: '普通队列',
  };

  // Theme state
  const [theme, setTheme] = useState('light');

  // Toggle theme function
  const toggleTheme = () => {
    setTheme(prevTheme => (prevTheme === 'light' ? 'dark' : 'light'));
  };

  // Apply theme class to body
  useEffect(() => {
    document.body.className = theme + '-mode';
  }, [theme]);

  // --- Data Fetching and Socket Listeners ---
  
  // Fetch initial config
  useEffect(() => {
    getConfig()
      .then(response => setConfig(response.data))
      .catch(err => {
        console.error("Error fetching config:", err);
        setError(prev => ({ ...prev, config: '获取配置失败' }));
      });
  }, []);

  // Fetch initial queues
  const fetchQueues = () => {
    Promise.all([
      getQueue('streamer'),
      getQueue('guard'),
      getQueue('normal')
    ]).then(([streamerRes, guardRes, normalRes]) => {
      const parseQueue = (res) => res.data?.queue || [];
      
      setQueues({
        streamer: parseQueue(streamerRes),
        guard: parseQueue(guardRes),
        normal: parseQueue(normalRes),
      });
    }).catch(err => {
      console.error("Error fetching queues:", err);
      // setError(prev => ({ ...prev, queue: '获取队列失败' }));
    });
  };

  // Poll for queue updates
  useEffect(() => {
    fetchQueues(); // Initial fetch
    const interval = setInterval(fetchQueues, 1000); // Poll every second
    return () => clearInterval(interval); // Cleanup
  }, []);

  // Listen for history updates
  useEffect(() => {
    const handleMessage = (data) => {
      if (data.albumCover && !data.albumCover.includes('Spotify.png')) {
        const requestWithTimestamp = { ...data, timestamp: Date.now() };
        setRequests(prev => [requestWithTimestamp, ...prev]);
      } else {
        setDanmaku(prev => [data, ...prev]);
      }
    };
    socket.on('message_update', handleMessage);
    return () => socket.off('message_update', handleMessage);
  }, []);

  useEffect(() => {
    const handleDanmaku = (data) => {
      setDanmakuHistory(prev => [data, ...prev]);
    };
    socket.on('danmaku_update', handleDanmaku);
    return () => socket.off('danmaku_update', handleDanmaku);
  }, []);

  // Listen for real-time queue updates from the backend
  useEffect(() => {
    const handlePlaylistUpdate = (data) => {
      console.log("Playlist update received via Socket.IO:", data);
      // The backend sends the entire new playlist structure
      // It might be nested under a 'playlist' or 'queues' key depending on backend implementation
      const updatedQueues = data.queues || data; // Adapt to backend structure
      setQueues({
        streamer: updatedQueues.streamer || [],
        guard: updatedQueues.guard || [],
        normal: updatedQueues.normal || [],
      });
    };
    socket.on('playlist_update', handlePlaylistUpdate);
    return () => socket.off('playlist_update', handlePlaylistUpdate);
  }, []);


  // --- Handler Functions ---

  const handleSearch = (query, limit) => {
    searchTrack(query, limit)
      .then(response => {
        let data = response.data;
        if (typeof data === 'string') data = JSON.parse(data);
        setSearchResults(Array.isArray(data) ? data : [data]);
      })
      .catch(err => {
        console.error("Error searching tracks:", err);
        setError(prev => ({ ...prev, search: '搜索失败' }));
        setSearchResults([]);
      });
  };

  const handleAddToQueue = (queueType, song) => {
    addSongToQueue(queueType, song)
      .then(() => {
        console.log(`Added to ${queueType} queue: ${song.name}`);
        showToast(`已将 ${song.name} 添加到 ${queueTypeMap[queueType]}`, 'success');
      })
      .catch(err => {
        console.error("Error adding song to queue:", err);
        setError(prev => ({ ...prev, queue: '添加歌曲失败' }));
        showToast(`添加歌曲失败: ${err.message}`, 'error');
      });
  };

  const handleDelete = (queueType, index) => {
    // Just send the command to the backend.
    // The UI will update automatically via the 'playlist_update' socket event.
    deleteQueueItem(queueType, index)
      .then(() => {
        showToast(`已从 ${queueTypeMap[queueType]} 删除歌曲`, 'success');
      })
      .catch(err => {
        console.error("Error deleting item:", err);
        setError(prev => ({ ...prev, queue: '删除歌曲失败' }));
        showToast(`删除歌曲失败: ${err.message}`, 'error');
      });
  };

  const handleDragEnd = (result) => {
    const { source, destination } = result;
    if (!destination) return;

    const sourceQueueId = source.droppableId;
    const destQueueId = destination.droppableId;

    // Create a temporary new state to send to the backend
    const sourceQueue = [...queues[sourceQueueId]];
    const destQueue = sourceQueueId === destQueueId ? sourceQueue : [...queues[destQueueId]];
    const [removed] = sourceQueue.splice(source.index, 1);
    destQueue.splice(destination.index, 0, removed);

    // Just send the command to the backend.
    // The UI will update automatically via the 'playlist_update' socket event.
    reorderQueue(destQueueId, destQueue).then(() => {
      showToast(`已更新 ${queueTypeMap[destQueueId]}`, 'success');
    }).catch(err => {
      console.error("Error reordering queue:", err);
      setError(prev => ({ ...prev, queue: '重排队列失败' }));
      showToast(`重排队列失败: ${err.message}`, 'error');
    });
    // If moved between queues, update the source queue as well
    if (sourceQueueId !== destQueueId) {
      reorderQueue(sourceQueueId, sourceQueue).then(() => {
        showToast(`已更新 ${queueTypeMap[sourceQueueId]}`, 'success');
      }).catch(err => {
        console.error("Error reordering source queue:", err);
        setError(prev => ({ ...prev, queue: '重排队列失败' }));
        showToast(`重排队列失败: ${err.message}`, 'error');
      });
    }
  };

  const handlePlayNow = (song, queueType = null, index = null) => {
    playSong(song)
      .then(() => {
        console.log(`Playing now: ${song.name}`);
        showToast(`正在播放: ${song.name}`, 'success');
        // If queueType and index are provided, delete the song from the queue
        if (queueType !== null && index !== null) {
          deleteQueueItem(queueType, index)
            .then(() => {
              console.log(`Deleted from ${queueType} queue: ${song.name}`);
            })
            .catch(err => {
              console.error("Error deleting item after playing:", err);
              setError(prev => ({ ...prev, queue: '播放后删除歌曲失败' }));
              showToast(`播放后删除歌曲失败: ${err.message}`, 'error');
            });
        }
      })
      .catch(err => {
        console.error("Error playing song:", err);
        setError(prev => ({ ...prev, spotify: '播放歌曲失败，请确保 Spotify 客户端已打开并有活跃设备。' }));
        showToast(`播放歌曲失败: ${err.message || '请确保 Spotify 客户端已打开并有活跃设备。'}`, 'error');
      });
  };

  return (
    <Router>
      <div className="app-container">
        <Sidebar theme={theme} toggleTheme={toggleTheme} />
        <div className="content-container">
          <main className="main-content">
            <Routes>
              <Route path="/" element={<ConfigPage config={config} error={error.config} />} />
              <Route path="/history" element={<HistoryPage danmaku={danmakuHistory} requests={requests} />} />
              <Route path="/search" element={<SearchPage results={searchResults} error={error.search} onSearch={handleSearch} onAddToQueue={handleAddToQueue} onPlayNow={handlePlayNow} />} />
              <Route path="/queue" element={<QueuePage queues={queues} error={error.queue} onDelete={handleDelete} onDragEnd={handleDragEnd} onPlayNow={handlePlayNow} queueTypeMap={queueTypeMap} />} />
            </Routes>
          </main>
          {toast.message && (
            <div className={`toast-notification ${toast.type} ${toast.message ? 'show' : ''}`}>
              {toast.message}
            </div>
          )}
        </div>
      </div>
    </Router>
  );
}

export default App;