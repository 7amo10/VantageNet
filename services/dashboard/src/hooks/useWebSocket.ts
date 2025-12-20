/**
 * useWebSocket Hook
 * 
 * VANTA-31: Custom hook for WebSocket connection management with:
 * - Automatic reconnection with exponential backoff (max 5 attempts)
 * - Message handlers for all message types
 * - Connection state management
 * - Cleanup on unmount
 * - 30s inactivity timeout handling
 */

import { useEffect, useRef, useState, useCallback } from 'react';

export interface SentimentUpdate {
  timestamp: string;
  camera_id: string;
  total_faces: number;
  dominant_emotion: string;
  mood_score: number;
  emotion_distribution: {
    happy: number;
    sad: number;
    angry: number;
    neutral: number;
    surprise: number;
    fear: number;
    disgust: number;
  };
}

export interface AlertTriggered {
  alert_id: string;
  rule_id: string;
  camera_id: string;
  message: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  triggered_at: string;
  metadata?: Record<string, any>;
}

export interface RuleEvaluation {
  rule_id: string;
  camera_id: string;
  result: boolean;
  conditions_met: string[];
  timestamp: string;
}

export interface CameraStatus {
  camera_id: string;
  status: 'connected' | 'disconnected';
  timestamp: string;
  reason?: string;
}

export interface WebSocketMessage {
  type: 'sentiment_update' | 'alert_triggered' | 'rule_evaluation' | 'camera_status' | 'connected' | 'pong';
  data?: any;
  timestamp: string;
}

export interface UseWebSocketOptions {
  url: string;
  onSentimentUpdate?: (data: SentimentUpdate) => void;
  onAlert?: (data: AlertTriggered) => void;
  onRuleEvaluation?: (data: RuleEvaluation) => void;
  onCameraStatus?: (data: CameraStatus) => void;
  onConnected?: (data: any) => void;
  onError?: (error: Event) => void;
  autoReconnect?: boolean;
  maxReconnectAttempts?: number;
  reconnectInterval?: number;
}

export interface UseWebSocketReturn {
  isConnected: boolean;
  isConnecting: boolean;
  error: string | null;
  reconnectAttempts: number;
  sendMessage: (message: string) => void;
}

export const useWebSocket = (options: UseWebSocketOptions): UseWebSocketReturn => {
  const {
    url,
    onSentimentUpdate,
    onAlert,
    onRuleEvaluation,
    onCameraStatus,
    onConnected,
    onError,
    autoReconnect = true,
    maxReconnectAttempts = 5,
    reconnectInterval = 1000, // Initial reconnect interval (1s)
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const shouldReconnectRef = useRef(true);
  const hasConnectedRef = useRef(false); // Prevent double mount in StrictMode

  // Send ping every 25s to keep connection alive (before 30s timeout)
  const startPingInterval = useCallback(() => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
    }

    pingIntervalRef.current = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send('ping');
      }
    }, 25000); // 25 seconds
  }, []);

  // Stop ping interval
  const stopPingInterval = useCallback(() => {
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
  }, []);

  // Handle incoming messages
  const handleMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);

        switch (message.type) {
          case 'sentiment_update':
            onSentimentUpdate?.(message.data as SentimentUpdate);
            break;

          case 'alert_triggered':
            onAlert?.(message.data as AlertTriggered);
            break;

          case 'rule_evaluation':
            onRuleEvaluation?.(message.data as RuleEvaluation);
            break;

          case 'camera_status':
            onCameraStatus?.(message.data as CameraStatus);
            break;

          case 'connected':
            onConnected?.(message.data);
            console.log('WebSocket connected:', message.data);
            break;

          case 'pong':
            // Keepalive response
            break;

          default:
            console.warn('Unknown message type:', message.type);
        }
      } catch (err) {
        console.error('Error parsing WebSocket message:', err);
      }
    },
    [onSentimentUpdate, onAlert, onRuleEvaluation, onCameraStatus, onConnected]
  );

  // Connect to WebSocket
  const connect = useCallback(() => {
    // Avoid multiple simultaneous connection attempts
    if (wsRef.current) {
      const state = wsRef.current.readyState;
      if (state === WebSocket.OPEN || state === WebSocket.CONNECTING) {
        return;
      }
    }

    setIsConnecting(true);
    setError(null);

    try {
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected');
        setIsConnected(true);
        setIsConnecting(false);
        setError(null);
        setReconnectAttempts(0);
        startPingInterval();
      };

      ws.onmessage = handleMessage;

      ws.onerror = (event) => {
        console.error('WebSocket error:', event);
        setError('WebSocket connection error');
        onError?.(event);
      };

      ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        setIsConnected(false);
        setIsConnecting(false);
        stopPingInterval();

        // Attempt reconnection with exponential backoff
        if (
          shouldReconnectRef.current &&
          autoReconnect &&
          reconnectAttempts < maxReconnectAttempts
        ) {
          const delay = Math.min(
            reconnectInterval * Math.pow(2, reconnectAttempts),
            30000 // Max 30s delay
          );

          console.log(
            `Reconnecting in ${delay}ms (attempt ${reconnectAttempts + 1}/${maxReconnectAttempts})`
          );

          reconnectTimeoutRef.current = setTimeout(() => {
            setReconnectAttempts((prev) => prev + 1);
            connect();
          }, delay);
        } else if (reconnectAttempts >= maxReconnectAttempts) {
          setError('Max reconnection attempts reached');
        }
      };
    } catch (err) {
      console.error('Error creating WebSocket:', err);
      setError('Failed to create WebSocket connection');
      setIsConnecting(false);
    }
  }, [
    url,
    autoReconnect,
    maxReconnectAttempts,
    reconnectAttempts,
    reconnectInterval,
    handleMessage,
    onError,
    startPingInterval,
    stopPingInterval,
  ]);

  // Send message
  const sendMessage = useCallback((message: string) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(message);
    } else {
      console.warn('WebSocket not connected, cannot send message');
    }
  }, []);

  // Connect on mount
  useEffect(() => {
    // Prevent double connection in React StrictMode
    if (hasConnectedRef.current) {
      return;
    }
    
    hasConnectedRef.current = true;
    shouldReconnectRef.current = true;
    
    // Call connect only once
    connect();

    // Cleanup on unmount
    return () => {
      shouldReconnectRef.current = false;
      stopPingInterval();

      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }

      if (wsRef.current) {
        wsRef.current.close(1000, 'Component unmounted');
        wsRef.current = null;
      }
      
      // Allow reconnection if component remounts
      hasConnectedRef.current = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url]); // Only depend on URL, not connect function

  return {
    isConnected,
    isConnecting,
    error,
    reconnectAttempts,
    sendMessage,
  };
};
