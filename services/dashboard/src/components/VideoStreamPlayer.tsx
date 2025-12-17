'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import Hls from 'hls.js';

interface DetectedFace {
  faceId: string;
  emotion: string;
  confidence: number;
  bbox: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
}

interface VideoStreamPlayerProps {
  cameraId: string;
  streamUrl: string;
  faces?: DetectedFace[];
  autoPlay?: boolean;
  showAnnotations?: boolean;
  onError?: (error: string) => void;
  onStreamReady?: () => void;
}

const EMOTION_COLORS: Record<string, string> = {
  happy: '#10b981',      // green
  sad: '#3b82f6',        // blue
  angry: '#ef4444',      // red
  surprised: '#f59e0b',  // amber
  neutral: '#6b7280',    // gray
  fear: '#8b5cf6',       // purple
  disgust: '#f97316',    // orange
};

export default function VideoStreamPlayer({
  cameraId,
  streamUrl,
  faces = [],
  autoPlay = true,
  showAnnotations = true,
  onError,
  onStreamReady,
}: VideoStreamPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const hlsRef = useRef<Hls | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reconnectAttempt, setReconnectAttempt] = useState(0);
  const [streamStatus, setStreamStatus] = useState<'connecting' | 'playing' | 'error' | 'offline'>('connecting');

  // Draw annotations on canvas
  const drawAnnotations = useCallback(() => {
    const canvas = canvasRef.current;
    const video = videoRef.current;

    if (!canvas || !video || !showAnnotations || faces.length === 0) {
      return;
    }

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Match canvas size to video display size
    const rect = video.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;

    // Clear previous drawings
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Calculate scale factors
    const scaleX = canvas.width / video.videoWidth;
    const scaleY = canvas.height / video.videoHeight;

    // Draw each face
    faces.forEach((face) => {
      const { bbox, emotion, confidence } = face;
      
      // Scale bounding box coordinates
      const x = bbox.x * scaleX;
      const y = bbox.y * scaleY;
      const width = bbox.width * scaleX;
      const height = bbox.height * scaleY;

      // Get emotion color
      const color = EMOTION_COLORS[emotion.toLowerCase()] || '#6b7280';

      // Draw bounding box
      ctx.strokeStyle = color;
      ctx.lineWidth = 3;
      ctx.strokeRect(x, y, width, height);

      // Draw label background
      const label = `${emotion} (${(confidence * 100).toFixed(0)}%)`;
      ctx.font = 'bold 14px Inter, sans-serif';
      const textMetrics = ctx.measureText(label);
      const textWidth = textMetrics.width;
      const textHeight = 20;

      // Position label above box
      const labelX = x;
      const labelY = y - textHeight - 5;

      // Draw label background
      ctx.fillStyle = color;
      ctx.fillRect(labelX, labelY, textWidth + 10, textHeight);

      // Draw label text
      ctx.fillStyle = '#ffffff';
      ctx.fillText(label, labelX + 5, labelY + 15);
    });

    // Continue animation loop
    animationFrameRef.current = requestAnimationFrame(drawAnnotations);
  }, [faces, showAnnotations]);

  // Initialize HLS player
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    setIsLoading(true);
    setError(null);
    setStreamStatus('connecting');

    if (Hls.isSupported()) {
      const hls = new Hls({
        enableWorker: true,
        lowLatencyMode: true,
        backBufferLength: 90,
      });

      hlsRef.current = hls;

      hls.loadSource(streamUrl);
      hls.attachMedia(video);

      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        console.log('[VideoStream] HLS manifest parsed');
        setIsLoading(false);
        setStreamStatus('playing');
        if (autoPlay) {
          video.play().catch((err) => {
            console.error('[VideoStream] Autoplay failed:', err);
            setError('Autoplay blocked. Click to play.');
          });
        }
        onStreamReady?.();
      });

      hls.on(Hls.Events.ERROR, (event, data) => {
        console.error('[VideoStream] HLS error:', data);
        
        if (data.fatal) {
          setStreamStatus('error');
          switch (data.type) {
            case Hls.ErrorTypes.NETWORK_ERROR:
              setError('Network error. Reconnecting...');
              // Try to recover
              setTimeout(() => {
                setReconnectAttempt(prev => prev + 1);
                hls.startLoad();
              }, 5000);
              break;
            case Hls.ErrorTypes.MEDIA_ERROR:
              setError('Media error. Attempting recovery...');
              hls.recoverMediaError();
              break;
            default:
              setError('Stream unavailable');
              onError?.('Fatal HLS error');
              break;
          }
        }
      });

    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      // Native HLS support (Safari)
      video.src = streamUrl;
      
      video.addEventListener('loadedmetadata', () => {
        setIsLoading(false);
        setStreamStatus('playing');
        if (autoPlay) {
          video.play();
        }
        onStreamReady?.();
      });

      video.addEventListener('error', () => {
        setStreamStatus('error');
        setError('Stream unavailable');
        onError?.('Video playback error');
      });
    } else {
      setError('HLS not supported in this browser');
      setStreamStatus('offline');
    }

    // Cleanup
    return () => {
      if (hlsRef.current) {
        hlsRef.current.destroy();
        hlsRef.current = null;
      }
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [streamUrl, autoPlay, onStreamReady, onError]);

  // Handle play/pause events
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);

    video.addEventListener('play', handlePlay);
    video.addEventListener('pause', handlePause);

    return () => {
      video.removeEventListener('play', handlePlay);
      video.removeEventListener('pause', handlePause);
    };
  }, []);

  // Start annotation rendering when video is playing
  useEffect(() => {
    if (isPlaying && showAnnotations) {
      drawAnnotations();
    }

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, [isPlaying, showAnnotations, drawAnnotations]);

  const handlePlayPause = () => {
    const video = videoRef.current;
    if (!video) return;

    if (isPlaying) {
      video.pause();
    } else {
      video.play().catch((err) => {
        console.error('[VideoStream] Play failed:', err);
        setError('Failed to play video');
      });
    }
  };

  const getStatusColor = () => {
    switch (streamStatus) {
      case 'playing':
        return 'bg-green-500';
      case 'connecting':
        return 'bg-yellow-500';
      case 'error':
        return 'bg-orange-500';
      case 'offline':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const getStatusText = () => {
    switch (streamStatus) {
      case 'playing':
        return 'Live';
      case 'connecting':
        return 'Connecting...';
      case 'error':
        return 'Reconnecting...';
      case 'offline':
        return 'Offline';
      default:
        return 'Unknown';
    }
  };

  return (
    <div className="relative bg-black rounded-lg overflow-hidden shadow-lg">
      {/* Video element */}
      <video
        ref={videoRef}
        className="w-full h-full object-contain"
        controls={false}
        muted
        playsInline
      />

      {/* Canvas overlay for annotations */}
      <canvas
        ref={canvasRef}
        className="absolute top-0 left-0 w-full h-full pointer-events-none"
      />

      {/* Loading spinner */}
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-50">
          <div className="animate-spin rounded-full h-16 w-16 border-b-4 border-white"></div>
        </div>
      )}

      {/* Error message */}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-75">
          <div className="text-center text-white p-6">
            <div className="text-6xl mb-4">⚠️</div>
            <p className="text-xl font-semibold mb-2">{error}</p>
            <p className="text-sm text-gray-300">
              {reconnectAttempt > 0 && `Attempt ${reconnectAttempt}`}
            </p>
          </div>
        </div>
      )}

      {/* Status indicator */}
      <div className="absolute top-4 left-4 flex items-center gap-2 bg-black bg-opacity-60 px-3 py-2 rounded-lg">
        <div className={`w-3 h-3 rounded-full ${getStatusColor()} ${streamStatus === 'playing' ? 'animate-pulse' : ''}`} />
        <span className="text-white text-sm font-semibold">{getStatusText()}</span>
      </div>

      {/* Camera ID */}
      <div className="absolute top-4 right-4 bg-black bg-opacity-60 px-3 py-2 rounded-lg">
        <span className="text-white text-sm font-semibold">{cameraId}</span>
      </div>

      {/* Face count indicator */}
      {showAnnotations && faces.length > 0 && (
        <div className="absolute bottom-4 left-4 bg-black bg-opacity-60 px-3 py-2 rounded-lg">
          <span className="text-white text-sm font-semibold">
            👤 {faces.length} {faces.length === 1 ? 'Face' : 'Faces'}
          </span>
        </div>
      )}

      {/* Play/Pause button */}
      <button
        onClick={handlePlayPause}
        className="absolute bottom-4 right-4 bg-black bg-opacity-60 hover:bg-opacity-80 p-3 rounded-full transition-all"
        title={isPlaying ? 'Pause' : 'Play'}
      >
        {isPlaying ? (
          <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        ) : (
          <svg className="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
          </svg>
        )}
      </button>
    </div>
  );
}
