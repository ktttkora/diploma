/**
 * Video player with an error timeline.
 *
 * Streams the video through the authenticated endpoint (token in the query
 * string) and lets the user jump to any detected error by clicking a marker.
 */

import { useRef, useState, useEffect, useImperativeHandle, forwardRef } from 'react';
import { Paper, Box, Typography, Slider, Chip, Stack } from '@mui/material';
import api from '../services/api';
import authService from '../services/authService';
import type { AnalysisError, ErrorSeverity } from '../types';

export interface VideoPlayerHandle {
  /** Seek to a timestamp in seconds. */
  seekTo: (timestamp: number) => void;
}

interface VideoPlayerProps {
  videoId: number;
  errors: AnalysisError[];
}

const SEVERITY_COLOR: Record<ErrorSeverity, string> = {
  low: '#9e9e9e',
  medium: '#29b6f6',
  high: '#ffa726',
  critical: '#ef5350',
};

/** Format seconds as m:ss. */
function formatTimestamp(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  const minutes = Math.floor(total / 60);
  const rest = total % 60;
  return `${minutes}:${rest.toString().padStart(2, '0')}`;
}

export const VideoPlayer = forwardRef<VideoPlayerHandle, VideoPlayerProps>(
  function VideoPlayer({ videoId, errors }, ref) {
    const videoRef = useRef<HTMLVideoElement>(null);
    const [duration, setDuration] = useState(0);
    const [currentTime, setCurrentTime] = useState(0);

    // Media elements cannot send headers, so pass the token in the query
    const token = authService.getToken();
    const streamUrl = `${api.defaults.baseURL}/api/videos/${videoId}/stream?token=${encodeURIComponent(token ?? '')}`;

    useImperativeHandle(ref, () => ({
      seekTo(timestamp: number) {
        const video = videoRef.current;
        if (!video) return;
        video.currentTime = Math.max(0, timestamp);
        void video.play().catch(() => {
          // Autoplay may be blocked; the seek still applies
        });
      },
    }));

    // Track playback position for the timeline
    useEffect(() => {
      const video = videoRef.current;
      if (!video) return;

      const handleTimeUpdate = () => setCurrentTime(video.currentTime);
      const handleLoadedMetadata = () => setDuration(video.duration || 0);

      video.addEventListener('timeupdate', handleTimeUpdate);
      video.addEventListener('loadedmetadata', handleLoadedMetadata);

      return () => {
        video.removeEventListener('timeupdate', handleTimeUpdate);
        video.removeEventListener('loadedmetadata', handleLoadedMetadata);
      };
    }, []);

    const handleSliderChange = (_event: Event, value: number | number[]) => {
      const timestamp = Array.isArray(value) ? value[0] : value;
      const video = videoRef.current;
      if (video) {
        video.currentTime = timestamp;
      }
    };

    return (
      <Paper elevation={2} sx={{ p: 2 }}>
        <Box
          component="video"
          ref={videoRef}
          src={streamUrl}
          controls
          sx={{
            width: '100%',
            maxHeight: 480,
            bgcolor: 'black',
            borderRadius: 1,
            display: 'block',
          }}
        />

        {duration > 0 ? (
          <Box sx={{ mt: 2 }}>
            <Typography variant="caption" color="text.secondary">
              {formatTimestamp(currentTime)} / {formatTimestamp(duration)}
            </Typography>

            <Slider
              value={Math.min(currentTime, duration)}
              min={0}
              max={duration}
              step={0.1}
              onChange={handleSliderChange}
              size="small"
              aria-label="Позиция воспроизведения"
              sx={{
                // Colour the track by the error markers beneath it
                '& .MuiSlider-rail': { opacity: 0.4 },
              }}
            />

            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
              <Typography variant="caption" color="text.secondary">
                Ошибки:
              </Typography>
              {errors.length === 0 ? (
                <Typography variant="caption" color="text.secondary">
                  не найдены
                </Typography>
              ) : (
                errors.map((error) => (
                  <Chip
                    key={error.id}
                    label={formatTimestamp(error.timestamp)}
                    size="small"
                    onClick={() => {
                      const video = videoRef.current;
                      if (video) {
                        video.currentTime = error.timestamp;
                      }
                    }}
                    sx={{
                      bgcolor: SEVERITY_COLOR[error.severity],
                      color: 'white',
                      cursor: 'pointer',
                    }}
                  />
                ))
              )}
            </Stack>
          </Box>
        ) : null}
      </Paper>
    );
  }
);

export default VideoPlayer;
