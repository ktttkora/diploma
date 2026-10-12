/**
 * TypeScript types for API entities.
 */

export interface User {
  id: number;
  email: string;
  created_at: string;
  updated_at: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export type AnalysisStatus = 'PENDING' | 'PROCESSING' | 'COMPLETED' | 'FAILED';
export type ErrorSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface Video {
  id: number;
  user_id: number;
  filename: string;
  file_path: string;
  file_size: number;
  duration: number;
  fps: number;
  is_saved: boolean;
  uploaded_at: string;
  saved_at: string | null;
}

export interface VideoListResponse {
  videos: Video[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface AnalysisError {
  id: number;
  analysis_id: number;
  element_name: string;
  timestamp: number;
  error_type: string;
  severity: ErrorSeverity;
  description: string;
  screenshot_path: string | null;
}

export interface Analysis {
  id: number;
  video_id: number;
  status: AnalysisStatus;
  overall_score: number | null;
  music_score: number | null;
  rhythm_score: number | null;
  started_at: string;
  completed_at: string | null;
  errors?: AnalysisError[];
}

export interface AnalysisListResponse {
  analyses: Analysis[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ApiError {
  detail: string;
}
