/**
 * Analysis service: polling, results, save/discard, screenshots.
 */

import api from './api';
import type {
  Analysis,
  AnalysisListResponse,
  AnalysisStatusResponse,
  SaveAnalysisResponse,
  AnalysisError,
} from '../types';

interface ErrorListResponse {
  errors: AnalysisError[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export const analysisService = {
  /**
   * List the current user's analyses.
   */
  async list(page = 1, pageSize = 20, savedOnly = false): Promise<AnalysisListResponse> {
    const response = await api.get<AnalysisListResponse>('/api/analyses/', {
      params: { page, page_size: pageSize, saved_only: savedOnly },
    });
    return response.data;
  },

  /**
   * Get a single analysis with its errors.
   */
  async get(analysisId: number): Promise<Analysis> {
    const response = await api.get<Analysis>(`/api/analyses/${analysisId}`);
    return response.data;
  },

  /**
   * Get lightweight status, used while polling.
   */
  async getStatus(analysisId: number): Promise<AnalysisStatusResponse> {
    const response = await api.get<AnalysisStatusResponse>(
      `/api/analyses/${analysisId}/status`
    );
    return response.data;
  },

  /**
   * Get a paginated list of errors for an analysis.
   */
  async getErrors(
    analysisId: number,
    page = 1,
    pageSize = 50
  ): Promise<ErrorListResponse> {
    const response = await api.get<ErrorListResponse>(
      `/api/analyses/${analysisId}/errors`,
      { params: { page, page_size: pageSize } }
    );
    return response.data;
  },

  /**
   * Save an analysis permanently (keeps the video file).
   */
  async save(analysisId: number): Promise<SaveAnalysisResponse> {
    const response = await api.post<SaveAnalysisResponse>(
      `/api/analyses/${analysisId}/save`
    );
    return response.data;
  },

  /**
   * Discard an analysis and delete its video and screenshots.
   */
  async discard(analysisId: number): Promise<SaveAnalysisResponse> {
    const response = await api.delete<SaveAnalysisResponse>(
      `/api/analyses/${analysisId}`
    );
    return response.data;
  },

  /**
   * Fetch an error screenshot as a blob URL.
   *
   * Screenshots sit behind an authenticated endpoint, so they cannot be
   * used directly as an <img src>. Callers must revoke the URL when done.
   */
  async fetchScreenshot(analysisId: number, errorId: number): Promise<string> {
    const response = await api.get(
      `/api/analyses/${analysisId}/errors/${errorId}/screenshot`,
      { responseType: 'blob' }
    );
    return URL.createObjectURL(response.data);
  },
};

export default analysisService;
