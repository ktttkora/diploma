/**
 * Video service.
 *
 * Handles upload, listing, retrieval, and deletion of videos.
 */

import api from './api';
import type { Video, VideoListResponse } from '../types';

export const videoService = {
  /**
   * Upload a video file.
   *
   * @param file Video file
   * @param onProgress Optional progress callback (0-100)
   */
  async upload(file: File, onProgress?: (percent: number) => void): Promise<Video> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post<Video>('/api/videos/', formData, {
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
   * List user's videos (paginated).
   */
  async list(page = 1, pageSize = 20): Promise<VideoListResponse> {
    const response = await api.get<VideoListResponse>('/api/videos/', {
      params: { page, page_size: pageSize },
    });
    return response.data;
  },

  /**
   * Get single video by ID.
   */
  async get(videoId: number): Promise<Video> {
    const response = await api.get<Video>(`/api/videos/${videoId}`);
    return response.data;
  },

  /**
   * Delete video and its files.
   */
  async delete(videoId: number): Promise<void> {
    await api.delete(`/api/videos/${videoId}`);
  },
};

export default videoService;
