/**
 * Errors list.
 *
 * Renders the detected errors with severity and partner filters, and
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
import { SUBJECT_LABEL } from '../types';
import type { AnalysisError, ErrorSeverity } from '../types';

interface ErrorsListProps {
  errors: AnalysisError[];
  analysisId: number;
  onSeek?: (timestamp: number) => void;
  subject?: 'female' | 'male' | 'both' | null;
  personFilter: PersonFilter;
  onPersonFilterChange: (person: PersonFilter) => void;
}

type FilterValue = 'all' | ErrorSeverity;
export type PersonFilter = 'all' | 'female' | 'male';

const FILTERS: { value: FilterValue; label: string }[] = [
  { value: 'all', label: 'Все' },
  { value: 'critical', label: 'Критичные' },
  { value: 'high', label: 'Высокие' },
  { value: 'medium', label: 'Средние' },
  { value: 'low', label: 'Низкие' },
];

const PERSON_FILTERS: { value: PersonFilter; label: string }[] = [
  { value: 'all', label: 'Все' },
  { value: 'female', label: SUBJECT_LABEL.female },
  { value: 'male', label: SUBJECT_LABEL.male },
];

export default function ErrorsList({
  errors,
  analysisId,
  onSeek,
  subject,
  personFilter,
  onPersonFilterChange,
}: ErrorsListProps) {
  const [filter, setFilter] = useState<FilterValue>('all');

  const visible = useMemo(() => {
    return errors.filter((error) => {
      if (filter !== 'all' && error.severity !== filter) return false;
      if (personFilter === 'all') return true;
      return error.person === personFilter;
    });
  }, [errors, filter, personFilter]);

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

  const showPersonFilter = useMemo(() => {
    const hasFemale = errors.some((error) => error.person === 'female');
    const hasMale = errors.some((error) => error.person === 'male');
    return (hasFemale && hasMale) || (subject === 'both' && (hasFemale || hasMale));
  }, [errors, subject]);

  if (errors.length === 0) {
    return (
      <Alert severity="success">
        Ошибок не найдено — техника выглядит чисто.
      </Alert>
    );
  }

  const heading =
    filter === 'all' && personFilter === 'all'
      ? `Найденные ошибки (${visible.length})`
      : `Найденные ошибки (${visible.length} из ${errors.length})`;

  return (
    <Box>
      <Box sx={{ mb: 2 }}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: 2,
            mb: showPersonFilter ? 1 : 0,
          }}
        >
          <Typography variant="h6">{heading}</Typography>

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

        {showPersonFilter ? (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
            <Typography variant="body2" color="text.secondary">
              Кто:
            </Typography>
            <ToggleButtonGroup
              value={personFilter}
              exclusive
              size="small"
              aria-label="Кто"
              onChange={(_event, value: PersonFilter | null) => {
                if (value !== null) onPersonFilterChange(value);
              }}
            >
              {PERSON_FILTERS.map((option) => (
                <ToggleButton key={option.value} value={option.value}>
                  {option.label}
                </ToggleButton>
              ))}
            </ToggleButtonGroup>
          </Box>
        ) : null}
      </Box>

      {visible.length === 0 ? (
        <Alert severity="info">
          {personFilter !== 'all' &&
          !errors.some((error) => error.person === personFilter)
            ? 'Нет ошибок у выбранного партнёра.'
            : 'Нет ошибок с выбранной серьёзностью.'}
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
