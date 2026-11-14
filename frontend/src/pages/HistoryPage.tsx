/**
 * History page.
 *
 * Lists the user's saved analyses with their scores, and links to each
 * result. Saved analyses are the ones the user kept from the results page.
 */

import { useEffect, useState, useCallback } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import {
  Container,
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  Button,
  Alert,
  CircularProgress,
  TablePagination,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
} from '@mui/material';
import { ArrowForward, Delete } from '@mui/icons-material';
import { AxiosError } from 'axios';
import Header from '../components/Header';
import analysisService from '../services/analysisService';
import videoService from '../services/videoService';
import type { Analysis, ApiError } from '../types';
import { SUBJECT_LABEL } from '../types';

const PAGE_SIZE = 10;

/** Format an ISO timestamp as a local date and time. */
function formatDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/** Colour a score from red (low) through amber to green (high). */
function scoreColor(score: number | null): 'success.main' | 'warning.main' | 'error.main' | 'text.disabled' {
  if (score === null) return 'text.disabled';
  if (score >= 80) return 'success.main';
  if (score >= 60) return 'warning.main';
  return 'error.main';
}

/** Format a score for the compact category line. */
function shortScore(score: number | null): string {
  return score === null ? '—' : score.toFixed(0);
}

/** Small preview taken from the first error screenshot. */
function HistoryThumb({ analysis }: { analysis: Analysis }) {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!analysis.preview_error_id) return undefined;
    let objectUrl = '';
    let active = true;
    analysisService
      .fetchScreenshot(analysis.id, analysis.preview_error_id)
      .then((nextUrl) => {
        if (!active) {
          URL.revokeObjectURL(nextUrl);
          return;
        }
        objectUrl = nextUrl;
        setUrl(nextUrl);
      })
      .catch(() => {
        // A missing screenshot still leaves the row usable
      });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [analysis.id, analysis.preview_error_id]);

  if (!url) {
    return (
      <Box
        sx={{ width: 96, height: 54, borderRadius: 1, bgcolor: 'action.hover' }}
      />
    );
  }

  return (
    <Box
      component="img"
      src={url}
      alt=""
      sx={{ width: 96, height: 54, objectFit: 'cover', borderRadius: 1 }}
    />
  );
}

export default function HistoryPage() {
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [pendingDelete, setPendingDelete] = useState<Analysis | null>(null);
  const [deleting, setDeleting] = useState(false);

  const load = useCallback(async (pageIndex: number) => {
    setLoading(true);
    try {
      // Only analyses whose video was saved appear in the history
      const data = await analysisService.list(pageIndex + 1, PAGE_SIZE, true);
      setAnalyses(data.analyses);
      setTotal(data.total);
      setError('');
    } catch (err) {
      const axiosError = err as AxiosError<ApiError>;
      if (axiosError.response?.status === 401) {
        setError('Сессия истекла, войдите заново');
      } else {
        setError(
          axiosError.response?.data?.detail || 'Не удалось загрузить историю'
        );
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(page);
  }, [load, page]);

  const handleDelete = async () => {
    if (!pendingDelete) return;
    setDeleting(true);
    try {
      await videoService.delete(pendingDelete.video_id);
      setPendingDelete(null);
      const nextPage = analyses.length === 1 && page > 0 ? page - 1 : page;
      if (nextPage !== page) {
        setPage(nextPage);
      } else {
        await load(page);
      }
    } catch (err) {
      const axiosError = err as AxiosError<ApiError>;
      setError(axiosError.response?.data?.detail || 'Не удалось удалить видео');
      setPendingDelete(null);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <>
      <Header />

      <Container maxWidth="lg">
        <Box sx={{ mt: 4, mb: 6 }}>
          <Typography variant="h4" gutterBottom>
            История анализов
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Сохранённые результаты. Чтобы сохранить новый, откройте результат
            анализа и нажмите «Сохранить в историю».
          </Typography>

          {error ? (
            <Alert severity="error" sx={{ mb: 3 }}>
              {error}
            </Alert>
          ) : null}

          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 6 }}>
              <CircularProgress />
            </Box>
          ) : analyses.length === 0 ? (
            <Paper elevation={1} sx={{ p: 4, textAlign: 'center' }}>
              <Typography variant="body1" gutterBottom>
                Пока нет сохранённых анализов
              </Typography>
              <Button
                variant="contained"
                component={RouterLink}
                to="/upload"
                sx={{ mt: 2 }}
              >
                Загрузить видео
              </Button>
            </Paper>
          ) : (
            <TableContainer component={Paper} elevation={2}>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Видео</TableCell>
                    <TableCell>Дата</TableCell>
                    <TableCell align="right">Оценка</TableCell>
                    <TableCell align="right">Ошибок</TableCell>
                    <TableCell align="right" />
                  </TableRow>
                </TableHead>
                <TableBody>
                  {analyses.map((analysis) => (
                    <TableRow key={analysis.id} hover>
                      <TableCell>
                        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                          <HistoryThumb analysis={analysis} />
                          <Box>
                            <Typography variant="body2">
                              {analysis.filename || `Видео #${analysis.video_id}`}
                              {analysis.subject ? ` · ${SUBJECT_LABEL[analysis.subject]}` : ''}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              Р {shortScore(analysis.rhythm_score)} · П{' '}
                              {shortScore(analysis.posture_score)} · Т{' '}
                              {shortScore(analysis.technique_score)} · М{' '}
                              {shortScore(analysis.music_score)}
                            </Typography>
                          </Box>
                        </Box>
                      </TableCell>
                      <TableCell>{formatDate(analysis.started_at)}</TableCell>
                      <TableCell
                        align="right"
                        sx={{
                          color: scoreColor(analysis.overall_score),
                          fontWeight: 600,
                        }}
                      >
                        {analysis.overall_score !== null
                          ? analysis.overall_score.toFixed(0)
                          : '—'}
                      </TableCell>
                      <TableCell align="right">
                        <Chip
                          label={analysis.total_errors}
                          size="small"
                          color={analysis.total_errors > 0 ? 'warning' : 'success'}
                        />
                      </TableCell>
                      <TableCell align="right">
                        <Button
                          size="small"
                          endIcon={<ArrowForward />}
                          component={RouterLink}
                          to={`/results/${analysis.id}`}
                        >
                          Открыть
                        </Button>
                        <IconButton
                          aria-label="Удалить"
                          color="error"
                          onClick={() => setPendingDelete(analysis)}
                        >
                          <Delete />
                        </IconButton>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <TablePagination
                component="div"
                count={total}
                page={page}
                onPageChange={(_event, newPage) => setPage(newPage)}
                rowsPerPage={PAGE_SIZE}
                rowsPerPageOptions={[PAGE_SIZE]}
                labelDisplayedRows={({ from, to, count }) =>
                  `${from}–${to} из ${count}`
                }
              />
            </TableContainer>
          )}
        </Box>
      </Container>

      <Dialog open={pendingDelete !== null} onClose={() => setPendingDelete(null)}>
        <DialogTitle>Удалить анализ?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Видео «{pendingDelete?.filename || 'без названия'}» и его результат
            будут удалены без возможности восстановления.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPendingDelete(null)} disabled={deleting}>
            Отмена
          </Button>
          <Button color="error" onClick={() => void handleDelete()} disabled={deleting}>
            Удалить
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
