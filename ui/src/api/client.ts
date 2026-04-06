import axios from 'axios';

export const apiClient = axios.create({
  baseURL: '',
  withCredentials: true,
});

apiClient.interceptors.request.use((config) => {
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      try {
        const resp = await axios.post('/api/v1/auth/refresh');
        const newToken = resp.data.access_token;
        error.config.headers['Authorization'] = `Bearer ${newToken}`;
        return axios(error.config);
      } catch {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);
