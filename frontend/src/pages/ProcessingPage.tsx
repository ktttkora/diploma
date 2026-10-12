/**
 * Processing page.
 *
 * Polls the analysis status and shows progress, then redirects to the
 * results page when processing finishes.
 */

import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate, Link as RouterLink } from 'react-router-dom';
import {
  Container,
  Paper,
  Typography,
  Box,
  LinearProgress,
  Alert,
  Button,
  Stepper,
  Step,
  StepLabel,
  AppBar,
  Toolbar,
  IconButton,
  CircularProgress,
} from '@mui/material';
import { Logout, History } from '@mui/icons-material';
import { AxiosError } from 'axios';
import analysisService from '../services/analysisService';
import authService from '../services/authService';
import { usePolling } from '../hooks/usePolling';
import type { AnalysisStatusResponse, ApiError } from '../types';

const STAGES = [
  'Анализ ритма',
  'Извлечение кадров',
  'AI-анализ техники',
  'Генерация скриншотов',
];

/** Rough stage from elapsed time; the pipeline does not report per-step progress. */
function estimateStage(startedAt: number): number {
  const elapsed = (Date.now() - startedAt) / 1000;
  if (elapsed < 30) return 0;
  if (elapsed < 60) return 1;
  if (elapsed < 150) return 2;
  return 3;
}

export default function ProcessingPage() {
  const { analysisId } = useParams<{ analysisId: string }>();
  const navigate = useNavigate();
  const id = Number(analysisId);

  const [startedAt] = useState(() => Date.now());
  const [stage, setStage] = useState(0);
  const [fatalError, setFatalError] = useState('');

  const handleLogout = () => {
    authService.logout();
    navigate('/login');
  };

  const fetchStatus = useCallback(
    () => analysisService.getStatus(id),
    [id]
  );

  const { data, error, stop } = usePolling<AnalysisStatusResponse>(fetchStatus, {
    intervalMs: 3000,
    enabled: Number.isFinite(id),
    shouldStop: (status) =>
      status.status === 'completed' || status.status === 'failed',
    onError: (err) => {
      const axiosError = err as AxiosError<ApiError>;
      if (axiosError.response?.status === 404) {
        setFatalError('Анализ не найден');
      } else if (axiosError.response?.status === 401) {
        setFatalError('Сессия истекла, войдите заново');
      }
    },
  });

  // Advance the displayed stage while processing
  useEffect(() => {
    if (data?.status !== 'processing' && data?.status !== 'pending') {
      return;
    }
    const timer = window.setInterval(() => {
      setStage(estimateStage(startedAt));
    }, 2000);
    return () => window.clearInterval(timer);
  }, [data?.status, startedAt]);

  // Move to the results page once the analysis completes
  useEffect(() => {
    if (data?.status === 'completed') {
      stop();
      navigate(`/results/${id}`, { replace: true });
    }
  }, [data?.status, id, navigate, stop]);

  const isFailed = data?.status === 'failed';
  const message = fatalError || (isFailed ? data?.error_message : '') || '';
  const elapsed = Math.round((Date.now() - startedAt) / 1000);

  return (
    <>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            Hustl Analyzer
          </Typography>
          <IconButton
            color="inherit"
            component={RouterLink}
            to="/history"
            title="История"
          >
            <History />
          </IconButton>
          <IconButton color="inherit" onClick={handleLogout} title="Выйти">
            <Logout />
          </IconButton>
        </Toolbar>
      </AppBar>

      <Container maxWidth="md">
        <Box sx={{ mt: 4 }}>
          {message ? (
            <>
              <Alert severity="error" sx={{ mb: 3 }}>
                <Typography variant="subtitle1" gutterBottom>
                  Не удалось обработать видео
                </Typography>
                <Typography variant="body2">{message}</Typography>
              </Alert>
              <Button variant="contained" onClick={() => navigate('/upload')}>
                Загрузить другое видео
              </Button>
            </>
          ) : (
            <>
              <Typography variant="h4" gutterBottom>
                Анализ видео
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
                Обработка занимает 3-5 минут. Можно оставить страницу открытой.
              </Typography>

              <Paper elevation={2} sx={{ p: 4 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
                  <CircularProgress size={28} />
                  <Typography variant="h6">
                    {STAGES[stage]}...
                  </Typography>
                </Box>

                <LinearProgress
                  variant="determinate"
                  value={((stage + 1) / STAGES.length) * 100}
                  sx={{ mb: 3, height: 8, borderRadius: 4 }}
                />

                <Stepper activeStep={stage} alternativeLabel>
                  {STAGES.map((label) => (
                    <Step key={label}>
                      <StepLabel>{label}</StepLabel>
                    </Step>
                  ))}
                </Stepper>

                <Typography
                  variant="caption"
                  color="text.secondary"
                  display="block"
                  sx={{ mt: 3 }}
                >
                  Прошло: {elapsed} с
                  {data ? ` · найдено ошибок: ${data.total_errors}` : ''}
                </Typography>
              </Paper>

              {error ? (
                <Alert severity="warning" sx={{ mt: 3 }}>
                  Не удалось получить статус. Повторяем попытки...
                </Alert>
              ) : null}
            </>
          )}
        </Box>
      </Container>
    </>
  );
}
