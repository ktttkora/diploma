/**
 * Analysis service.
 *
 * Handles retrieval of analysis results and errors.
 */

import api from './api';
import type { Analysis, AnalysisListResponse, AnalysisError } from '../types';

interface ErrorListResponse {
  errors: AnalysisError[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export const analysisService = {
  /**
   * List user's analyses (paginated).
   */
  async list(page = 1, pageSize = 20): Promise<AnalysisListResponse> {
    const response = await api.get<AnalysisListResponse>('/api/analyses/', {
      params: { page, page_size: pageSize },
    });
    return response.data;
  },

  /**
   * Get single analysis with errors.
   */
  async get(analysisId: number): Promise<Analysis> {
    const response = await api.get<Analysis>(`/api/analyses/${analysisId}`);
    return response.data;
  },

  /**
   * Get errors for an analysis (paginated).
   */
  async getErrors(analysisId: number, page = 1, pageSize = 20): Promise<ErrorListResponse> {
    const response = await api.get<ErrorListResponse>(
      `/api/analyses/${analysisId}/errors`,
      { params: { page, page_size: pageSize } }
    );
    return response.data;
  },

  /**
   * Delete an analysis.
   */
  async delete(analysisId: number): Promise<void> {
    await api.delete(`/api/analyses/${analysisId}`);
  },
};

export default analysisService;
