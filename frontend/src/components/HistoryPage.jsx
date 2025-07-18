import React from 'react';

const HistoryPage = ({ danmaku, requests }) => {
  return (
    <div>
      <h1>历史记录</h1>
      <div className="history-columns-container">
        <div className="bordered-column">
          <h2>弹幕</h2>
          <div className="scrollable-list">
            <ul className="list-group">
            {danmaku.map((item, index) => (
              <li key={index} className="list-group-item d-flex align-items-center">
                <img src={item.face} alt="user face" width="40" height="40" className="me-3 rounded-circle" referrerPolicy="no-referrer" />
                <div>
                  <strong>{item.uname}</strong>
                  <div>{item.msg}</div>
                  <small className="text-muted">{new Date(item.timestamp).toLocaleString()}</small>
                </div>
              </li>
            ))}
          </ul>
          </div>
        </div>
        <div className="bordered-column">
          <h2>点歌请求</h2>
          <div className="scrollable-list">
            <ul className="list-group">
            {requests.map((item, index) => (
              <li key={index} className="list-group-item d-flex align-items-center">
                <img src={item.face} alt="" width="50" height="50" className="me-3" referrerPolicy='no-referrer'/>
                <div>
                  <strong>{item.message}</strong>
                  <div>{item.user}</div>
                  <small className="text-muted">{new Date(item.timestamp).toLocaleString()}</small>
                </div>
              </li>
            ))}
          </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HistoryPage;