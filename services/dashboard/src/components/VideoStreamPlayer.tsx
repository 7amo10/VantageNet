'use client';

import { useEffect, useRef, useState, useCallback, memo } from 'react';

// ============================================================================
// TYPES
// ============================================================================

interface VideoStreamPlayerProps {
  cameraId: string;
  streamUrl: string;
  faceCount?: number;
  autoPlay?: boolean;
  showAnnotations?: boolean;
  onError?: (error: string) => void;
  onStreamReady?: () => void;
}

type StreamStatus = 'idle' | 'connecting' | 'playing' | 'error';

const DEBUG = false;
const log = (...args: unknown[]) => {
  if (DEBUG) console.log('[VideoStream]', ...args);
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

function VideoStreamPlayer({
  cameraId,
  streamUrl,
  faceCount = 0,
  autoPlay = true,
  showAnnotations = true,
  onError,
  onStreamReady,
}: VideoStreamPlayerProps) {
  // Refs
  const imgRef = useRef<HTMLImageElement>(null);
  const initializedUrlRef = useRef<string>('');
  const statusRef = useRef<StreamStatus>('idle');

  // State
  const [status, setStatus] = useState<StreamStatus>('idle');

  const updateStatus = useCallback((newStatus: StreamStatus) => {
    statusRef.current = newStatus;
    setStatus(newStatus);
  }, []);

  // ============================================================================
  // STREAM INITIALIZATION
  // ============================================================================

  useEffect(() => {
    if (initializedUrlRef.current === streamUrl) return;
    if (!streamUrl) return;

    log('Initializing stream:', streamUrl);
    initializedUrlRef.current = streamUrl;
    updateStatus('connecting');

    const img = imgRef.current;
    if (!img) return;

    let checkInterval: NodeJS.Timeout | null = null;
    let mounted = true;

    const handleLoad = () => {
      if (!mounted) return;
      updateStatus('playing');
      onStreamReady?.();
    };

    const handleError = () => {
      if (!mounted) return;
      if (statusRef.current === 'idle') {
        updateStatus('error');
        onError?.('Stream failed to load');
      }
    };

    img.addEventListener('load', handleLoad);
    img.addEventListener('error', handleError);

    // Build stream URL with annotations enabled
    const annotatedUrl = streamUrl.includes('?')
      ? `${streamUrl}&annotate=${showAnnotations}`
      : `${streamUrl}?annotate=${showAnnotations}`;
    img.src = annotatedUrl;

    let attempts = 0;
    checkInterval = setInterval(() => {
      if (!mounted) {
        if (checkInterval) clearInterval(checkInterval);
        return;
      }
      attempts++;
      if (img.naturalWidth > 0 && img.naturalHeight > 0) {
        log('Stream ready:', img.naturalWidth, 'x', img.naturalHeight);
        updateStatus('playing');
        onStreamReady?.();
        if (checkInterval) clearInterval(checkInterval);
      } else if (attempts > 50) {
        if (checkInterval) clearInterval(checkInterval);
      }
    }, 100);

    return () => {
      mounted = false;
      if (checkInterval) clearInterval(checkInterval);
      img.removeEventListener('load', handleLoad);
      img.removeEventListener('error', handleError);
    };
  }, [streamUrl, showAnnotations, onStreamReady, onError, updateStatus]);

  // ============================================================================
  // STATUS HELPERS
  // ============================================================================

  const getStatusColor = () => {
    switch (status) {
      case 'playing': return 'bg-green-500';
      case 'connecting': return 'bg-yellow-500 animate-pulse';
      case 'error': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'playing': return 'Live';
      case 'connecting': return 'Connecting...';
      case 'error': return 'Error';
      default: return 'Idle';
    }
  };

  // ============================================================================
  // RENDER
  // ============================================================================

  return (
    <div className="relative bg-gray-900 rounded-lg overflow-hidden shadow-lg w-full h-full min-h-[400px]">
      {streamUrl && (
        <img
          ref={imgRef}
          className="w-full h-full object-contain"
          alt="Live camera stream with emotion detection"
          style={{ display: 'block', backgroundColor: '#1a1a1a' }}
        />
      )}

      {/* Status indicator */}
      <div className="absolute top-4 left-4 flex items-center gap-2 bg-black bg-opacity-70 px-3 py-2 rounded-lg">
        <div className={`w-3 h-3 rounded-full ${getStatusColor()}`} />
        <span className="text-white text-sm font-semibold">{getStatusText()}</span>
      </div>

      {/* Camera ID */}
      <div className="absolute top-4 right-4 bg-black bg-opacity-70 px-3 py-2 rounded-lg">
        <span className="text-white text-xs font-mono">{cameraId.slice(0, 8)}...</span>
      </div>

      {/* Annotations info (server-side rendering) */}
      {showAnnotations && (
        <div className="absolute bottom-4 right-4 bg-black bg-opacity-70 px-3 py-2 rounded-lg">
          <span className="text-white text-xs">
            📊 Server-side annotations
          </span>
        </div>
      )}
    </div>
  );
}

// Memo to prevent unnecessary re-renders
export default memo(VideoStreamPlayer, (prevProps, nextProps) => {
  if (prevProps.streamUrl !== nextProps.streamUrl) return false;
  if (prevProps.cameraId !== nextProps.cameraId) return false;
  if (prevProps.showAnnotations !== nextProps.showAnnotations) return false;
  return true;
});
