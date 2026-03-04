import api from './api';
import { SignupRequest, SigninRequest, AuthResponse } from '@/types/auth.types';

export const authService = {
  signup: async (data: SignupRequest): Promise<AuthResponse> => {
    const response = await api.post<AuthResponse>('/auth/signup', data);
    return response.data;
  },

  signin: async (data: SigninRequest): Promise<AuthResponse> => {
    const response = await api.post<AuthResponse>('/auth/signin', data);
    return response.data;
  },
};
