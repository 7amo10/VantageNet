import axios, { AxiosInstance, AxiosError } from 'axios';

/**
 * API Client Service for VantageNet Dashboard
 * Provides typed HTTP client for API Gateway communication
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Create Axios instance with default config
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
apiClient.interceptors.request.use(
  (config) => {
    console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('[API Request Error]', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    console.log(`[API Response] ${response.status} ${response.config.url}`);
    return response;
  },
  (error: AxiosError) => {
    console.error('[API Response Error]', {
      url: error.config?.url,
      status: error.response?.status,
      message: error.message,
    });
    return Promise.reject(error);
  }
);

// Type definitions
export interface Camera {
  camera_id: string;
  name: string;
  source_type: 'rtsp' | 'file' | 'http';
  source_url: string;
  status: 'active' | 'inactive' | 'error';
  location?: string;
  created_at: string;
  updated_at: string;
}

export interface CameraCreate {
  name: string;
  source_type: 'rtsp' | 'file' | 'http';
  source_url: string;
  location?: string;
}

export interface Rule {
  rule_id: string;
  name: string;
  description?: string;
  condition: {
    metric: string;
    operator: string;
    threshold: number;
  };
  action: 'alert' | 'log' | 'webhook';
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface RuleCreate {
  name: string;
  description?: string;
  condition: {
    metric: string;
    operator: string;
    threshold: number;
  };
  action: 'alert' | 'log' | 'webhook';
  is_active?: boolean;
}

export interface SentimentSummary {
  sentiment_score: number;
  dominant_emotion: string;
  total_faces: number;
  camera_count: number;
  period_start: string;
  period_end: string;
}

export interface AnalyticsSummary {
  current_sentiment: SentimentSummary;
  emotion_distribution: Record<string, number>;
}

export interface HealthResponse {
  status: string;
  memory_usage_mb: number;
  services: {
    websocket: {
      active_connections: number;
      uptime_seconds: number;
    };
  };
}

// API Service methods
class ApiService {
  // Health check
  async getHealth(): Promise<HealthResponse> {
    const response = await apiClient.get<HealthResponse>('/health');
    return response.data;
  }

  // Camera endpoints
  async getCameras(): Promise<Camera[]> {
    const response = await apiClient.get<Camera[]>('/api/cameras');
    return response.data;
  }

  async getCamera(cameraId: string): Promise<Camera> {
    const response = await apiClient.get<Camera>(`/api/cameras/${cameraId}`);
    return response.data;
  }

  async createCamera(camera: CameraCreate): Promise<Camera> {
    const response = await apiClient.post<Camera>('/api/cameras', camera);
    return response.data;
  }

  async updateCamera(cameraId: string, camera: Partial<CameraCreate>): Promise<Camera> {
    const response = await apiClient.put<Camera>(`/api/cameras/${cameraId}`, camera);
    return response.data;
  }

  async deleteCamera(cameraId: string): Promise<void> {
    await apiClient.delete(`/api/cameras/${cameraId}`);
  }

  // Rule endpoints
  async getRules(): Promise<Rule[]> {
    const response = await apiClient.get<Rule[]>('/api/rules');
    return response.data;
  }

  async getRule(ruleId: string): Promise<Rule> {
    const response = await apiClient.get<Rule>(`/api/rules/${ruleId}`);
    return response.data;
  }

  async createRule(rule: RuleCreate): Promise<Rule> {
    const response = await apiClient.post<Rule>('/api/rules', rule);
    return response.data;
  }

  async updateRule(ruleId: string, rule: Partial<RuleCreate>): Promise<Rule> {
    const response = await apiClient.put<Rule>(`/api/rules/${ruleId}`, rule);
    return response.data;
  }

  async deleteRule(ruleId: string): Promise<void> {
    await apiClient.delete(`/api/rules/${ruleId}`);
  }

  // Analytics endpoints
  async getAnalyticsSummary(): Promise<AnalyticsSummary> {
    const response = await apiClient.get<AnalyticsSummary>('/api/analytics/summary');
    return response.data;
  }
}

// Export singleton instance
export const api = new ApiService();

// Export Axios instance for custom requests
export { apiClient };
