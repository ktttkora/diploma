/**
 * History page.
 *
 * Lists the user's saved analyses with their scores, and links to each
 * result. Saved analyses are the ones the user kept from the results page.
 */

import { useEffect, useState, useCallback } from 'react';
import { useNavigate, Link as RouterLink } from 'react-router-dom';
import {
  Container,
  Box,
  Typography,
  AppBar,
  Toolbar,
  IconButton,
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
} from '@mui/material';
import { Logout, CloudUpload, ArrowForward } from '@mui/icons-material';
import { AxiosError } from 'axios';
import analysisService from '../services/analysisService';
import authService from '../services/authService';
import type { Analysis, ApiError } from '../types';

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

export default function HistoryPage() {
  const navigate = useNavigate();

  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

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

  const handleLogout = () => {
    authService.logout();
    navigate('/login');
  };

  return (
    <>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            Hustl Analyzer
          </Typography>
          <Button
            color="inherit"
            component={RouterLink}
            to="/upload"
            startIcon={<CloudUpload />}
          >
            Загрузить
          </Button>
          <IconButton color="inherit" onClick={handleLogout} title="Выйти">
            <Logout />
          </IconButton>
        </Toolbar>
      </AppBar>

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
                    <TableCell>Дата</TableCell>
                    <TableCell align="right">Оценка</TableCell>
                    <TableCell align="right">Ошибок</TableCell>
                    <TableCell align="right">Длительность</TableCell>
                    <TableCell align="right" />
                  </TableRow>
                </TableHead>
                <TableBody>
                  {analyses.map((analysis) => (
                    <TableRow key={analysis.id} hover>
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
                        {analysis.processing_time !== null
                          ? `${analysis.processing_time.toFixed(0)} с`
                          : '—'}
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
    </>
  );
}
