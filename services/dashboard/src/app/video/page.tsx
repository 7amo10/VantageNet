'use client';

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import VideoStreamPlayer from '@/components/VideoStreamPlayer';
import CameraSelector from '@/components/CameraSelector';
import { websocket } from '@/services/websocket';

interface Camera {
  id: string;
  name: string;
  status: 'online' | 'offline';
  location?: string;
}

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
  frameWidth?: number;
  frameHeight?: number;
}

export default function VideoPage() {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [selectedCameraId, setSelectedCameraId] = useState<string>('');
  const [faces, setFaces] = useState<DetectedFace[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showAnnotations, setShowAnnotations] = useState(true);
  const [isConnected, setIsConnected] = useState(false);
  const [streamStats, setStreamStats] = useState({
    latency: 0,
    fps: 0,
    faces: 0,
  });

  // Fetch available cameras from API
  useEffect(() => {
    const fetchCameras = async () => {
      try {
        setIsLoading(true);
        // Fetch from API Gateway (port 8000) - has persistent PostgreSQL storage
        const response = await fetch('http://localhost:8000/api/cameras/');

        if (response.ok) {
          const data = await response.json();
          // API returns array directly, map camera_id to id and status values
          const cameraList: Camera[] = (Array.isArray(data) ? data : []).map((cam: any) => ({
            id: cam.camera_id,
            name: cam.name,
            status: (cam.status === 'active' && cam.enabled) ? 'online' : 'offline',
            location: cam.metadata?.location,
          }));
          setCameras(cameraList);

          // Auto-select first online camera, or first available camera
          const firstOnline = cameraList.find(c => c.status === 'online');
          if (firstOnline) {
            setSelectedCameraId(firstOnline.id);
          } else if (cameraList.length > 0) {
            setSelectedCameraId(cameraList[0].id);
          }
        } else {
          console.error('[Video] Failed to fetch cameras:', response.statusText);
        }
      } catch (error) {
        console.error('[Video] Error fetching cameras:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchCameras();
  }, []);

  // Track faces and timestamp for proper clearing
  const facesMapRef = useRef<Map<string, DetectedFace>>(new Map());
  const lastTimestampRef = useRef<string>('');

  // Handle emotion events from WebSocket
  const handleEmotionEvent = useCallback((data: any) => {
    // Only update faces for the selected camera
    if (data.camera_id !== selectedCameraId) return;

    const timestamp = data.timestamp || new Date().toISOString();

    const newFace: DetectedFace = {
      faceId: data.face_id || `face_${Date.now()}`,
      emotion: data.emotion || 'neutral',
      confidence: data.confidence || 0.5,
      bbox: data.bbox || { x: 0, y: 0, width: 100, height: 100 },
      frameWidth: data.frame_width || 640,
      frameHeight: data.frame_height || 480,
    };

    // If new timestamp, clear all old faces first
    if (timestamp !== lastTimestampRef.current) {
      lastTimestampRef.current = timestamp;
      facesMapRef.current.clear();
    }

    // Add/update this face
    facesMapRef.current.set(newFace.faceId, newFace);

    // Update state
    setFaces(Array.from(facesMapRef.current.values()));

    // Update stats
    setStreamStats(prev => ({
      ...prev,
      faces: prev.faces + 1,
    }));
  }, [selectedCameraId]);

  // Initialize WebSocket connection
  useEffect(() => {
    const unsubscribeEmotion = websocket.onEmotionEvent(handleEmotionEvent);

    const unsubscribeConnect = websocket.onConnect(() => {
      console.log('[Video] WebSocket connected');
      setIsConnected(true);
    });

    const unsubscribeDisconnect = websocket.onDisconnect(() => {
      console.log('[Video] WebSocket disconnected');
      setIsConnected(false);
    });

    return () => {
      unsubscribeEmotion();
      unsubscribeConnect();
      unsubscribeDisconnect();
    };
  }, [handleEmotionEvent]);

  // Clear faces when camera changes
  useEffect(() => {
    setFaces([]);
  }, [selectedCameraId]);

  // Ensure camera is started in video-ingestion when selected
  useEffect(() => {
    const ensureCameraStarted = async () => {
      if (!selectedCameraId) return;

      try {
        // Get camera details from API Gateway
        const apiResponse = await fetch(`http://localhost:8000/api/cameras/`);
        if (!apiResponse.ok) return;

        const apiCameras = await apiResponse.json();
        const camera = apiCameras.find((c: any) => c.camera_id === selectedCameraId);
        if (!camera) return;

        // Check if camera exists in video-ingestion
        const videoResponse = await fetch('http://localhost:8001/cameras');
        const videoData = await videoResponse.json();
        const videoCameras = videoData.cameras || [];

        const existsInVideo = videoCameras.some((c: any) => c.camera_id === selectedCameraId);

        if (!existsInVideo) {
          // Create camera in video-ingestion with the same ID
          console.log('[Video] Starting camera in video-ingestion:', camera.name);
          const createResponse = await fetch('http://localhost:8001/cameras', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              camera_id: selectedCameraId,  // Pass the ID so it matches
              name: camera.name,
              source_type: camera.source_type,
              source_url: camera.source_url,
              fps: 10,
              enabled: true,
              metadata: camera.metadata
            })
          });

          if (createResponse.ok) {
            console.log('[Video] Camera started successfully');
          } else {
            console.error('[Video] Failed to start camera:', await createResponse.text());
          }
        }
      } catch (error) {
        console.error('[Video] Error ensuring camera started:', error);
      }
    };

    ensureCameraStarted();
  }, [selectedCameraId]);

  const handleCameraChange = (cameraId: string) => {
    setSelectedCameraId(cameraId);
  };

  // Memoize streamUrl to prevent creating new string references on every render
  // This prevents VideoStreamPlayer from reconnecting unnecessarily
  const streamUrl = useMemo(() => {
    if (!selectedCameraId) return '';
    return `http://localhost:8001/cameras/${selectedCameraId}/stream`;
  }, [selectedCameraId]);

  const selectedCamera = cameras.find(c => c.id === selectedCameraId);

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-gray-900">Live Video Stream</h1>
            <p className="text-gray-600 mt-2">Real-time camera feeds with emotion detection</p>
          </div>

          {/* Connection status */}
          <div className={`flex items-center gap-2 px-4 py-2 rounded-lg ${isConnected ? 'bg-green-100' : 'bg-red-100'}`}>
            <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
            <span className={`text-sm font-semibold ${isConnected ? 'text-green-700' : 'text-red-700'}`}>
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>
      </div>

      {/* Controls Row */}
      <div className="mb-6 flex items-center justify-between gap-4 flex-wrap">
        {/* Camera Selector */}
        <div className="flex-1 min-w-[300px]">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select Camera
          </label>
          <CameraSelector
            cameras={cameras}
            selectedCameraId={selectedCameraId}
            onCameraChange={handleCameraChange}
            isLoading={isLoading}
          />
        </div>

        {/* Annotation Toggle */}
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="showAnnotations"
              checked={showAnnotations}
              onChange={(e) => setShowAnnotations(e.target.checked)}
              className="w-5 h-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <label htmlFor="showAnnotations" className="text-sm font-medium text-gray-700 cursor-pointer">
              Show Annotations
            </label>
          </div>

          {/* Stats */}
          <div className="flex items-center gap-4 text-sm">
            <div className="flex items-center gap-2">
              <span className="text-gray-600">Faces:</span>
              <span className="font-semibold text-gray-800">{faces.length}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-gray-600">Total:</span>
              <span className="font-semibold text-gray-800">{streamStats.faces}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Video Player */}
      {selectedCameraId ? (
        <div className="bg-white rounded-lg shadow-lg p-4">
          <div className="w-full" style={{ minHeight: '600px', height: 'calc(100vh - 400px)' }}>
            <VideoStreamPlayer
              cameraId={selectedCameraId}
              streamUrl={streamUrl}
              faceCount={faces.length}
              showAnnotations={showAnnotations}
              autoPlay={true}
              onError={(error) => {
                console.error('[Video] Stream error:', error);
              }}
              onStreamReady={() => {
                console.log('[Video] Stream ready');
              }}
            />
          </div>

          {/* Camera Info */}
          {selectedCamera && (
            <div className="mt-4 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div>
                  <p className="text-sm text-gray-600">Camera</p>
                  <p className="font-semibold text-gray-800">{selectedCamera.name}</p>
                </div>
                {selectedCamera.location && (
                  <div>
                    <p className="text-sm text-gray-600">Location</p>
                    <p className="font-semibold text-gray-800">{selectedCamera.location}</p>
                  </div>
                )}
              </div>

              <div className="text-right">
                <p className="text-sm text-gray-600">Stream URL</p>
                <p className="text-xs font-mono text-gray-500 bg-gray-100 px-3 py-1 rounded">
                  {streamUrl}
                </p>
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-lg p-12 text-center">
          <div className="text-6xl mb-4">📹</div>
          <p className="text-xl font-semibold text-gray-800 mb-2">No Camera Selected</p>
          <p className="text-gray-600">Select a camera from the dropdown to start streaming</p>
        </div>
      )}

      {/* Instructions */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="font-semibold text-blue-900 mb-2">🎥 Live Streaming Features</h3>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• Real-time HLS video streaming with low latency (&lt;3s)</li>
          <li>• Face detection with emotion labels and confidence scores</li>
          <li>• Color-coded bounding boxes (happy=green, angry=red, etc.)</li>
          <li>• Automatic reconnection on stream failure</li>
          <li>• Toggle annotations on/off for cleaner view</li>
        </ul>
      </div>
    </div>
  );
}
