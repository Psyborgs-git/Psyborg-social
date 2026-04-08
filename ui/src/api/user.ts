import { apiClient } from './client';

export interface UserSettings {
  username: string;
  email?: string | null;
  notifications_enabled: boolean;
}

export const userApi = {
  getSettings: () => apiClient.get<UserSettings>('/api/v1/user/settings').then((r) => r.data),
  updateSettings: (data: Partial<UserSettings>) =>
    apiClient.put<UserSettings>('/api/v1/user/settings', data).then((r) => r.data),
  changePassword: (oldPassword: string, newPassword: string) =>
    apiClient.put('/api/v1/user/password', {
      old_password: oldPassword,
      new_password: newPassword,
    }),
};
