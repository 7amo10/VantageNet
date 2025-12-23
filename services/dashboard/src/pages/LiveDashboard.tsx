'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import LiveSentimentCard from '@/components/LiveSentimentCard';
import EmotionDistributionChart from '@/components/EmotionDistributionChart';
import CrowdSizeGauge from '@/components/CrowdSizeGauge';
import MoodTrendChart from '@/components/MoodTrendChart';
import AlertFeedPanel, { AlertItem } from '@/components/AlertFeedPanel';
import { websocket } from '@/services/websocket';

interface EmotionDistribution extends Record<string, number> {
  happy: number;
  sad: number;
  angry: number;
  surprised: number;
  neutral: number;
  fear: number;
  disgust: number;
}

interface MoodDataPoint {
  timestamp: number;
  moodScore: number;
  emotion?: string;
}

interface CrowdHistory {
  timestamp: number;
  count: number;
}

export default function LiveEmotionDashboard() {
  // Live Sentiment State
  const [dominantEmotion, setDominantEmotion] = useState<string>('neutral');
  const [moodScore, setMoodScore] = useState<number>(0.5);
  const [trend, setTrend] = useState<'up' | 'down' | 'stable'>('stable');
  const [lastSentimentUpdate, setLastSentimentUpdate] = useState<Date>(new Date());

  // Emotion Distribution State
  const [emotionDistribution, setEmotionDistribution] = useState<EmotionDistribution>({
    happy: 0,
    sad: 0,
    angry: 0,
    surprised: 0,
    neutral: 0,
    fear: 0,
    disgust: 0,
  });
  const [lastEmotionUpdate, setLastEmotionUpdate] = useState<Date>(new Date());

  // Crowd Size State
  const [crowdSize, setCrowdSize] = useState<number>(0);
  const [crowdHistory, setCrowdHistory] = useState<CrowdHistory[]>([]);

  // Mood Trend State
  const [moodTrendData, setMoodTrendData] = useState<MoodDataPoint[]>([]);

  // Alert State
  const [alerts, setAlerts] = useState<AlertItem[]>([]);

  // Connection State
  const [isConnected, setIsConnected] = useState(false);

  // Refs for previous values (for trend calculation)
  const prevMoodScore = useRef<number>(0.5);
  const emotionUpdateInterval = useRef<NodeJS.Timeout | null>(null);

  // Calculate trend based on previous mood score
  const calculateTrend = useCallback((newScore: number): 'up' | 'down' | 'stable' => {
    const diff = newScore - prevMoodScore.current;
    if (Math.abs(diff) < 0.05) return 'stable';
    return diff > 0 ? 'up' : 'down';
  }, []);

  // Handle sentiment update from WebSocket
  const handleSentimentUpdate = useCallback((data: any) => {
    console.log('[Dashboard] Sentiment update received:', data);

    const newMoodScore = data.sentiment_score || data.moodScore || 0.5;
    const newTrend = calculateTrend(newMoodScore);

    setMoodScore(newMoodScore);
    setDominantEmotion(data.dominant_emotion || data.emotion || 'neutral');
    setTrend(newTrend);
    setCrowdSize(data.face_count || data.faceCount || 0);
    setLastSentimentUpdate(new Date());

    prevMoodScore.current = newMoodScore;

    // Add to mood trend data
    setMoodTrendData(prev => {
      const newPoint: MoodDataPoint = {
        timestamp: Date.now(),
        moodScore: newMoodScore,
        emotion: data.dominant_emotion || data.emotion,
      };
      return [...prev, newPoint].slice(-180); // Keep last 30 minutes (assuming 10s intervals)
    });

    // Add to crowd history
    setCrowdHistory(prev => {
      const newPoint: CrowdHistory = {
        timestamp: Date.now(),
        count: data.face_count || data.faceCount || 0,
      };
      return [...prev, newPoint].slice(-30); // Keep last 5 minutes
    });
  }, [calculateTrend]);

  // Handle emotion event from WebSocket
  const handleEmotionEvent = useCallback((data: any) => {
    console.log('[Dashboard] Emotion event received:', data);

    setEmotionDistribution(prev => {
      const emotion = (data.emotion || 'neutral').toLowerCase();
      return {
        ...prev,
        [emotion]: (prev[emotion as keyof EmotionDistribution] || 0) + 1,
      };
    });
    setLastEmotionUpdate(new Date());
  }, []);

  // Handle alert from WebSocket
  const handleAlert = useCallback((data: any) => {
    console.log('[Dashboard] Alert received:', data);

    const newAlert: AlertItem = {
      id: data.alert_id || data.id || `alert_${Date.now()}`,
      ruleId: data.rule_id || data.ruleId || 'unknown',
      ruleName: data.rule_name || data.ruleName || 'Unknown Rule',
      message: data.message || 'Alert triggered',
      severity: data.severity || 'info',
      timestamp: new Date(data.timestamp || Date.now()),
      cameraId: data.camera_id || data.cameraId,
      resolved: false,
    };

    setAlerts(prev => [newAlert, ...prev].slice(0, 50)); // Keep last 50 alerts
  }, []);

  // Initialize WebSocket connection
  useEffect(() => {
    console.log('[Dashboard] Initializing WebSocket connection');

    // Fetch initial alerts from API
    const fetchInitialAlerts = async () => {
      try {
        const response = await fetch('http://localhost:8000/api/alerts/?page=1&limit=10');
        if (response.ok) {
          const data = await response.json();
          const initialAlerts: AlertItem[] = (data.alerts || []).map((alert: any) => ({
            id: alert.id,
            ruleId: alert.rule_id,
            ruleName: alert.rule_name || 'Unknown Rule',
            message: alert.message,
            severity: alert.severity || 'info',
            timestamp: new Date(alert.triggered_at),
            cameraId: alert.camera_id,
            resolved: !!alert.resolved_at,
          }));
          setAlerts(initialAlerts);
          console.log('[Dashboard] Loaded', initialAlerts.length, 'initial alerts');
        }
      } catch (error) {
        console.error('[Dashboard] Failed to fetch initial alerts:', error);
      }
    };

    fetchInitialAlerts();

    // Register handlers
    const unsubscribeSentiment = websocket.onSentimentUpdate(handleSentimentUpdate);
    const unsubscribeEmotion = websocket.onEmotionEvent(handleEmotionEvent);
    const unsubscribeAlert = websocket.onAlert(handleAlert);

    const unsubscribeConnect = websocket.onConnect(() => {
      console.log('[Dashboard] WebSocket connected');
      setIsConnected(true);
    });

    const unsubscribeDisconnect = websocket.onDisconnect(() => {
      console.log('[Dashboard] WebSocket disconnected');
      setIsConnected(false);
    });

    // Start periodic emotion decay (reset distribution every 2 seconds for fresh data)
    emotionUpdateInterval.current = setInterval(() => {
      setEmotionDistribution(prev => {
        const total = Object.values(prev).reduce((sum, val) => sum + val, 0);
        if (total === 0) return prev;

        // Decay old emotions gradually
        const decayed: EmotionDistribution = {
          happy: Math.floor(prev.happy * 0.95),
          sad: Math.floor(prev.sad * 0.95),
          angry: Math.floor(prev.angry * 0.95),
          surprised: Math.floor(prev.surprised * 0.95),
          fear: Math.floor(prev.fear * 0.95),
          disgust: Math.floor(prev.disgust * 0.95),
          neutral: Math.floor(prev.neutral * 0.95)
        };
        return decayed;
      });
    }, 2000);

    // Cleanup
    return () => {
      unsubscribeSentiment();
      unsubscribeEmotion();
      unsubscribeAlert();
      unsubscribeConnect();
      unsubscribeDisconnect();
      if (emotionUpdateInterval.current) {
        clearInterval(emotionUpdateInterval.current);
      }
    };
  }, [handleSentimentUpdate, handleEmotionEvent, handleAlert]);

  // Alert handlers
  const handleResolveAlert = useCallback((alertId: string) => {
    setAlerts(prev =>
      prev.map(alert =>
        alert.id === alertId ? { ...alert, resolved: true } : alert
      )
    );
  }, []);

  const handleDismissAlert = useCallback((alertId: string) => {
    setAlerts(prev => prev.filter(alert => alert.id !== alertId));
  }, []);

  const handleViewAlertDetails = useCallback((alertItem: AlertItem) => {
    console.log('[Dashboard] View alert details:', alertItem);
    // TODO: Open modal with alert details
    window.alert(`Alert Details:\n\n${JSON.stringify(alertItem, null, 2)}`);
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-gray-900">Live Emotion Dashboard</h1>
            <p className="text-gray-600 mt-2">Real-time crowd sentiment analysis and monitoring</p>
          </div>
          <div className="flex items-center gap-3">
            <div className={`flex items-center gap-2 px-4 py-2 rounded-lg ${isConnected ? 'bg-green-100' : 'bg-red-100'}`}>
              <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
              <span className={`text-sm font-semibold ${isConnected ? 'text-green-700' : 'text-red-700'}`}>
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Dashboard Grid - Responsive Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Top Row: Live Sentiment Card (spans 4 cols) + Emotion Distribution (spans 5 cols) + Crowd Size (spans 3 cols) */}
        <div className="lg:col-span-4">
          <LiveSentimentCard
            emotion={dominantEmotion}
            moodScore={moodScore}
            trend={trend}
            lastUpdate={lastSentimentUpdate}
          />
        </div>

        <div className="lg:col-span-5">
          <EmotionDistributionChart
            emotions={emotionDistribution}
            lastUpdate={lastEmotionUpdate}
          />
        </div>

        <div className="lg:col-span-3">
          <CrowdSizeGauge
            currentCount={crowdSize}
            history={crowdHistory}
            lastUpdate={lastSentimentUpdate}
          />
        </div>

        {/* Middle Row: Mood Trend Chart (spans 8 cols) */}
        <div className="lg:col-span-8">
          <MoodTrendChart
            data={moodTrendData}
            lastUpdate={lastSentimentUpdate}
          />
        </div>

        {/* Middle Row: Alert Feed (spans 4 cols) */}
        <div className="lg:col-span-4">
          <AlertFeedPanel
            alerts={alerts}
            onResolve={handleResolveAlert}
            onDismiss={handleDismissAlert}
            onViewDetails={handleViewAlertDetails}
          />
        </div>
      </div>

      {/* Footer Info */}
      <div className="mt-8 text-center text-sm text-gray-500">
        <p>Dashboard updates automatically via WebSocket connection</p>
        <p className="mt-1">
          Sentiment: Every 1s | Emotions: Every 2s | Performance optimized for 60 FPS
        </p>
      </div>
    </div>
  );
}
