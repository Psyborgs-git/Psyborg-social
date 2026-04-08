import { apiClient } from './client';
import { Task, TaskLog } from '../types/api';

export const tasksApi = {
  list: (params?: { account_id?: string; status?: string; limit?: number }) =>
    apiClient.get<Task[]>('/api/v1/tasks/', { params }).then(r => r.data),
  get: (id: string) => apiClient.get<Task>(`/api/v1/tasks/${id}`).then(r => r.data),
  create: (data: Partial<Task>) => apiClient.post<Task>('/api/v1/tasks/', data).then(r => r.data),
  cancel: (id: string) => apiClient.post<Task>(`/api/v1/tasks/${id}/cancel`).then(r => r.data),
  getLogs: (id: string) => apiClient.get<TaskLog[]>(`/api/v1/tasks/${id}/logs`).then(r => r.data),
};
