import React from 'react';
import { NavLink } from 'react-router-dom';

// Import SVG icons
import ConfigIcon from '../assets/icons/config.svg';
import HistoryIcon from '../assets/icons/history.svg';
import SearchIcon from '../assets/icons/search.svg';
import QueueIcon from '../assets/icons/queue.svg';
import MoonIcon from '../assets/icons/moon.svg';
import SunIcon from '../assets/icons/sun.svg';

const Sidebar = ({ theme, toggleTheme }) => {
  return (
    <div className="sidebar">
      <div className="sidebar-brand">
        <span>BiliBili Spotilive</span>
      </div>
      <hr />
      <ul className="nav-list">
        <li>
          <NavLink to="/" end>
            <img src={ConfigIcon} alt="Config" className="nav-icon" />
            <span>配置</span>
          </NavLink>
        </li>
        <li>
          <NavLink to="/history">
            <img src={HistoryIcon} alt="History" className="nav-icon" />
            <span>历史记录</span>
          </NavLink>
        </li>
        <li>
          <NavLink to="/search">
            <img src={SearchIcon} alt="Search" className="nav-icon" />
            <span>搜索</span>
          </NavLink>
        </li>
        <li>
          <NavLink to="/queue">
            <img src={QueueIcon} alt="Queue" className="nav-icon" />
            <span>队列</span>
          </NavLink>
        </li>
      </ul>
      <hr />
      <div className="theme-toggle-container">
        <button onClick={toggleTheme} className="theme-toggle-button">
          <img src={theme === 'light' ? MoonIcon : SunIcon} alt="Toggle Theme" className="theme-icon" />
          <span>{theme === 'light' ? '深色模式' : '浅色模式'}</span>
        </button>
      </div>
    </div>
  );
};

export default Sidebar;
