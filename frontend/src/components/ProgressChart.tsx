/**
 * Score timeline for saved analyses.
 */

import { Paper, Typography, Box } from '@mui/material';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { ProgressPoint } from '../types';

interface ProgressChartProps {
  points: ProgressPoint[];
}

const SERIES = [
  { key: 'overall_score', name: 'Общая', color: '#7b1fa2' },
  { key: 'rhythm_score', name: 'Ритм', color: '#0288d1' },
  { key: 'posture_score', name: 'Постура', color: '#2e7d32' },
  { key: 'technique_score', name: 'Техника', color: '#ed6c02' },
  { key: 'music_score', name: 'Музыкальность', color: '#c2185b' },
] as const;

/** Format an ISO timestamp as a short local date. */
function formatAxisDate(iso: string | null): string {
  if (!iso) return '—';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit' });
}

export default function ProgressChart({ points }: ProgressChartProps) {
  const data = points.map((point) => ({
    ...point,
    label: formatAxisDate(point.completed_at),
  }));

  return (
    <Paper elevation={2} sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        Прогресс
      </Typography>
      {data.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          Сохраните анализ, чтобы увидеть, как меняются оценки.
        </Typography>
      ) : (
        <Box sx={{ width: '100%', height: 320 }}>
          <ResponsiveContainer>
            <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="label" />
              <YAxis domain={[0, 100]} />
              <Tooltip />
              <Legend />
              {SERIES.map((series) => (
                <Line
                  key={series.key}
                  type="monotone"
                  dataKey={series.key}
                  name={series.name}
                  stroke={series.color}
                  strokeWidth={series.key === 'overall_score' ? 3 : 2}
                  connectNulls
                  dot={{ r: 3 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </Box>
      )}
    </Paper>
  );
}
