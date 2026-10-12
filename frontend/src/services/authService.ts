/**
 * Authentication service.
 *
 * Handles register, login, logout, and current user retrieval.
 */

import api from './api';
import type { User, LoginResponse, RegisterRequest, LoginRequest } from '../types';

const TOKEN_KEY = 'access_token';

export const authService = {
  /**
   * Register a new user.
   */
  async register(data: RegisterRequest): Promise<User> {
    const response = await api.post<User>('/api/auth/register', data);
    return response.data;
  },

  /**
   * Login and store JWT token.
   */
  async login(data: LoginRequest): Promise<LoginResponse> {
    // OAuth2 expects form-urlencoded with 'username' field
    const formData = new URLSearchParams();
    formData.append('username', data.email);
    formData.append('password', data.password);

    const response = await api.post<LoginResponse>('/api/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });

    localStorage.setItem(TOKEN_KEY, response.data.access_token);
    return response.data;
  },

  /**
   * Get current authenticated user.
   */
  async getCurrentUser(): Promise<User> {
    const response = await api.get<User>('/api/users/me');
    return response.data;
  },

  /**
   * Update current user profile.
   */
  async updateProfile(data: { email?: string; password?: string }): Promise<User> {
    const response = await api.put<User>('/api/users/me', data);
    return response.data;
  },

  /**
   * Logout: remove token from storage.
   */
  logout(): void {
    localStorage.removeItem(TOKEN_KEY);
  },

  /**
   * Check if user is authenticated (token exists).
   */
  isAuthenticated(): boolean {
    return !!localStorage.getItem(TOKEN_KEY);
  },

  /**
   * Get stored token.
   */
  getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  },
};

export default authService;
