/**
 * Scores summary.
 *
 * Shows the overall score plus a per-category breakdown. Categories the
 * AI could not evaluate are shown as unavailable rather than as zero.
 */

import { Paper, Typography, Box, LinearProgress, Chip, Tooltip } from '@mui/material';
import type { Analysis } from '../types';

interface ScoresSummaryProps {
  analysis: Analysis;
}

interface ScoreRow {
  label: string;
  value: number | null;
}

/** Colour a score from red (low) through amber to green (high). */
function scoreColor(score: number | null): string {
  if (score === null) return 'text.disabled';
  if (score >= 80) return 'success.main';
  if (score >= 60) return 'warning.main';
  return 'error.main';
}

export default function ScoresSummary({ analysis }: ScoresSummaryProps) {
  const rows: ScoreRow[] = [
    { label: 'Ритм', value: analysis.rhythm_score },
    { label: 'Постура', value: analysis.posture_score },
    { label: 'Техника', value: analysis.technique_score },
    { label: 'Музыкальность', value: analysis.music_score },
  ];

  const overall = analysis.overall_score;

  return (
    <Paper elevation={2} sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        Оценки
      </Typography>

      <Box sx={{ display: 'flex', alignItems: 'baseline', gap: 2, mb: 3 }}>
        <Typography
          variant="h2"
          sx={{ color: scoreColor(overall), fontWeight: 600 }}
        >
          {overall !== null ? overall.toFixed(0) : '—'}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          общая оценка из 100
        </Typography>
      </Box>

      {rows.map((row) => (
        <Box key={row.label} sx={{ mb: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
            <Typography variant="body2">{row.label}</Typography>
            <Typography variant="body2" color={scoreColor(row.value)}>
              {row.value !== null ? row.value.toFixed(0) : 'н/д'}
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={row.value ?? 0}
            color={
              row.value === null
                ? 'inherit'
                : row.value >= 80
                  ? 'success'
                  : row.value >= 60
                    ? 'warning'
                    : 'error'
            }
            sx={{ height: 6, borderRadius: 3 }}
          />
        </Box>
      ))}

      <Box sx={{ display: 'flex', gap: 1, mt: 3, flexWrap: 'wrap' }}>
        <Chip
          label={`Ошибок: ${analysis.total_errors}`}
          size="small"
          color={analysis.total_errors > 0 ? 'warning' : 'success'}
        />
        {analysis.processing_time !== null ? (
          <Chip
            label={`Обработка: ${analysis.processing_time.toFixed(0)} с`}
            size="small"
            variant="outlined"
          />
        ) : null}
        {analysis.posture_score === null ? (
          <Tooltip title="Для оценки постуры, техники и музыкальности нужен ключ ANTHROPIC_API_KEY">
            <Chip label="AI-анализ недоступен" size="small" color="default" />
          </Tooltip>
        ) : null}
      </Box>
    </Paper>
  );
}
