/**
 * Test Utilities and Helper Functions
 * Common utilities for creating mock data in tests
 */

export const createMockSentimentData = (overrides = {}) => ({
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
  ...overrides,
});

export const createMockCamera = (overrides = {}) => ({
  id: `camera-${Date.now()}`,
  name: 'Test Camera',
  status: 'online' as const,
  location: 'Test Location',
  ...overrides,
});

export const createMockAlert = (overrides = {}) => ({
  id: `alert-${Date.now()}`,
  type: 'sentiment',
  severity: 'high',
  message: 'Test alert message',
  timestamp: new Date().toISOString(),
  camera_id: 'camera-1',
  ...overrides,
});

export const createMockRule = (overrides = {}) => ({
  id: `rule-${Date.now()}`,
  name: 'Test Rule',
  condition: 'mood_score < 0.3',
  severity: 'high',
  enabled: true,
  ...overrides,
});
