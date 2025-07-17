import React from 'react';

const Queue = ({ songs }) => {
  return (
    <ul className="list-group">
      {songs.length === 0 ? (
        <li className="list-group-item">Queue is empty.</li>
      ) : (
        songs.map((item, index) => (
          <li key={item.song.id || index} className="list-group-item d-flex justify-content-between align-items-center">
            <div>
              <strong>{item.song.name}</strong>
              <br />
              <small>{item.song.artists.map(artist => artist.name).join(', ')}</small>
            </div>
            {item.song.album && item.song.album.images && item.song.album.images[2] && (
              <img src={item.song.album.images[2].url} alt={item.song.name} height="40" />
            )}
          </li>
        ))
      )}
    </ul>
  );
};

export default Queue;