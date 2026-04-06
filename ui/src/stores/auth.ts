import { create } from 'zustand';
import { User } from '../types/api';
import { apiClient } from '../api/client';

interface AuthStore {
  token: string | null;
  user: User | null;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  setToken: (token: string | null) => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  token: null,
  user: null,
  isAuthenticated: false,
  login: async (username, password) => {
    const resp = await apiClient.post('/api/v1/auth/token', { username, password });
    set({ token: resp.data.access_token, user: resp.data.user, isAuthenticated: true });
    apiClient.defaults.headers.common['Authorization'] = `Bearer ${resp.data.access_token}`;
  },
  logout: () => {
    delete apiClient.defaults.headers.common['Authorization'];
    set({ token: null, user: null, isAuthenticated: false });
  },
  setToken: (token) => set({ token, isAuthenticated: !!token }),
}));
