import { apiClient } from './client';
import { Account } from '../types/api';

export const accountsApi = {
  list: (params?: { platform?: string; status?: string }) =>
    apiClient.get<Account[]>('/api/v1/accounts/', { params }).then(r => r.data),
  get: (id: string) => apiClient.get<Account>(`/api/v1/accounts/${id}`).then(r => r.data),
  create: (data: { platform: string; username: string; password: string; proxy_url?: string }) =>
    apiClient.post<Account>('/api/v1/accounts/', data).then(r => r.data),
  update: (id: string, data: Partial<Account>) =>
    apiClient.patch<Account>(`/api/v1/accounts/${id}`, data).then(r => r.data),
  delete: (id: string) => apiClient.delete(`/api/v1/accounts/${id}`),
  pause: (id: string, reason?: string) =>
    apiClient.post(`/api/v1/accounts/${id}/pause`, { reason }),
  resume: (id: string) => apiClient.post(`/api/v1/accounts/${id}/resume`),
  getPosts: (id: string) => apiClient.get(`/api/v1/accounts/${id}/posts`).then(r => r.data),
  getRateLimits: (id: string) => apiClient.get(`/api/v1/accounts/${id}/rate-limits`).then(r => r.data),
};
