/**
 * Video service: upload, listing, streaming, deletion.
 */

import api from './api';
import type { Video, VideoUploadResponse, VideoListResponse } from '../types';

export const videoService = {
  /**
   * Upload a video and queue its analysis.
   *
   * @param file Video file
   * @param onProgress Optional progress callback (0-100)
   */
  async upload(
    file: File,
    onProgress?: (percent: number) => void
  ): Promise<VideoUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post<VideoUploadResponse>('/api/videos/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (event) => {
        if (onProgress && event.total) {
          onProgress(Math.round((event.loaded * 100) / event.total));
        }
      },
    });

    return response.data;
  },

  /**
   * List the current user's videos.
   */
  async list(page = 1, pageSize = 20, savedOnly = false): Promise<VideoListResponse> {
    const response = await api.get<VideoListResponse>('/api/videos/', {
      params: { page, page_size: pageSize, saved_only: savedOnly },
    });
    return response.data;
  },

  /**
   * List the user's saved videos (analysis history).
   */
  async history(page = 1, pageSize = 20): Promise<VideoListResponse> {
    const response = await api.get<VideoListResponse>('/api/videos/history', {
      params: { page, page_size: pageSize },
    });
    return response.data;
  },

  /**
   * Get a single video.
   */
  async get(videoId: number): Promise<Video> {
    const response = await api.get<Video>(`/api/videos/${videoId}`);
    return response.data;
  },

  /**
   * Delete a video and everything derived from it.
   */
  async delete(videoId: number): Promise<void> {
    await api.delete(`/api/videos/${videoId}`);
  },

  /**
   * URL for streaming a video in a player.
   *
   * Served through the API with the Authorization header, so the caller
   * must fetch it with an authenticated request rather than a plain src.
   */
  streamUrl(videoId: number): string {
    return `${api.defaults.baseURL}/api/videos/${videoId}/stream`;
  },
};

export default videoService;
