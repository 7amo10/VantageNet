'use client';

import { useEffect, useState } from 'react';
import { useWebSocket, SentimentUpdate, AlertTriggered, CameraStatus } from '@/hooks/useWebSocket';

interface DashboardStats {
  totalCameras: number;
  activeCameras: number;
  totalFaces: number;
  averageSentiment: number;
  dominantEmotion: string;
}

interface RecentAlert {
  id: string;
  message: string;
  timestamp: string;
  severity: 'info' | 'warning' | 'error';
}

export default function DashboardHome() {
  const [stats, setStats] = useState<DashboardStats>({
    totalCameras: 0,
    activeCameras: 0,
    totalFaces: 0,
    averageSentiment: 0,
    dominantEmotion: 'neutral',
  });

  const [recentAlerts, setRecentAlerts] = useState<RecentAlert[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<string>('Disconnected');

  // VANTA-31: WebSocket integration
  const { isConnected, isConnecting, error, reconnectAttempts } = useWebSocket({
    url: 'ws://localhost:8000/ws/live',
    
    onConnected: (data) => {
      console.log('WebSocket connected:', data);
      setConnectionStatus('Connected');
    },
    
    onSentimentUpdate: (data: SentimentUpdate) => {
      // Update dashboard stats with real-time sentiment data
      setStats(prev => ({
        ...prev,
        totalFaces: data.total_faces,
        averageSentiment: data.mood_score,
        dominantEmotion: data.dominant_emotion,
      }));
    },
    
    onAlert: (data: AlertTriggered) => {
      // Add new alert to the top of the list
      const newAlert: RecentAlert = {
        id: data.alert_id,
        message: data.message,
        timestamp: new Date(data.triggered_at).toLocaleString(),
        severity: data.severity === 'high' || data.severity === 'critical' ? 'error' 
                  : data.severity === 'medium' ? 'warning' 
                  : 'info',
      };
      
      setRecentAlerts(prev => [newAlert, ...prev.slice(0, 9)]); // Keep last 10 alerts
    },
    
    onCameraStatus: (data: CameraStatus) => {
      console.log('Camera status update:', data);
      // Update camera counts based on status
      if (data.status === 'connected') {
        setStats(prev => ({
          ...prev,
          activeCameras: prev.activeCameras + 1,
        }));
      } else if (data.status === 'disconnected') {
        setStats(prev => ({
          ...prev,
          activeCameras: Math.max(0, prev.activeCameras - 1),
        }));
      }
    },
    
    onError: (event) => {
      console.error('WebSocket error:', event);
      setConnectionStatus('Error');
    },
    
    autoReconnect: true,
    maxReconnectAttempts: 5,
  });

  // Update connection status based on state
  useEffect(() => {
    if (isConnecting) {
      setConnectionStatus(`Connecting... ${reconnectAttempts > 0 ? `(attempt ${reconnectAttempts})` : ''}`);
    } else if (isConnected) {
      setConnectionStatus('Connected');
    } else if (error) {
      setConnectionStatus(`Error: ${error}`);
    } else {
      setConnectionStatus('Disconnected');
    }
  }, [isConnected, isConnecting, error, reconnectAttempts]);

  // Fetch initial camera count
  useEffect(() => {
    fetch('http://localhost:8000/api/cameras')
      .then(res => res.json())
      .then(data => {
        setStats(prev => ({
          ...prev,
          totalCameras: data.cameras?.length || 0,
          activeCameras: data.cameras?.filter((c: any) => c.active).length || 0,
        }));
      })
      .catch(err => console.error('Error fetching cameras:', err));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600 mt-2">Real-time emotion analytics overview</p>
      </div>

      {/* VANTA-31: Connection Status Indicator */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-700">WebSocket Status:</span>
          <div className="flex items-center gap-2">
            <span className={`inline-block w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-500' : isConnecting ? 'bg-yellow-500' : 'bg-red-500'
            }`}></span>
            <span className="text-sm text-gray-600">{connectionStatus}</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Cameras"
          value={stats.totalCameras}
          icon="📹"
        />
        <StatCard
          title="Active Cameras"
          value={stats.activeCameras}
          icon="🟢"
        />
        <StatCard
          title="Faces Detected"
          value={stats.totalFaces}
          icon="👥"
          live={isConnected}
        />
        <StatCard
          title="Avg Sentiment"
          value={stats.averageSentiment.toFixed(2)}
          icon={getEmotionIcon(stats.dominantEmotion)}
          live={isConnected}
        />
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Live Feed</h2>
        <div className="flex items-center justify-center h-64 bg-gray-100 rounded">
          <p className="text-gray-500">Camera feed will appear here (Sprint 2)</p>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Recent Alerts</h2>
        {recentAlerts.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            No alerts yet. Listening for real-time updates...
          </div>
        ) : (
          <div className="space-y-3">
            {recentAlerts.map(alert => (
              <AlertItem
                key={alert.id}
                message={alert.message}
                timestamp={alert.timestamp}
                severity={alert.severity}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

interface StatCardProps {
  title: string;
  value: string | number;
  icon: string;
  live?: boolean;
}

function StatCard({ title, value, icon, live }: StatCardProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6 relative">
      {live && (
        <span className="absolute top-2 right-2 flex items-center gap-1 text-xs text-green-600">
          <span className="inline-block w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
          LIVE
        </span>
      )}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-600">{title}</p>
          <p className="text-2xl font-bold mt-1">{value}</p>
        </div>
        <span className="text-4xl">{icon}</span>
      </div>
    </div>
  );
}

interface AlertItemProps {
  message: string;
  timestamp: string;
  severity: 'info' | 'warning' | 'error';
}

function AlertItem({ message, timestamp, severity }: AlertItemProps) {
  const colors = {
    info: 'border-blue-200 bg-blue-50',
    warning: 'border-yellow-200 bg-yellow-50',
    error: 'border-red-200 bg-red-50',
  };

  return (
    <div className={`border-l-4 p-4 rounded ${colors[severity]}`}>
      <p className="font-medium">{message}</p>
      <p className="text-sm text-gray-600 mt-1">{timestamp}</p>
    </div>
  );
}

function getEmotionIcon(emotion: string): string {
  const icons: Record<string, string> = {
    happy: '😊',
    sad: '😢',
    angry: '😠',
    neutral: '😐',
    surprise: '😮',
    fear: '😨',
    disgust: '🤢',
  };
  return icons[emotion.toLowerCase()] || '😐';
}
