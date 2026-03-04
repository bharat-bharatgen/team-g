import { create } from 'zustand';
import { AuthState, User } from '@/types/auth.types';
import { STORAGE_KEYS } from '@/utils/constants';

export const useAuthStore = create<AuthState>((set) => ({
  user: (() => {
    const userData = localStorage.getItem(STORAGE_KEYS.USER_DATA);
    return userData ? JSON.parse(userData) : null;
  })(),
  token: localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN),
  isAuthenticated: !!localStorage.getItem(STORAGE_KEYS.AUTH_TOKEN),

  login: (token: string, user: User) => {
    localStorage.setItem(STORAGE_KEYS.AUTH_TOKEN, token);
    localStorage.setItem(STORAGE_KEYS.USER_DATA, JSON.stringify(user));
    set({ token, user, isAuthenticated: true });
  },

  logout: () => {
    localStorage.removeItem(STORAGE_KEYS.AUTH_TOKEN);
    localStorage.removeItem(STORAGE_KEYS.USER_DATA);
    set({ token: null, user: null, isAuthenticated: false });
  },

  setUser: (user: User) => {
    localStorage.setItem(STORAGE_KEYS.USER_DATA, JSON.stringify(user));
    set({ user });
  },
}));
