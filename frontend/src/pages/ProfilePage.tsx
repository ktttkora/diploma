/**
 * Profile page.
 *
 * Shows the account, lets the user change name, email and password,
 * and summarises progress across saved analyses.
 */

import { FormEvent, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Container,
  Paper,
  TextField,
  Typography,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  CircularProgress,
} from '@mui/material';
import { AxiosError } from 'axios';
import Header from '../components/Header';
import ProgressChart from '../components/ProgressChart';
import authService from '../services/authService';
import type { ApiError, User, UserStats } from '../types';

const ERROR_TYPE_LABELS: Record<string, string> = {
  rhythm: 'Ритм',
  posture: 'Постура',
  technique: 'Техника',
  musicality: 'Музыкальность',
  music: 'Музыкальность',
  content: 'Контент',
};

const SCORE_ROWS: { key: keyof UserStats['average_scores']; label: string }[] = [
  { key: 'overall', label: 'Общая' },
  { key: 'rhythm', label: 'Ритм' },
  { key: 'posture', label: 'Постура' },
  { key: 'technique', label: 'Техника' },
  { key: 'music', label: 'Музыкальность' },
];

/** Colour a score from red (low) through amber to green (high). */
function scoreColor(score: number | null): string {
  if (score === null) return 'text.disabled';
  if (score >= 80) return 'success.main';
  if (score >= 60) return 'warning.main';
  return 'error.main';
}

/** Format an ISO timestamp as a local date. */
function formatDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleDateString('ru-RU');
}

export default function ProfilePage() {
  const [user, setUser] = useState<User | null>(null);
  const [stats, setStats] = useState<UserStats | null>(null);
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [passwordAgain, setPasswordAgain] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState('');

  useEffect(() => {
    let active = true;
    const load = async () => {
      setLoading(true);
      try {
        const [profile, progress] = await Promise.all([
          authService.getCurrentUser(),
          authService.getStats(),
        ]);
        if (!active) return;
        setUser(profile);
        setStats(progress);
        setDisplayName(profile.display_name ?? '');
        setEmail(profile.email);
        setError('');
      } catch (err) {
        if (!active) return;
        const axiosError = err as AxiosError<ApiError>;
        setError(axiosError.response?.data?.detail || 'Не удалось загрузить профиль');
      } finally {
        if (active) setLoading(false);
      }
    };
    void load();
    return () => {
      active = false;
    };
  }, []);

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setSaved('');
    setError('');

    if (password && password.length < 8) {
      setError('Пароль должен быть не короче 8 символов');
      return;
    }
    if (password !== passwordAgain) {
      setError('Пароли не совпадают');
      return;
    }

    setSaving(true);
    try {
      const updated = await authService.updateProfile({
        display_name: displayName,
        email,
        ...(password ? { password } : {}),
      });
      setUser(updated);
      setPassword('');
      setPasswordAgain('');
      setSaved('Профиль обновлён');
    } catch (err) {
      const axiosError = err as AxiosError<ApiError>;
      setError(axiosError.response?.data?.detail || 'Не удалось сохранить профиль');
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <Header />
      <Container maxWidth="lg">
        <Box sx={{ mt: 4, mb: 6 }}>
          <Typography variant="h4" gutterBottom>
            Профиль
          </Typography>

          {error ? (
            <Alert severity="error" sx={{ mb: 3 }}>
              {error}
            </Alert>
          ) : null}
          {saved ? (
            <Alert severity="success" sx={{ mb: 3 }}>
              {saved}
            </Alert>
          ) : null}

          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 6 }}>
              <CircularProgress />
            </Box>
          ) : (
            <Box
              sx={{
                display: 'grid',
                gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' },
                gap: 3,
              }}
            >
              <Paper elevation={2} sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Данные аккаунта
                </Typography>
                {user ? (
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    С нами с {formatDate(user.created_at)}
                  </Typography>
                ) : null}
                <Box component="form" onSubmit={handleSubmit}>
                  <TextField
                    label="Имя"
                    value={displayName}
                    onChange={(event) => setDisplayName(event.target.value)}
                    fullWidth
                    margin="normal"
                    inputProps={{ maxLength: 100 }}
                  />
                  <TextField
                    label="Email"
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    required
                    fullWidth
                    margin="normal"
                  />
                  <TextField
                    label="Новый пароль"
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    fullWidth
                    margin="normal"
                    helperText="Оставьте пустым, если менять пароль не нужно"
                    autoComplete="new-password"
                  />
                  <TextField
                    label="Повторите пароль"
                    type="password"
                    value={passwordAgain}
                    onChange={(event) => setPasswordAgain(event.target.value)}
                    fullWidth
                    margin="normal"
                    autoComplete="new-password"
                  />
                  <Button
                    type="submit"
                    variant="contained"
                    disabled={saving}
                    sx={{ mt: 2 }}
                  >
                    {saving ? 'Сохранение…' : 'Сохранить'}
                  </Button>
                </Box>
              </Paper>

              <Paper elevation={2} sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Средние оценки
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  По {stats?.saved_analyses ?? 0} сохранённым анализам
                </Typography>
                {SCORE_ROWS.map((row) => {
                  const value = stats?.average_scores[row.key] ?? null;
                  return (
                    <Box key={row.key} sx={{ mb: 2 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                        <Typography variant="body2">{row.label}</Typography>
                        <Typography variant="body2" sx={{ color: scoreColor(value) }}>
                          {value === null ? '—' : value.toFixed(0)}
                        </Typography>
                      </Box>
                      <LinearProgress
                        variant="determinate"
                        value={value ?? 0}
                        sx={{ height: 8, borderRadius: 4 }}
                      />
                    </Box>
                  );
                })}

                <Typography variant="h6" sx={{ mt: 3 }} gutterBottom>
                  Частые ошибки
                </Typography>
                {stats && stats.top_errors.length > 0 ? (
                  <List dense disablePadding>
                    {stats.top_errors.map((item) => (
                      <ListItem key={item.error_type} disableGutters>
                        <ListItemText
                          primary={ERROR_TYPE_LABELS[item.error_type] || item.error_type}
                          secondary={`${item.count} раз`}
                        />
                      </ListItem>
                    ))}
                  </List>
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    Пока нет сохранённых ошибок
                  </Typography>
                )}
              </Paper>

              <Box sx={{ gridColumn: { md: '1 / -1' } }}>
                <ProgressChart points={stats?.progress ?? []} />
              </Box>
            </Box>
          )}
        </Box>
      </Container>
    </>
  );
}
