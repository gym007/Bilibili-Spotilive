import React, { useState } from 'react';

const SearchPage = ({ results, error, onSearch, onAddToQueue, onPlayNow }) => {
  const [query, setQuery] = useState('');
  const [limit, setLimit] = useState(5);

  const handleSearch = () => {
    if (query.trim()) {
      onSearch(query, limit);
    }
  };

  const handleKeyDown = (event) => {
    if (event.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <div>
      <h1>搜索</h1>
      <div className="input-group mb-3">
        <input
          type="text"
          className="form-control"
          placeholder="搜索歌曲"
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <input
          type="number"
          className="form-control"
          value={limit}
          onChange={e => setLimit(e.target.value)}
        />
        <button className="btn btn-primary" type="button" onClick={handleSearch}>
          搜索
        </button>
      </div>

      {error && <div className="alert alert-danger">{error}</div>}

      <ul className="list-group">
        {results.map(track => (
          <li key={track.id} className="list-group-item d-flex align-items-center">
            <img src={track.album.images[0]?.url} alt="album cover" width="50" height="50" className="me-3" />
            <div>
              <strong>{track.name}</strong>
              <br />
              {track.artists.map(artist => artist.name).join(', ')}
            </div>
            <div className="ms-auto">
              <button className="btn btn-success btn-sm me-2" onClick={() => onAddToQueue('streamer', track)}>
                主播队列
              </button>
              <button className="btn btn-info btn-sm me-2" onClick={() => onAddToQueue('guard', track)}>
                大航海队列
              </button>
              <button className="btn btn-secondary btn-sm" onClick={() => onAddToQueue('normal', track)}>
                普通队列
              </button>
              <button className="btn btn-primary btn-sm ms-2" onClick={() => onPlayNow(track)}>
                立即播放
              </button>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default SearchPage;