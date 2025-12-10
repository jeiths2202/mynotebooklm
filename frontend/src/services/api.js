import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Notebooks API
export const notebooksAPI = {
  list: () => api.get('/notebooks'),

  create: (name) => api.post('/notebooks', { name }),

  get: (notebookId) => api.get(`/notebooks/${notebookId}`),

  update: (notebookId, name) => api.patch(`/notebooks/${notebookId}`, { name }),

  delete: (notebookId) => api.delete(`/notebooks/${notebookId}`),
};

// Documents API
export const documentsAPI = {
  list: (notebookId) => api.get(`/notebooks/${notebookId}/documents`),

  upload: (notebookId, file, onProgress) => {
    const formData = new FormData();
    formData.append('file', file);

    return api.post(`/notebooks/${notebookId}/documents`, formData, {
      // Let Axios set the correct Content-Type with boundary for multipart
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percent);
        }
      },
    });
  },

  get: (documentId) => api.get(`/documents/${documentId}`),

  delete: (documentId) => api.delete(`/documents/${documentId}`),
};

// Chat API
export const chatAPI = {
  query: (notebookId, query) =>
    api.post(`/notebooks/${notebookId}/chat`, { query }),
};

export default api;
