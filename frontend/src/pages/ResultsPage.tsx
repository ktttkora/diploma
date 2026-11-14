/**
 * Results page.
 *
 * Shows the video, the scores, and the list of detected errors, and lets
 * the user save the analysis or discard it.
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import { useParams, useNavigate, Link as RouterLink } from 'react-router-dom';
import {
  Container,
  Box,
  Typography,
  Button,
  Alert,
  CircularProgress,
  Paper,
  Stack,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Snackbar,
} from '@mui/material';
import { CloudUpload, Delete } from '@mui/icons-material';
import { AxiosError } from 'axios';
import Header from '../components/Header';
import analysisService from '../services/analysisService';
import ScoresSummary from '../components/ScoresSummary';
import ErrorsList, { PersonFilter } from '../components/ErrorsList';
import VideoPlayer, { VideoPlayerHandle } from '../components/VideoPlayer';
import type { Analysis, ApiError } from '../types';
import { SUBJECT_LABEL } from '../types';

export default function ResultsPage() {
  const { analysisId } = useParams<{ analysisId: string }>();
  const navigate = useNavigate();
  const id = Number(analysisId);

  const playerRef = useRef<VideoPlayerHandle>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [actionError, setActionError] = useState('');
  const [saving, setSaving] = useState(false);
  const [confirmDiscard, setConfirmDiscard] = useState(false);
  const [toast, setToast] = useState('');
  const [personFilter, setPersonFilter] = useState<PersonFilter>('all');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await analysisService.get(id);
      setAnalysis(data);
      setLoadError('');
    } catch (err) {
      const axiosError = err as AxiosError<ApiError>;
      if (axiosError.response?.status === 404) {
        setLoadError('Анализ не найден');
      } else if (axiosError.response?.status === 401) {
        setLoadError('Сессия истекла, войдите заново');
      } else {
        setLoadError(
          axiosError.response?.data?.detail || 'Не удалось загрузить результат'
        );
      }
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    setPersonFilter('all');
    if (Number.isFinite(id)) {
      void load();
    }
  }, [id, load]);

  const handleSave = async () => {
    setSaving(true);
    setActionError('');
    try {
      await analysisService.save(id);
      setToast('Результат сохранён в историю');
      await load();
    } catch (err) {
      const axiosError = err as AxiosError<ApiError>;
      setActionError(
        axiosError.response?.data?.detail || 'Не удалось сохранить результат'
      );
    } finally {
      setSaving(false);
    }
  };

  const handleDiscard = async () => {
    setConfirmDiscard(false);
    setSaving(true);
    setActionError('');
    try {
      await analysisService.discard(id);
      navigate('/upload', { replace: true });
    } catch (err) {
      const axiosError = err as AxiosError<ApiError>;
      setActionError(
        axiosError.response?.data?.detail || 'Не удалось удалить результат'
      );
      setSaving(false);
    }
  };

  const seekTo = (timestamp: number) => {
    playerRef.current?.seekTo(timestamp);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const header = <Header />;

  if (loading) {
    return (
      <>
        {header}
        <Container maxWidth="md">
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 8 }}>
            <CircularProgress />
          </Box>
        </Container>
      </>
    );
  }

  if (loadError || !analysis) {
    return (
      <>
        {header}
        <Container maxWidth="md">
          <Box sx={{ mt: 4 }}>
            <Alert severity="error" sx={{ mb: 3 }}>
              {loadError || 'Анализ недоступен'}
            </Alert>
            <Button variant="contained" onClick={() => navigate('/upload')}>
              Загрузить видео
            </Button>
          </Box>
        </Container>
      </>
    );
  }

  const errors = analysis.errors ?? [];
  const videoErrors =
    personFilter === 'all'
      ? errors
      : errors.filter((error) => error.person === personFilter);

  return (
    <>
      {header}

      <Container maxWidth="lg">
        <Box sx={{ mt: 4, mb: 6 }}>
          <Typography variant="h4" gutterBottom>
            Результат анализа
          </Typography>
          {analysis.subject ? (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Кого разбирали: {SUBJECT_LABEL[analysis.subject]}
            </Typography>
          ) : null}

          {analysis.error_message ? (
            <Alert severity="warning" sx={{ mb: 3 }}>
              {analysis.error_message}
            </Alert>
          ) : null}

          {actionError ? (
            <Alert severity="error" sx={{ mb: 3 }}>
              {actionError}
            </Alert>
          ) : null}

          <Stack direction={{ xs: 'column', md: 'row' }} spacing={3}>
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <VideoPlayer
                ref={playerRef}
                videoId={analysis.video_id}
                errors={videoErrors}
              />

              <Box sx={{ mt: 3 }}>
                <ErrorsList
                  errors={errors}
                  analysisId={analysis.id}
                  onSeek={seekTo}
                  subject={analysis.subject}
                  personFilter={personFilter}
                  onPersonFilterChange={setPersonFilter}
                />
              </Box>
            </Box>

            <Box sx={{ width: { xs: '100%', md: 340 }, flexShrink: 0 }}>
              <ScoresSummary analysis={analysis} />

              <Paper elevation={2} sx={{ p: 2, mt: 3 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Что дальше?
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {analysis.video_id
                    ? 'Сохраните результат, чтобы вернуться к нему позже, или удалите видео.'
                    : ''}
                </Typography>

                <Stack spacing={1}>
                  <Button
                    variant="contained"
                    startIcon={<CloudUpload />}
                    onClick={handleSave}
                    disabled={saving}
                    fullWidth
                  >
                    Сохранить в историю
                  </Button>
                  <Button
                    variant="outlined"
                    color="error"
                    startIcon={<Delete />}
                    onClick={() => setConfirmDiscard(true)}
                    disabled={saving}
                    fullWidth
                  >
                    Удалить видео
                  </Button>
                  <Button
                    component={RouterLink}
                    to="/upload"
                    disabled={saving}
                    fullWidth
                  >
                    Загрузить ещё
                  </Button>
                </Stack>
              </Paper>
            </Box>
          </Stack>
        </Box>
      </Container>

      <Dialog open={confirmDiscard} onClose={() => setConfirmDiscard(false)}>
        <DialogTitle>Удалить результат?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Видео и все скриншоты будут удалены без возможности восстановления.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmDiscard(false)}>Отмена</Button>
          <Button onClick={handleDiscard} color="error" variant="contained">
            Удалить
          </Button>
        </DialogActions>
      </Dialog>

      <Snackbar
        open={Boolean(toast)}
        autoHideDuration={3000}
        onClose={() => setToast('')}
        message={toast}
      />
    </>
  );
}
