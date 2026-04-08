import { apiClient } from './client';
import { Campaign } from '../types/api';

export const campaignsApi = {
  list: () => apiClient.get<Campaign[]>('/api/v1/campaigns/').then(r => r.data),
  get: (id: string) => apiClient.get<Campaign>(`/api/v1/campaigns/${id}`).then(r => r.data),
  create: (data: Partial<Campaign>) =>
    apiClient.post<Campaign>('/api/v1/campaigns/', data).then(r => r.data),
  update: (id: string, data: Partial<Campaign>) =>
    apiClient.patch<Campaign>(`/api/v1/campaigns/${id}`, data).then(r => r.data),
  delete: (id: string) => apiClient.delete(`/api/v1/campaigns/${id}`),
  activate: (id: string) => apiClient.post(`/api/v1/campaigns/${id}/resume`),
  deactivate: (id: string) => apiClient.post(`/api/v1/campaigns/${id}/pause`),
  addAccount: (campaignId: string, accountId: string) =>
    apiClient.post<Campaign>(`/api/v1/campaigns/${campaignId}/accounts/${accountId}`).then(r => r.data),
  removeAccount: (campaignId: string, accountId: string) =>
    apiClient.delete<Campaign>(`/api/v1/campaigns/${campaignId}/accounts/${accountId}`).then(r => r.data),
};
