/**
 * Errors list.
 *
 * Renders the detected errors with optional severity filtering, and
 * forwards a seek request when the user wants to see the moment.
 */

import { useMemo, useState } from 'react';
import {
  Box,
  Typography,
  ToggleButtonGroup,
  ToggleButton,
  Alert,
} from '@mui/material';
import ErrorCard from './ErrorCard';
import type { AnalysisError, ErrorSeverity } from '../types';

interface ErrorsListProps {
  errors: AnalysisError[];
  analysisId: number;
  onSeek?: (timestamp: number) => void;
}

type FilterValue = 'all' | ErrorSeverity;

const FILTERS: { value: FilterValue; label: string }[] = [
  { value: 'all', label: 'Все' },
  { value: 'critical', label: 'Критичные' },
  { value: 'high', label: 'Высокие' },
  { value: 'medium', label: 'Средние' },
  { value: 'low', label: 'Низкие' },
];

export default function ErrorsList({ errors, analysisId, onSeek }: ErrorsListProps) {
  const [filter, setFilter] = useState<FilterValue>('all');

  const visible = useMemo(() => {
    if (filter === 'all') return errors;
    return errors.filter((error) => error.severity === filter);
  }, [errors, filter]);

  // Only offer filters that match at least one error
  const availableFilters = useMemo(
    () =>
      FILTERS.filter(
        (option) =>
          option.value === 'all' ||
          errors.some((error) => error.severity === option.value)
      ),
    [errors]
  );

  if (errors.length === 0) {
    return (
      <Alert severity="success">
        Ошибок не найдено — техника выглядит чисто.
      </Alert>
    );
  }

  return (
    <Box>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 2,
          mb: 2,
        }}
      >
        <Typography variant="h6">
          Найденные ошибки ({errors.length})
        </Typography>

        {availableFilters.length > 2 ? (
          <ToggleButtonGroup
            value={filter}
            exclusive
            size="small"
            onChange={(_event, value: FilterValue | null) => {
              if (value !== null) setFilter(value);
            }}
          >
            {availableFilters.map((option) => (
              <ToggleButton key={option.value} value={option.value}>
                {option.label}
              </ToggleButton>
            ))}
          </ToggleButtonGroup>
        ) : null}
      </Box>

      {visible.length === 0 ? (
        <Alert severity="info">
          Нет ошибок с выбранной серьёзностью.
        </Alert>
      ) : (
        visible.map((error) => (
          <ErrorCard
            key={error.id}
            error={error}
            analysisId={analysisId}
            onSeek={onSeek}
          />
        ))
      )}
    </Box>
  );
}
