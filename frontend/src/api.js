import axios from 'axios';

const API_BASE = 'http://127.0.0.1:8000/api';

export const api = {
    chat: async (question) => {
        const response = await axios.post(`${API_BASE}/chat`, { question });
        return response.data;
    },
    
    getSources: async () => {
        const response = await axios.get(`${API_BASE}/sources`);
        return response.data;
    },

    getGraphTriplets: async (limit = 2000) => {
        const response = await axios.get(`${API_BASE}/graph/triplets`, {
            params: { limit }
        });
        return response.data;
    },
    
    getMemory: async () => {
        const response = await axios.get(`${API_BASE}/memory`);
        return response.data;
    },
    
    setMemory: async (preferences) => {
        const response = await axios.post(`${API_BASE}/memory`, { preferences });
        return response.data;
    },
    
    uploadFiles: async (files) => {
        const formData = new FormData();
        Array.from(files).forEach(file => {
            formData.append('files', file);
        });
        
        const response = await axios.post(`${API_BASE}/ingest/upload`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        });
        return response.data;
    },

    ingestUrl: async (url) => {
        const response = await axios.post(`${API_BASE}/ingest/url`, { url });
        return response.data;
    },

    getInsights: async () => {
        const response = await axios.get(`${API_BASE}/insights/weekly`);
        return response.data;
    },

    getChunk: async (chunkId) => {
        const response = await axios.get(`${API_BASE}/chunk/${chunkId}`);
        return response.data;
    }
};
