// Mock axios for API testing
const mockAxios = {
  create: jest.fn(function() { return mockAxios; }),
  get: jest.fn(),
  post: jest.fn(),
  put: jest.fn(),
  delete: jest.fn(),
  patch: jest.fn(),
  request: jest.fn(),
  defaults: {
    headers: {
      common: {},
    },
  },
  interceptors: {
    request: {
      use: jest.fn(),
      eject: jest.fn(),
    },
    response: {
      use: jest.fn(),
      eject: jest.fn(),
    },
  },
};

// Mock response helpers
export const createMockResponse = <T>(data: T, status: number = 200) => ({
  data,
  status,
  statusText: 'OK',
  headers: {},
  config: {} as any,
});

export const createMockError = (message: string, status: number = 500) => ({
  message,
  response: {
    data: { error: message },
    status,
    statusText: 'Error',
    headers: {},
    config: {} as any,
  },
  isAxiosError: true,
});

// Mock API responses
export const mockApiResponses = {
  cameras: [
    {
      id: 'camera-1',
      name: 'Main Entrance',
      status: 'online',
      location: 'Building A',
    },
    {
      id: 'camera-2',
      name: 'Lobby',
      status: 'online',
      location: 'Building B',
    },
    {
      id: 'camera-3',
      name: 'Parking',
      status: 'offline',
      location: 'Outdoor',
    },
  ],
  sentimentData: {
    timestamp: new Date().toISOString(),
    crowd_sentiment: {
      dominant_emotion: 'happy',
      mood_score: 0.75,
      emotions: {
        happy: 15,
        sad: 3,
        angry: 2,
        surprised: 5,
        neutral: 10,
        fear: 1,
        disgust: 1,
      },
      faces_detected: 37,
    },
  },
  alerts: [
    {
      id: 'alert-1',
      type: 'sentiment',
      severity: 'high',
      message: 'Negative sentiment spike detected',
      timestamp: new Date().toISOString(),
      camera_id: 'camera-1',
    },
    {
      id: 'alert-2',
      type: 'crowd',
      severity: 'medium',
      message: 'High crowd density',
      timestamp: new Date().toISOString(),
      camera_id: 'camera-2',
    },
  ],
  rules: [
    {
      id: 'rule-1',
      name: 'High Negative Sentiment',
      condition: 'mood_score < 0.3',
      severity: 'high',
      enabled: true,
    },
    {
      id: 'rule-2',
      name: 'Crowd Capacity',
      condition: 'faces_detected > 50',
      severity: 'medium',
      enabled: true,
    },
  ],
  analytics: {
    hourlyData: Array.from({ length: 24 }, (_, i) => ({
      hour: i,
      moodScore: Math.random(),
      facesDetected: Math.floor(Math.random() * 50),
    })),
    emotionTrends: {
      happy: [0.2, 0.3, 0.4, 0.5, 0.6],
      sad: [0.1, 0.15, 0.12, 0.08, 0.05],
      angry: [0.05, 0.08, 0.1, 0.07, 0.04],
    },
  },
};

export default mockAxios;
