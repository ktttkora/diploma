/**
 * TypeScript types mirroring the backend API schemas.
 */

export interface User {
  id: number;
  email: string;
  display_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface ScoreAverages {
  overall: number | null;
  rhythm: number | null;
  posture: number | null;
  technique: number | null;
  music: number | null;
}

export interface FrequentError {
  error_type: string;
  count: number;
}

export interface ProgressPoint {
  analysis_id: number;
  completed_at: string | null;
  overall_score: number | null;
  rhythm_score: number | null;
  posture_score: number | null;
  technique_score: number | null;
  music_score: number | null;
}

export interface UserStats {
  saved_analyses: number;
  average_scores: ScoreAverages;
  top_errors: FrequentError[];
  progress: ProgressPoint[];
}

export interface RegisterRequest {
  email: string;
  password: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}

/** Analysis lifecycle, matching the backend AnalysisStatus enum values. */
export type AnalysisStatus = 'pending' | 'processing' | 'completed' | 'failed';

/** Error severity, matching the backend ErrorSeverity enum values. */
export type ErrorSeverity = 'low' | 'medium' | 'high' | 'critical';

/** Who the analysis should critique. */
export type AnalysisSubject = 'female' | 'male' | 'both';

export const SUBJECT_LABEL: Record<AnalysisSubject, string> = {
  female: 'Девушка',
  male: 'Мужчина',
  both: 'Оба партнёра',
};

export interface Video {
  id: number;
  user_id: number;
  filename: string;
  file_size: number;
  duration: number;
  fps: number;
  is_saved: boolean;
  uploaded_at: string;
  saved_at: string | null;
}

export interface VideoUploadResponse {
  video: Video;
  analysis_id: number;
  status: AnalysisStatus;
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
  person: 'female' | 'male' | null;
}

export interface Analysis {
  id: number;
  video_id: number;
  status: AnalysisStatus;
  subject: AnalysisSubject | null;
  overall_score: number | null;
  rhythm_score: number | null;
  posture_score: number | null;
  technique_score: number | null;
  music_score: number | null;
  total_errors: number;
  processing_time: number | null;
  error_message: string | null;
  started_at: string;
  completed_at: string | null;
  filename?: string | null;
  preview_error_id?: number | null;
  errors?: AnalysisError[];
}

export interface AnalysisStatusResponse {
  id: number;
  status: AnalysisStatus;
  total_errors: number;
  overall_score: number | null;
  error_message: string | null;
}

export interface AnalysisListResponse {
  analyses: Analysis[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface SaveAnalysisResponse {
  message: string;
  analysis_id: number;
  video_id: number;
  is_saved: boolean;
}

export interface ApiError {
  detail: string;
}
