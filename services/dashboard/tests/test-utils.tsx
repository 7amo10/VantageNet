// Test utilities and helpers
import { render, RenderOptions } from '@testing-library/react';
import { ReactElement } from 'react';

// Custom render function with providers if needed
export function renderWithProviders(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) {
  // For now, just use default render
  // Add providers here if needed in the future (e.g., Context providers)
  return render(ui, options);
}

// Helper to wait for async updates
export const waitForAsync = () => new Promise(resolve => setTimeout(resolve, 0));

// Helper to create mock sentiment data
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

// Helper to create mock camera data
export const createMockCamera = (overrides = {}) => ({
  id: 'camera-1',
  name: 'Test Camera',
  status: 'online' as const,
  location: 'Test Location',
  ...overrides,
});

// Helper to create mock alert data
export const createMockAlert = (overrides = {}) => ({
  id: 'alert-1',
  type: 'sentiment',
  severity: 'high',
  message: 'Test alert',
  timestamp: new Date().toISOString(),
  camera_id: 'camera-1',
  ...overrides,
});

// Helper to create mock rule data
export const createMockRule = (overrides = {}) => ({
  id: 'rule-1',
  name: 'Test Rule',
  condition: 'mood_score < 0.3',
  severity: 'high',
  enabled: true,
  ...overrides,
});

// Helper to simulate WebSocket message
export const createWebSocketMessage = (type: string, data: any) => ({
  type,
  data,
  timestamp: new Date().toISOString(),
});

// Re-export testing library utilities
export * from '@testing-library/react';
export { default as userEvent } from '@testing-library/user-event';
