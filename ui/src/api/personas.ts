import { apiClient } from './client';

interface Persona {
  id: string;
  name: string;
  system_prompt: string;
  tone: string;
  niche: string;
  language: string;
  vocab_level: string;
  emoji_usage: string;
  hashtag_strategy: string;
  reply_probability: number;
  like_probability: number;
  follow_back_probability: number;
  created_at: string;
}

interface PersonaCreate {
  name: string;
  system_prompt: string;
  tone?: string;
  niche?: string;
  language?: string;
  vocab_level?: string;
  emoji_usage?: string;
  hashtag_strategy?: string;
  reply_probability?: number;
  like_probability?: number;
  follow_back_probability?: number;
}

export const personasApi = {
  async list(): Promise<Persona[]> {
    const response = await apiClient.get('/api/v1/personas/');
    return response.data;
  },

  async get(id: string): Promise<Persona> {
    const response = await apiClient.get(`/api/v1/personas/${id}`);
    return response.data;
  },

  async create(data: PersonaCreate): Promise<Persona> {
    const response = await apiClient.post('/api/v1/personas/', data);
    return response.data;
  },

  async update(id: string, data: Partial<PersonaCreate>): Promise<Persona> {
    const response = await apiClient.put(`/api/v1/personas/${id}`, data);
    return response.data;
  },

  async delete(id: string): Promise<void> {
    await apiClient.delete(`/api/v1/personas/${id}`);
  },
};
