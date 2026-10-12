/**
 * Upload page.
 *
 * Drag-and-drop video upload with progress indicator.
 */

import { useState, ChangeEvent, DragEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Paper,
  Typography,
  Button,
  Box,
  Alert,
  LinearProgress,
  AppBar,
  Toolbar,
  IconButton,
} from '@mui/material';
import { CloudUpload, Logout } from '@mui/icons-material';
import { AxiosError } from 'axios';
import videoService from '../services/videoService';
import authService from '../services/authService';
import type { ApiError } from '../types';

export default function UploadPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState('');
  const [dragActive, setDragActive] = useState(false);

  const handleLogout = () => {
    authService.logout();
    navigate('/login');
  };

  const validateFile = (f: File): string | null => {
    if (!f.type.startsWith('video/')) {
      return 'Файл должен быть видео';
    }
    if (f.size > 1024 * 1024 * 1024) {
      return 'Файл слишком большой (максимум 1 ГБ)';
    }
    return null;
  };

  const handleFileSelect = (f: File) => {
    const validationError = validateFile(f);
    if (validationError) {
      setError(validationError);
      setFile(null);
      return;
    }
    setError('');
    setFile(f);
  };

  const handleInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0]);
    }
  };

  const handleDrag = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(e.type === 'dragenter' || e.type === 'dragover');
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setError('');

    try {
      const video = await videoService.upload(file, setProgress);
      navigate(`/processing/${video.id}`);
    } catch (err) {
      const axiosError = err as AxiosError<ApiError>;
      setError(axiosError.response?.data?.detail || 'Ошибка загрузки. Попробуйте позже.');
      setUploading(false);
    }
  };

  return (
    <>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            Hustl Analyzer
          </Typography>
          <IconButton color="inherit" onClick={handleLogout} title="Выйти">
            <Logout />
          </IconButton>
        </Toolbar>
      </AppBar>

      <Container maxWidth="md">
        <Box sx={{ mt: 4 }}>
          <Typography variant="h4" gutterBottom>
            Загрузка видео
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Загрузите видео танца хастл для анализа техники
          </Typography>

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          <Paper
            elevation={dragActive ? 8 : 2}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            sx={{
              p: 6,
              textAlign: 'center',
              border: '2px dashed',
              borderColor: dragActive ? 'primary.main' : 'grey.400',
              bgcolor: dragActive ? 'action.hover' : 'background.paper',
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
            onClick={() => document.getElementById('file-input')?.click()}
          >
            <CloudUpload sx={{ fontSize: 64, color: 'primary.main', mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              Перетащите видео сюда
            </Typography>
            <Typography variant="body2" color="text.secondary">
              или нажмите для выбора файла
            </Typography>
            <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
              MP4, AVI, MOV · до 10 минут · до 1 ГБ
            </Typography>
            <input
              id="file-input"
              type="file"
              accept="video/*"
              hidden
              onChange={handleInputChange}
            />
          </Paper>

          {file && (
            <Paper elevation={1} sx={{ p: 2, mt: 2 }}>
              <Typography variant="body1">
                <strong>Выбрано:</strong> {file.name}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Размер: {(file.size / (1024 * 1024)).toFixed(1)} МБ
              </Typography>
            </Paper>
          )}

          {uploading && (
            <Box sx={{ mt: 3 }}>
              <Typography variant="body2" gutterBottom>
                Загрузка: {progress}%
              </Typography>
              <LinearProgress variant="determinate" value={progress} />
            </Box>
          )}

          <Button
            fullWidth
            variant="contained"
            size="large"
            disabled={!file || uploading}
            onClick={handleUpload}
            sx={{ mt: 3 }}
          >
            {uploading ? 'Загрузка...' : 'Загрузить и проанализировать'}
          </Button>
        </Box>
      </Container>
    </>
  );
}
