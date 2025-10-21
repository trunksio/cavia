import axios from 'axios';

// In production (Docker), use nginx proxy. In dev, use direct backend URL
const API_BASE_URL = import.meta.env.VITE_API_URL || '';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for debugging
api.interceptors.request.use(
  (config) => {
    console.log('API Request:', config.method.toUpperCase(), config.url);
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

/**
 * CV Upload and Management
 */
export const uploadCV = async (file, onProgress) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/api/v1/cvs/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent) => {
      if (onProgress) {
        const percentCompleted = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total
        );
        onProgress(percentCompleted);
      }
    },
  });

  return response.data;
};

export const downloadCV = async (jobId) => {
  const response = await api.get(`/api/v1/cvs/${jobId}/download`, {
    responseType: 'blob',
  });
  return response.data;
};

/**
 * Job Status and Results
 */
export const listJobs = async (params = {}) => {
  const { status, limit = 50, offset = 0 } = params;
  const queryParams = new URLSearchParams();

  if (status) queryParams.append('status', status);
  queryParams.append('limit', limit);
  queryParams.append('offset', offset);

  const response = await api.get(`/api/v1/jobs?${queryParams.toString()}`);
  return response.data;
};

export const getJobStatus = async (jobId) => {
  const response = await api.get(`/api/v1/jobs/${jobId}/status`);
  return response.data;
};

export const getJobResult = async (jobId) => {
  const response = await api.get(`/api/v1/jobs/${jobId}/result`);
  return response.data;
};

export const downloadReport = async (jobId) => {
  const response = await api.get(`/api/v1/jobs/${jobId}/report/download`, {
    responseType: 'blob',
  });
  return response.data;
};

/**
 * Health Check
 */
export const healthCheck = async () => {
  const response = await api.get('/health');
  return response.data;
};

export default api;
