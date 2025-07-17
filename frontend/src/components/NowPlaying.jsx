import React from 'react';

const NowPlaying = ({ song }) => {
  if (!song) {
    return (
      <div className="card">
        <div className="card-body">
          <h5 className="card-title">Nothing is playing</h5>
        </div>
      </div>
    );
  }

  return (
    <div className="card">
      <img src={song.album.images[0].url} className="card-img-top" alt={song.name} />
      <div className="card-body">
        <h5 className="card-title">{song.name}</h5>
        <p className="card-text">{song.artists.map(artist => artist.name).join(', ')}</p>
      </div>
    </div>
  );
};

export default NowPlaying;
