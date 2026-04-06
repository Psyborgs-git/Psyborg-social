import { apiClient } from './client';
import { AnalyticsSummary } from '../types/api';

export const analyticsApi = {
  getSummary: () => apiClient.get<AnalyticsSummary>('/api/v1/analytics/summary').then(r => r.data),
  getEngagement: (params?: { period?: string; account_id?: string }) =>
    apiClient.get('/api/v1/analytics/engagement', { params }).then(r => r.data),
  getPlatformBreakdown: () =>
    apiClient.get('/api/v1/analytics/platforms').then(r => r.data),
};
