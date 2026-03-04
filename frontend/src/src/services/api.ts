import axios from 'axios';
import { API_BASE_URL, STORAGE_KEYS } from '@/utils/constants';

const REQUEST_TIMEOUT_MS = 4000;

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: REQUEST_TIMEOUT_MS,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor: retry once on timeout (stale connection), then 401 handling
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const isTimeout =
      error.code === 'ECONNABORTED' &&
      error.message?.toLowerCase().includes('timeout');
    const config = error.config as typeof error.config & { _retried?: boolean };

    if (isTimeout && config && !config._retried) {
      config._retried = true;
      config.headers = {
        ...config.headers,
        Connection: 'close',
      };
      return api.request(config);
    }

    if (error.response?.status === 401) {
      localStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN);
      localStorage.removeItem(STORAGE_KEYS.USER_DATA);
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Excel Upload Functions
export const uploadMERExcel = async (caseId: string, file: File) => {
  const formData = new FormData();
  formData.append('file', file);

  const token = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/mer/import-excel`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to upload Excel');
  }

  return await response.json();
};

export const uploadPathologyExcel = async (caseId: string, file: File) => {
  const formData = new FormData();
  formData.append('file', file);

  const token = localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN);
  const response = await fetch(`${API_BASE_URL}/cases/${caseId}/pathology/import-excel`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to upload Excel');
  }

  return await response.json();
};

export default api;
