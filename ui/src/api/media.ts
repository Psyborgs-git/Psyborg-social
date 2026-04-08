import { apiClient } from './client';

interface MediaAsset {
  id: string;
  filename: string;
  media_type: string;
  file_size_bytes?: number;
  mime_type?: string;
  width?: number;
  height?: number;
  duration_seconds?: number;
  storage_key: string;
  storage_bucket: string;
  created_at: string;
}

export const mediaApi = {
  async list(): Promise<MediaAsset[]> {
    const response = await apiClient.get('/api/v1/media/');
    return response.data;
  },

  async get(id: string): Promise<MediaAsset> {
    const response = await apiClient.get(`/api/v1/media/${id}`);
    return response.data;
  },

  async upload(file: File): Promise<MediaAsset> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post('/api/v1/media/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  async delete(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/media/${id}`);
  },

  async download(id: string, filename: string): Promise<Blob> {
    const response = await apiClient.get(`/api/v1/media/${id}/download`, {
      params: { filename },
      responseType: 'blob',
    });
    return response.data as Blob;
  },

  getDownloadUrl(id: string, filename: string): string {
    return `/api/v1/media/${id}/download?filename=${encodeURIComponent(filename)}`;
  },
};
