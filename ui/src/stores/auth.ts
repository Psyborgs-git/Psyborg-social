import { create } from 'zustand';
import {
  apiClient,
  clearStoredAuth,
  getStoredAccessToken,
  getStoredRefreshToken,
  persistAccessToken,
  persistRefreshToken,
} from '../api/client';

const initialToken = getStoredAccessToken();
const initialRefreshToken = getStoredRefreshToken();
const initialUsername = typeof window !== 'undefined' ? window.localStorage.getItem('username') : null;

if (initialToken) {
  apiClient.defaults.headers.common.Authorization = `Bearer ${initialToken}`;
}

interface AuthStore {
  token: string | null;
  refreshToken: string | null;
  user: { id?: string; username?: string } | null;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  setToken: (token: string | null) => void;
}

export const useAuthStore = create<AuthStore>((set) => ({
  token: initialToken,
  refreshToken: initialRefreshToken,
  user: initialUsername ? { username: initialUsername } : null,
  isAuthenticated: !!initialToken,
  login: async (username, password) => {
    const params = new URLSearchParams();
    params.append('username', username);
    params.append('password', password);

    const resp = await apiClient.post('/api/v1/auth/token', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });

    const token = resp.data.access_token as string;
    const refreshToken = (resp.data.refresh_token as string | undefined) ?? null;

    persistAccessToken(token);
    persistRefreshToken(refreshToken);
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('username', username);
    }

    apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    set({ token, refreshToken, user: { username }, isAuthenticated: true });
  },
  logout: () => {
    delete apiClient.defaults.headers.common['Authorization'];
    clearStoredAuth();
    if (typeof window !== 'undefined') {
      window.localStorage.removeItem('username');
    }
    set({ token: null, refreshToken: null, user: null, isAuthenticated: false });
  },
  setToken: (token) => {
    persistAccessToken(token);
    if (token) {
      apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
      delete apiClient.defaults.headers.common['Authorization'];
    }

    set((state) => ({
      token,
      isAuthenticated: !!token,
      user: token ? state.user : null,
    }));
  },
}));
