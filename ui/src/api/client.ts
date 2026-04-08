import axios, { AxiosError, AxiosHeaders, InternalAxiosRequestConfig } from 'axios';

const ACCESS_TOKEN_KEY = 'token';
const REFRESH_TOKEN_KEY = 'refresh_token';

function isBrowser(): boolean {
  return typeof window !== 'undefined';
}

export function getStoredAccessToken(): string | null {
  if (!isBrowser()) return null;
  return window.localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getStoredRefreshToken(): string | null {
  if (!isBrowser()) return null;
  return window.localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function persistAccessToken(token: string | null): void {
  if (!isBrowser()) return;
  if (token) {
    window.localStorage.setItem(ACCESS_TOKEN_KEY, token);
  } else {
    window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  }
}

export function persistRefreshToken(token: string | null): void {
  if (!isBrowser()) return;
  if (token) {
    window.localStorage.setItem(REFRESH_TOKEN_KEY, token);
  } else {
    window.localStorage.removeItem(REFRESH_TOKEN_KEY);
  }
}

export function clearStoredAuth(): void {
  persistAccessToken(null);
  persistRefreshToken(null);
}

function redirectToLogin(): void {
  if (!isBrowser()) return;
  if (window.location.pathname !== '/login') {
    window.location.href = '/login';
  }
}

export const apiClient = axios.create({
  baseURL: '',
  withCredentials: true,
});

const initialAccessToken = getStoredAccessToken();
if (initialAccessToken) {
  apiClient.defaults.headers.common.Authorization = `Bearer ${initialAccessToken}`;
}

apiClient.interceptors.request.use((config) => {
  const token = getStoredAccessToken();
  if (token) {
    const headers = AxiosHeaders.from(config.headers ?? {});
    headers.set('Authorization', `Bearer ${token}`);
    config.headers = headers;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined;
    const requestUrl = originalRequest?.url ?? '';
    const isAuthRequest = requestUrl.includes('/api/v1/auth/token') || requestUrl.includes('/api/v1/auth/refresh');

    if (error.response?.status === 401 && originalRequest && !originalRequest._retry && !isAuthRequest) {
      const refreshToken = getStoredRefreshToken();
      if (!refreshToken) {
        clearStoredAuth();
        redirectToLogin();
        return Promise.reject(error);
      }

      originalRequest._retry = true;

      try {
        const resp = await axios.post('/api/v1/auth/refresh', {
          refresh_token: refreshToken,
        });
        const newToken = (resp.data as { access_token: string }).access_token;

        persistAccessToken(newToken);
        apiClient.defaults.headers.common.Authorization = `Bearer ${newToken}`;
        const headers = AxiosHeaders.from(originalRequest.headers ?? {});
        headers.set('Authorization', `Bearer ${newToken}`);
        originalRequest.headers = headers;

        return apiClient(originalRequest);
      } catch (refreshError) {
        clearStoredAuth();
        redirectToLogin();
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);
