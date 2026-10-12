/**
 * Error card.
 *
 * Shows one detected mistake: severity, timestamp, description, and the
 * composite screenshot with the user's pose and the reference pose.
 */

import { useEffect, useState } from 'react';
import {
  Card,
  CardContent,
  CardMedia,
  Typography,
  Box,
  Chip,
  Button,
  Skeleton,
  Alert,
} from '@mui/material';
import { PlayArrow } from '@mui/icons-material';
import analysisService from '../services/analysisService';
import type { AnalysisError, ErrorSeverity } from '../types';

interface ErrorCardProps {
  error: AnalysisError;
  analysisId: number;
  /** Seek the video player to this error's timestamp. */
  onSeek?: (timestamp: number) => void;
}

const SEVERITY_LABEL: Record<ErrorSeverity, string> = {
  low: 'Низкая',
  medium: 'Средняя',
  high: 'Высокая',
  critical: 'Критичная',
};

const SEVERITY_COLOR: Record<
  ErrorSeverity,
  'default' | 'info' | 'warning' | 'error'
> = {
  low: 'default',
  medium: 'info',
  high: 'warning',
  critical: 'error',
};

const CATEGORY_LABEL: Record<string, string> = {
  rhythm: 'Ритм',
  posture: 'Постура',
  technique: 'Техника',
  musicality: 'Музыкальность',
};

/** Format seconds as m:ss. */
function formatTimestamp(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(total / 60);
  const rest = total % 60;
  return `${minutes}:${rest.toString().padStart(2, '0')}`;
}

export default function ErrorCard({ error, analysisId, onSeek }: ErrorCardProps) {
  const [screenshotUrl, setScreenshotUrl] = useState<string | null>(null);
  const [imageError, setImageError] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    // Screenshots are behind an authenticated endpoint, so fetch as a blob
    // and revoke the object URL when the card unmounts
    if (!error.screenshot_path) {
      return;
    }

    let objectUrl: string | null = null;
    let cancelled = false;

    setLoading(true);
    analysisService
      .fetchScreenshot(analysisId, error.id)
      .then((url) => {
        if (cancelled) {
          URL.revokeObjectURL(url);
          return;
        }
        objectUrl = url;
        setScreenshotUrl(url);
      })
      .catch(() => {
        if (!cancelled) {
          setImageError(true);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [analysisId, error.id, error.screenshot_path]);

  return (
    <Card elevation={2} sx={{ mb: 2 }}>
      <CardContent>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            gap: 1,
            flexWrap: 'wrap',
            mb: 1.5,
          }}
        >
          <Chip
            label={SEVERITY_LABEL[error.severity]}
            color={SEVERITY_COLOR[error.severity]}
            size="small"
          />
          <Chip
            label={CATEGORY_LABEL[error.error_type] ?? error.error_type}
            size="small"
            variant="outlined"
          />
          <Chip
            label={formatTimestamp(error.timestamp)}
            size="small"
            variant="outlined"
          />
          {error.element_name && error.element_name !== 'не определён' ? (
            <Chip label={error.element_name} size="small" color="primary" />
          ) : null}
        </Box>

        <Typography variant="body1" sx={{ mb: 1, whiteSpace: 'pre-line' }}>
          {error.description}
        </Typography>

        {onSeek ? (
          <Button
            size="small"
            startIcon={<PlayArrow />}
            onClick={() => onSeek(error.timestamp)}
          >
            Перейти к моменту
          </Button>
        ) : null}
      </CardContent>

      {loading ? <Skeleton variant="rectangular" height={220} /> : null}

      {!loading && screenshotUrl ? (
        <CardMedia
          component="img"
          image={screenshotUrl}
          alt={`Ошибка на ${formatTimestamp(error.timestamp)}`}
          sx={{ maxHeight: 420, objectFit: 'contain', bgcolor: 'grey.100' }}
        />
      ) : null}

      {!loading && !screenshotUrl && imageError ? (
        <Box sx={{ p: 2 }}>
          <Alert severity="info" variant="outlined">
            Скриншот недоступен
          </Alert>
        </Box>
      ) : null}
    </Card>
  );
}
