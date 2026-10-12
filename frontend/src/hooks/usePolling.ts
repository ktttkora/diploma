/**
 * Polling hook.
 *
 * Repeatedly calls a fetcher until the caller stops it or the component
 * unmounts. Keeps a single timer in flight and cancels it on cleanup.
 */

import { useEffect, useRef, useState, useCallback } from 'react';

interface UsePollingOptions<T> {
  /** Poll interval in milliseconds. */
  intervalMs?: number;
  /** Start polling immediately on mount. */
  enabled?: boolean;
  /** Stop polling once this returns true for a result. */
  shouldStop?: (data: T) => boolean;
  /** Called with each successful result. */
  onData?: (data: T) => void;
  /** Called when a poll fails. */
  onError?: (error: unknown) => void;
}

interface UsePollingResult<T> {
  data: T | null;
  error: unknown;
  isPolling: boolean;
  /** Run the fetcher once, outside the interval. */
  refresh: () => Promise<T | null>;
  /** Stop the interval. */
  stop: () => void;
}

export function usePolling<T>(
  fetcher: () => Promise<T>,
  options: UsePollingOptions<T> = {}
): UsePollingResult<T> {
  const {
    intervalMs = 3000,
    enabled = true,
    shouldStop,
    onData,
    onError,
  } = options;

  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [isPolling, setIsPolling] = useState(enabled);

  // Keep the latest callbacks in refs so the interval never needs to be
  // torn down just because a parent re-rendered with new closures
  const fetcherRef = useRef(fetcher);
  const shouldStopRef = useRef(shouldStop);
  const onDataRef = useRef(onData);
  const onErrorRef = useRef(onError);

  fetcherRef.current = fetcher;
  shouldStopRef.current = shouldStop;
  onDataRef.current = onData;
  onErrorRef.current = onError;

  const stoppedRef = useRef(false);
  const inFlightRef = useRef(false);

  const stop = useCallback(() => {
    stoppedRef.current = true;
    setIsPolling(false);
  }, []);

  const refresh = useCallback(async (): Promise<T | null> => {
    // Skip if a previous request is still running, so a slow response
    // cannot stack up requests behind a short interval
    if (inFlightRef.current) {
      return null;
    }

    inFlightRef.current = true;
    try {
      const result = await fetcherRef.current();
      setData(result);
      setError(null);
      onDataRef.current?.(result);

      if (shouldStopRef.current?.(result)) {
        stop();
      }

      return result;
    } catch (err) {
      setError(err);
      onErrorRef.current?.(err);
      return null;
    } finally {
      inFlightRef.current = false;
    }
  }, [stop]);

  useEffect(() => {
    stoppedRef.current = false;

    if (!enabled) {
      setIsPolling(false);
      return;
    }

    setIsPolling(true);
    void refresh();

    const timer = window.setInterval(() => {
      if (stoppedRef.current) {
        window.clearInterval(timer);
        return;
      }
      void refresh();
    }, intervalMs);

    return () => {
      stoppedRef.current = true;
      window.clearInterval(timer);
    };
  }, [enabled, intervalMs, refresh]);

  return { data, error, isPolling, refresh, stop };
}

export default usePolling;
