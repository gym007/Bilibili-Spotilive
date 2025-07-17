import axios from 'axios';
import io from 'socket.io-client';

const API_URL = 'http://localhost:5001';

export const getConfig = () => {
  return axios.get(`${API_URL}/api/config`);
};

export const getQueue = (queueType) => {
  return axios.get(`${API_URL}/api/queue/${queueType}`);
};

export const reorderQueue = (queueType, queue) => {
  return axios.post(`${API_URL}/api/queue/${queueType}/reorder`, { queue });
};

export const deleteQueueItem = (queueType, index) => {
  return axios.delete(`${API_URL}/api/queue/${queueType}/delete/${index}`);
};

export const searchTrack = (query, limit) => {
  return axios.get(`${API_URL}/api/spotify/search`, { params: { q: query, limit } });
};

export const addSongToQueue = (queueType, song) => {
  return axios.post(`${API_URL}/api/queue/${queueType}/add`, { song });
};

export const playSong = (song) => {
  return axios.post(`${API_URL}/api/spotify/playsong`, { song });
};

export const socket = io(API_URL);
