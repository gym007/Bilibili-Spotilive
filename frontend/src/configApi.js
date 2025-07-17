import axios from 'axios';

const CONFIG_API_URL = 'http://localhost:5002/api';

export const getConfig = () => axios.get(`${CONFIG_API_URL}/config`);
export const saveConfig = (config) => axios.post(`${CONFIG_API_URL}/config`, config);

export const getStatus = () => axios.get(`${CONFIG_API_URL}/status`);
export const startMachine = () => axios.post(`${CONFIG_API_URL}/status/start`);
export const stopMachine = () => axios.post(`${CONFIG_API_URL}/status/stop`);
