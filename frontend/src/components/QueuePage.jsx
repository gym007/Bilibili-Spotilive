import React from 'react';
import { DragDropContext, Droppable, Draggable } from 'react-beautiful-dnd';
import './QueuePage.css';

const QueueColumn = ({ title, queue, droppableId, onDelete, onPlayNow }) => (
  <div className="bordered-column">
    <h2>{title}</h2>
    <Droppable droppableId={droppableId}>
      {(provided) => (
        <div className="scrollable-list" {...provided.droppableProps} ref={provided.innerRef}>
          {queue.length === 0 ? (
            <p className="text-muted text-center mt-3">当前队列空</p>
          ) : (
            <ul className="list-group">
            {queue.map((item, index) => (
            <Draggable key={`${item.song.uri}-${index}`} draggableId={`${item.song.uri}-${index}`} index={index}>
              {(provided) => (
                <li
                  className="list-group-item"
                  ref={provided.innerRef}
                  {...provided.draggableProps}
                  {...provided.dragHandleProps}
                >
                  <div className="song-info-container d-flex align-items-center">
                    <img src={item.song.album.images[0]?.url} alt="album cover" width="50" height="50" className="me-3" />
                    <div>
                      <strong>{item.song.name}</strong>
                      <br />
                      点歌人: {item.request.user.uname}
                    </div>
                  </div>
                  <div className="button-group-container d-flex justify-content-end mt-2">
                    <button className="btn btn-danger btn-sm me-2" onClick={() => onDelete(droppableId, index)}>
                      删除
                    </button>
                    <button className="btn btn-primary btn-sm" onClick={() => onPlayNow(item.song, droppableId, index)}>
                      立即播放
                    </button>
                  </div>
                </li>
              )}
            </Draggable>
          ))}
          {provided.placeholder}
        </ul>
          )}
        </div>
      )}
    </Droppable>
  </div>
);

const QueuePage = ({ queues, error, onDelete, onDragEnd, onPlayNow, queueTypeMap }) => {
  if (error) {
    return <div className="alert alert-danger">{error}</div>;
  }

  return (
    <div>
      <h1>歌曲队列</h1>
      <DragDropContext onDragEnd={onDragEnd}>
        <div className="queue-columns-container">
          <QueueColumn title={queueTypeMap.streamer} queue={queues.streamer} droppableId="streamer" onDelete={onDelete} onPlayNow={onPlayNow} />
          <QueueColumn title={queueTypeMap.guard} queue={queues.guard} droppableId="guard" onDelete={onDelete} onPlayNow={onPlayNow} />
          <QueueColumn title={queueTypeMap.normal} queue={queues.normal} droppableId="normal" onDelete={onDelete} onPlayNow={onPlayNow} />
        </div>
      </DragDropContext>
    </div>
  );
};

export default QueuePage;