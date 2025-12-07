/**
 * WebSocket Client Service for VantageNet Dashboard
 * Handles real-time communication with API Gateway
 */

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/live';

export type WebSocketMessageType = 
  | 'sentiment_update'
  | 'emotion_event'
  | 'alert'
  | 'camera_status'
  | 'system_status';

export interface WebSocketMessage {
  type: WebSocketMessageType;
  timestamp: string;
  data: any;
}

export interface SentimentUpdate {
  camera_id: string;
  sentiment_score: number;
  dominant_emotion: string;
  face_count: number;
}

export interface EmotionEvent {
  camera_id: string;
  emotion: string;
  confidence: number;
  face_id?: string;
}

export interface Alert {
  alert_id: string;
  rule_id: string;
  message: string;
  severity: 'low' | 'medium' | 'high';
  camera_id?: string;
}

export interface CameraStatusUpdate {
  camera_id: string;
  status: 'active' | 'inactive' | 'error';
  message?: string;
}

type MessageHandler = (message: WebSocketMessage) => void;
type ConnectionHandler = () => void;
type ErrorHandler = (error: Event) => void;

/**
 * WebSocket Manager for real-time dashboard updates
 * Implements reconnection logic and event handling
 */
class WebSocketManager {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 2000;
  private isIntentionallyClosed = false;
  
  private messageHandlers: Set<MessageHandler> = new Set();
  private connectionHandlers: Set<ConnectionHandler> = new Set();
  private disconnectionHandlers: Set<ConnectionHandler> = new Set();
  private errorHandlers: Set<ErrorHandler> = new Set();

  constructor() {
    if (typeof window !== 'undefined') {
      this.connect();
    }
  }

  /**
   * Establish WebSocket connection to API Gateway
   */
  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      console.log('[WebSocket] Already connected');
      return;
    }

    this.isIntentionallyClosed = false;
    
    try {
      console.log(`[WebSocket] Connecting to ${WS_URL}`);
      this.ws = new WebSocket(WS_URL);

      this.ws.onopen = () => {
        console.log('[WebSocket] Connected successfully');
        this.reconnectAttempts = 0;
        this.connectionHandlers.forEach(handler => handler());
      };

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          console.log('[WebSocket] Message received:', message.type);
          this.messageHandlers.forEach(handler => handler(message));
        } catch (error) {
          console.error('[WebSocket] Failed to parse message:', error);
        }
      };

      this.ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
        this.errorHandlers.forEach(handler => handler(error));
      };

      this.ws.onclose = () => {
        console.log('[WebSocket] Connection closed');
        this.disconnectionHandlers.forEach(handler => handler());
        
        if (!this.isIntentionallyClosed) {
          this.attemptReconnect();
        }
      };
    } catch (error) {
      console.error('[WebSocket] Connection error:', error);
      this.attemptReconnect();
    }
  }

  /**
   * Attempt to reconnect with exponential backoff
   */
  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[WebSocket] Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    
    console.log(`[WebSocket] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
    
    setTimeout(() => {
      this.connect();
    }, delay);
  }

  /**
   * Close WebSocket connection
   */
  disconnect(): void {
    console.log('[WebSocket] Disconnecting');
    this.isIntentionallyClosed = true;
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * Check if WebSocket is connected
   */
  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Send message to server
   */
  send(message: any): void {
    if (!this.isConnected()) {
      console.warn('[WebSocket] Cannot send message - not connected');
      return;
    }

    try {
      this.ws?.send(JSON.stringify(message));
      console.log('[WebSocket] Message sent:', message);
    } catch (error) {
      console.error('[WebSocket] Failed to send message:', error);
    }
  }

  // Event handler registration
  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  onConnect(handler: ConnectionHandler): () => void {
    this.connectionHandlers.add(handler);
    return () => this.connectionHandlers.delete(handler);
  }

  onDisconnect(handler: ConnectionHandler): () => void {
    this.disconnectionHandlers.add(handler);
    return () => this.disconnectionHandlers.delete(handler);
  }

  onError(handler: ErrorHandler): () => void {
    this.errorHandlers.add(handler);
    return () => this.errorHandlers.delete(handler);
  }

  // Typed message handlers for convenience
  onSentimentUpdate(handler: (data: SentimentUpdate) => void): () => void {
    return this.onMessage((message) => {
      if (message.type === 'sentiment_update') {
        handler(message.data);
      }
    });
  }

  onEmotionEvent(handler: (data: EmotionEvent) => void): () => void {
    return this.onMessage((message) => {
      if (message.type === 'emotion_event') {
        handler(message.data);
      }
    });
  }

  onAlert(handler: (data: Alert) => void): () => void {
    return this.onMessage((message) => {
      if (message.type === 'alert') {
        handler(message.data);
      }
    });
  }

  onCameraStatus(handler: (data: CameraStatusUpdate) => void): () => void {
    return this.onMessage((message) => {
      if (message.type === 'camera_status') {
        handler(message.data);
      }
    });
  }
}

// Export singleton instance
export const websocket = new WebSocketManager();

// Export mock data for development
export const mockWebSocketData = {
  sentimentUpdate: {
    type: 'sentiment_update' as const,
    timestamp: new Date().toISOString(),
    data: {
      camera_id: 'cam_001',
      sentiment_score: 0.65,
      dominant_emotion: 'happy',
      face_count: 3,
    },
  },
  emotionEvent: {
    type: 'emotion_event' as const,
    timestamp: new Date().toISOString(),
    data: {
      camera_id: 'cam_001',
      emotion: 'happy',
      confidence: 0.92,
      face_id: 'face_123',
    },
  },
  alert: {
    type: 'alert' as const,
    timestamp: new Date().toISOString(),
    data: {
      alert_id: 'alert_001',
      rule_id: 'rule_001',
      message: 'High negative sentiment detected',
      severity: 'high' as const,
      camera_id: 'cam_001',
    },
  },
};
