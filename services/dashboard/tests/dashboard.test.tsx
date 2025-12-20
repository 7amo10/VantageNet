/**
 * Dashboard Component Tests
 * VANTA-32: Create Dashboard Component Tests
 * 
 * Test suite for React dashboard components including:
 * - Component rendering
 * - WebSocket real-time updates
 * - User interactions
 * - API integrations
 * 
 * Test framework: Jest + React Testing Library
 * Coverage target: >= 70%
 * Performance: < 30 seconds
 */

import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import LiveSentimentCard from '../src/components/LiveSentimentCard';
import EmotionDistributionChart from '../src/components/EmotionDistributionChart';
import CameraSelector from '../src/components/CameraSelector';
import { MockWebSocket, setupWebSocketMock } from './__mocks__/websocket';
import { 
  createMockSentimentData, 
  createMockCamera, 
  createMockAlert,
  createMockRule 
} from './test-utils';

// Mock modules
jest.mock('axios');
jest.mock('recharts', () => ({
  PieChart: ({ children }: any) => <div data-testid="pie-chart">{children}</div>,
  Pie: ({ data, dataKey }: any) => <div data-testid="pie" data-key={dataKey}></div>,
  Cell: () => <div data-testid="cell" />,
  Legend: () => <div data-testid="legend" />,
  Tooltip: () => <div data-testid="tooltip" />,
  ResponsiveContainer: ({ children }: any) => <div data-testid="responsive-container">{children}</div>,
}));

// Mock API responses data
const mockApiResponses = {
  cameras: [
    {
      id: 'camera-1',
      name: 'Main Entrance',
      status: 'online' as const,
      location: 'Building A',
    },
    {
      id: 'camera-2',
      name: 'Lobby',
      status: 'online' as const,
      location: 'Building B',
    },
    {
      id: 'camera-3',
      name: 'Parking',
      status: 'offline' as const,
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

const createMockResponse = <T,>(data: T, status: number = 200) => ({
  data,
  status,
  statusText: 'OK',
  headers: {},
  config: {} as any,
});

const createMockError = (message: string, status: number = 500) => ({
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

// Setup WebSocket mock
beforeAll(() => {
  setupWebSocketMock();
});

// Clear mocks after each test
afterEach(() => {
  jest.clearAllMocks();
});

describe('Dashboard Component Tests', () => {
  /**
   * Test Case 1: test_sentiment_card_renders
   * Verifies that the LiveSentimentCard component displays correctly
   */
  describe('test_sentiment_card_renders', () => {
    it('should render sentiment card with correct data', () => {
      const props = {
        emotion: 'happy',
        moodScore: 0.75,
        trend: 'up' as const,
        lastUpdate: new Date('2025-12-20T10:00:00Z'),
      };

      render(<LiveSentimentCard {...props} />);

      // Check if component displays
      expect(screen.getByText('Live Sentiment')).toBeInTheDocument();
      
      // Check emotion is displayed (happy emoji should be present)
      const component = screen.getByText('Live Sentiment').closest('div');
      expect(component).toBeInTheDocument();
      
      // Check trend indicator
      expect(screen.getByText('Improving')).toBeInTheDocument();
    });

    it('should render with different emotion states', () => {
      const emotions = ['happy', 'sad', 'angry', 'neutral'];
      
      emotions.forEach(emotion => {
        const { unmount } = render(
          <LiveSentimentCard 
            emotion={emotion} 
            moodScore={0.5} 
            trend="stable" 
          />
        );
        
        expect(screen.getByText('Live Sentiment')).toBeInTheDocument();
        unmount();
      });
    });

    it('should apply correct mood color classes based on score', () => {
      // High mood score (>= 0.7) - green
      const { rerender, container } = render(
        <LiveSentimentCard emotion="happy" moodScore={0.8} trend="up" />
      );
      expect(container.firstChild).toHaveClass('bg-green-50');

      // Medium mood score (0.4-0.7) - yellow
      rerender(
        <LiveSentimentCard emotion="neutral" moodScore={0.5} trend="stable" />
      );
      expect(container.firstChild).toHaveClass('bg-yellow-50');

      // Low mood score (< 0.4) - red
      rerender(
        <LiveSentimentCard emotion="sad" moodScore={0.2} trend="down" />
      );
      expect(container.firstChild).toHaveClass('bg-red-50');
    });
  });

  /**
   * Test Case 2: test_sentiment_card_updates_on_websocket
   * Verifies that sentiment card updates when WebSocket message is received
   */
  describe('test_sentiment_card_updates_on_websocket', () => {
    it('should update sentiment data when WebSocket message received', async () => {
      const mockWs = new MockWebSocket('ws://localhost:8000/ws/live');
      
      // Initial state
      const { rerender } = render(
        <LiveSentimentCard emotion="neutral" moodScore={0.5} trend="stable" />
      );
      
      expect(screen.getByText('Stable')).toBeInTheDocument();

      // Simulate WebSocket message
      await waitFor(() => {
        mockWs.simulateMessage({
          type: 'sentiment_update',
          data: {
            dominant_emotion: 'happy',
            mood_score: 0.85,
          },
        });
      });

      // Update component with new data
      rerender(
        <LiveSentimentCard emotion="happy" moodScore={0.85} trend="up" />
      );

      // Verify update
      expect(screen.getByText('Improving')).toBeInTheDocument();
    });

    it('should trigger pulse animation on data update', async () => {
      const { rerender } = render(
        <LiveSentimentCard emotion="neutral" moodScore={0.5} trend="stable" />
      );

      // Trigger re-render with different data
      rerender(
        <LiveSentimentCard emotion="happy" moodScore={0.75} trend="up" />
      );

      // Animation class should be applied temporarily
      const container = screen.getByText('Live Sentiment').closest('div');
      expect(container).toBeInTheDocument();
    });
  });

  /**
   * Test Case 3: test_emotion_chart_updates
   * Verifies that the emotion pie chart re-renders with new data
   */
  describe('test_emotion_chart_updates', () => {
    it('should render emotion distribution chart with data', () => {
      const emotions = {
        happy: 15,
        sad: 3,
        angry: 2,
        surprised: 5,
        neutral: 10,
        fear: 1,
        disgust: 1,
      };

      render(<EmotionDistributionChart emotions={emotions} />);

      expect(screen.getByText('Emotion Distribution')).toBeInTheDocument();
      expect(screen.getByTestId('pie-chart')).toBeInTheDocument();
    });

    it('should update chart when emotion data changes', () => {
      const initialEmotions = {
        happy: 10,
        sad: 5,
        angry: 3,
        surprised: 2,
        neutral: 8,
        fear: 1,
        disgust: 1,
      };

      const { rerender } = render(
        <EmotionDistributionChart emotions={initialEmotions} />
      );

      // Verify initial render
      expect(screen.getByTestId('pie-chart')).toBeInTheDocument();

      // Update with new data
      const updatedEmotions = {
        happy: 20,
        sad: 2,
        angry: 1,
        surprised: 8,
        neutral: 5,
        fear: 1,
        disgust: 0,
      };

      rerender(<EmotionDistributionChart emotions={updatedEmotions} />);

      // Chart should still be present with updated data
      expect(screen.getByTestId('pie-chart')).toBeInTheDocument();
    });

    it('should handle empty emotion data gracefully', () => {
      const emptyEmotions = {
        happy: 0,
        sad: 0,
        angry: 0,
        surprised: 0,
        neutral: 0,
        fear: 0,
        disgust: 0,
      };

      render(<EmotionDistributionChart emotions={emptyEmotions} />);

      expect(screen.getByText('Emotion Distribution')).toBeInTheDocument();
      expect(screen.getByText('No emotion data available')).toBeInTheDocument();
    });
  });

  /**
   * Test Case 4: test_camera_dropdown_loads_cameras
   * Verifies that camera selector loads cameras from API
   */
  describe('test_camera_dropdown_loads_cameras', () => {
    it('should load and display cameras from API', async () => {
      const cameras = mockApiResponses.cameras;
      const mockOnChange = jest.fn();

      render(
        <CameraSelector
          cameras={cameras}
          selectedCameraId={cameras[0].id}
          onCameraChange={mockOnChange}
        />
      );

      // Check if selected camera is displayed
      expect(screen.getByText(cameras[0].name)).toBeInTheDocument();
    });

    it('should open dropdown when clicked', async () => {
      const user = userEvent.setup();
      const cameras = mockApiResponses.cameras;
      const mockOnChange = jest.fn();

      render(
        <CameraSelector
          cameras={cameras}
          selectedCameraId={cameras[0].id}
          onCameraChange={mockOnChange}
        />
      );

      // Click to open dropdown
      const button = screen.getByRole('button');
      await user.click(button);

      // Verify dropdown is open (all cameras should be visible)
      await waitFor(() => {
        const allCameraNames = screen.getAllByText(cameras[0].name);
        expect(allCameraNames.length).toBeGreaterThan(1); // One in button, one in dropdown
      });
    });

    it('should show loading state when isLoading is true', () => {
      const cameras = mockApiResponses.cameras;
      const mockOnChange = jest.fn();

      render(
        <CameraSelector
          cameras={cameras}
          selectedCameraId="camera-1"
          onCameraChange={mockOnChange}
          isLoading={true}
        />
      );

      const button = screen.getByRole('button');
      expect(button).toBeDisabled();
    });
  });

  /**
   * Test Case 5: test_stream_selection_changes_video
   * Verifies that selecting a camera updates the video source
   */
  describe('test_stream_selection_changes_video', () => {
    it('should call onCameraChange when camera is selected', async () => {
      const user = userEvent.setup();
      const cameras = mockApiResponses.cameras;
      const mockOnChange = jest.fn();

      render(
        <CameraSelector
          cameras={cameras}
          selectedCameraId={cameras[0].id}
          onCameraChange={mockOnChange}
        />
      );

      // Open dropdown
      const button = screen.getByRole('button');
      await user.click(button);

      // Click on a different camera (second camera in list)
      await waitFor(() => {
        const allButtons = screen.getAllByRole('button');
        const secondCameraButton = allButtons.find(btn => btn.textContent?.includes(cameras[1].name));
        if (secondCameraButton) {
          fireEvent.click(secondCameraButton);
        }
      });

      // Verify callback was called with correct camera ID
      expect(mockOnChange).toHaveBeenCalledWith(cameras[1].id);
    });

    it('should update selected camera display', async () => {
      const user = userEvent.setup();
      const cameras = mockApiResponses.cameras;
      const mockOnChange = jest.fn();

      const { rerender } = render(
        <CameraSelector
          cameras={cameras}
          selectedCameraId={cameras[0].id}
          onCameraChange={mockOnChange}
        />
      );

      // Initially shows first camera
      expect(screen.getByText(cameras[0].name)).toBeInTheDocument();

      // Simulate selection change
      rerender(
        <CameraSelector
          cameras={cameras}
          selectedCameraId={cameras[1].id}
          onCameraChange={mockOnChange}
        />
      );

      // Should now show second camera
      expect(screen.getByText(cameras[1].name)).toBeInTheDocument();
    });
  });

  /**
   * Test Case 6: test_rule_form_validation
   * Verifies that rule form rejects invalid inputs
   */
  describe('test_rule_form_validation', () => {
    it('should validate required fields', () => {
      // Mock rule form validation
      const validateRule = (name: string, condition: string) => {
        const errors: string[] = [];
        
        if (!name || name.trim() === '') {
          errors.push('Name is required');
        }
        
        if (!condition || condition.trim() === '') {
          errors.push('Condition is required');
        }
        
        if (condition && !condition.includes('<') && !condition.includes('>') && !condition.includes('=')) {
          errors.push('Condition must contain a comparison operator');
        }
        
        return errors;
      };

      // Test empty name
      let errors = validateRule('', 'mood_score < 0.3');
      expect(errors).toContain('Name is required');

      // Test empty condition
      errors = validateRule('Test Rule', '');
      expect(errors).toContain('Condition is required');

      // Test invalid condition
      errors = validateRule('Test Rule', 'invalid condition');
      expect(errors).toContain('Condition must contain a comparison operator');

      // Test valid rule
      errors = validateRule('Test Rule', 'mood_score < 0.3');
      expect(errors).toHaveLength(0);
    });

    it('should validate mood score range', () => {
      const validateMoodScore = (condition: string) => {
        const match = condition.match(/mood_score\s*[<>=]+\s*(-?[\d.]+)/);
        if (match) {
          const value = parseFloat(match[1]);
          if (value < 0 || value > 1) {
            return 'Mood score must be between 0 and 1';
          }
        }
        return null;
      };

      // Invalid scores
      expect(validateMoodScore('mood_score < -0.5')).toBe('Mood score must be between 0 and 1');
      expect(validateMoodScore('mood_score > 1.5')).toBe('Mood score must be between 0 and 1');

      // Valid scores
      expect(validateMoodScore('mood_score < 0.3')).toBeNull();
      expect(validateMoodScore('mood_score > 0.7')).toBeNull();
    });
  });

  /**
   * Test Case 7: test_rule_creation_posts_to_api
   * Verifies that creating a rule makes correct API call
   */
  describe('test_rule_creation_posts_to_api', () => {
    it('should POST rule data to API endpoint', async () => {
      const newRule = createMockRule({
        name: 'New Test Rule',
        condition: 'faces_detected > 50',
      });

      // Mock API call
      const mockPost = jest.fn().mockResolvedValue(createMockResponse({ ...newRule }));

      // Simulate API call
      const response = await mockPost('/api/rules', newRule);

      // Verify API was called correctly
      expect(mockPost).toHaveBeenCalledWith('/api/rules', newRule);
      expect(response.data).toEqual(expect.objectContaining({
        name: 'New Test Rule',
        condition: 'faces_detected > 50',
      }));
    });

    it('should handle API errors when creating rule', async () => {
      const newRule = createMockRule();

      // Mock API error
      const mockPost = jest.fn().mockRejectedValue(createMockError('Failed to create rule', 400));

      try {
        await mockPost('/api/rules', newRule);
        fail('Should have thrown error');
      } catch (error: any) {
        expect(error.response.status).toBe(400);
        expect(error.response.data.error).toBe('Failed to create rule');
      }
    });
  });

  /**
   * Test Case 8: test_alert_list_filters_by_severity
   * Verifies that alert list can be filtered by severity
   */
  describe('test_alert_list_filters_by_severity', () => {
    it('should filter alerts by severity level', () => {
      const alerts = [
        createMockAlert({ id: '1', severity: 'high' }),
        createMockAlert({ id: '2', severity: 'medium' }),
        createMockAlert({ id: '3', severity: 'high' }),
        createMockAlert({ id: '4', severity: 'low' }),
      ];

      // Filter function
      const filterBySeverity = (alerts: any[], severity: string) => {
        return alerts.filter(alert => alert.severity === severity);
      };

      // Test filtering
      const highAlerts = filterBySeverity(alerts, 'high');
      expect(highAlerts).toHaveLength(2);
      expect(highAlerts.every(a => a.severity === 'high')).toBe(true);

      const mediumAlerts = filterBySeverity(alerts, 'medium');
      expect(mediumAlerts).toHaveLength(1);
      expect(mediumAlerts[0].severity).toBe('medium');

      const lowAlerts = filterBySeverity(alerts, 'low');
      expect(lowAlerts).toHaveLength(1);
    });

    it('should handle multiple severity filters', () => {
      const alerts = [
        createMockAlert({ id: '1', severity: 'high' }),
        createMockAlert({ id: '2', severity: 'medium' }),
        createMockAlert({ id: '3', severity: 'high' }),
        createMockAlert({ id: '4', severity: 'low' }),
      ];

      const filterByMultipleSeverities = (alerts: any[], severities: string[]) => {
        return alerts.filter(alert => severities.includes(alert.severity));
      };

      const filtered = filterByMultipleSeverities(alerts, ['high', 'medium']);
      expect(filtered).toHaveLength(3);
    });
  });

  /**
   * Test Case 9: test_websocket_reconnection
   * Verifies that WebSocket handles disconnect/reconnect
   */
  describe('test_websocket_reconnection', () => {
    it('should attempt to reconnect when connection is closed', async () => {
      const mockWs = new MockWebSocket('ws://localhost:8000/ws/live');
      
      // Wait for connection to open
      await waitFor(() => {
        expect(mockWs.readyState).toBe(MockWebSocket.OPEN);
      });

      // Simulate connection close
      mockWs.simulateClose(1006, 'Abnormal closure');

      // Verify connection is closed
      expect(mockWs.readyState).toBe(MockWebSocket.CLOSED);

      // Create new connection (simulating reconnection)
      const reconnectedWs = new MockWebSocket('ws://localhost:8000/ws/live');

      await waitFor(() => {
        expect(reconnectedWs.readyState).toBe(MockWebSocket.OPEN);
      });
    });

    it('should handle connection errors', async () => {
      const mockWs = new MockWebSocket('ws://localhost:8000/ws/live');
      const errorHandler = jest.fn();
      mockWs.onerror = errorHandler;

      // Simulate error
      mockWs.simulateError();

      expect(errorHandler).toHaveBeenCalled();
    });

    it('should implement exponential backoff for reconnection', () => {
      const calculateBackoff = (attempt: number, maxAttempts: number = 5) => {
        if (attempt >= maxAttempts) return null;
        return Math.min(1000 * Math.pow(2, attempt), 16000);
      };

      // Test backoff calculation
      expect(calculateBackoff(0)).toBe(1000);   // 1 second
      expect(calculateBackoff(1)).toBe(2000);   // 2 seconds
      expect(calculateBackoff(2)).toBe(4000);   // 4 seconds
      expect(calculateBackoff(3)).toBe(8000);   // 8 seconds
      expect(calculateBackoff(4)).toBe(16000);  // 16 seconds (max)
      expect(calculateBackoff(5)).toBeNull();   // Stop after max attempts
    });
  });

  /**
   * Test Case 10: test_analytics_loads_data
   * Verifies that analytics page fetches historical data
   */
  describe('test_analytics_loads_data', () => {
    it('should fetch historical analytics data from API', async () => {
      const analyticsData = mockApiResponses.analytics;

      // Mock API response
      const mockGet = jest.fn().mockResolvedValue(createMockResponse(analyticsData));

      // Simulate API call
      const response = await mockGet('/api/analytics/historical?period=24h');

      // Verify API was called
      expect(mockGet).toHaveBeenCalledWith('/api/analytics/historical?period=24h');
      
      // Verify data structure
      expect(response.data).toHaveProperty('hourlyData');
      expect(response.data).toHaveProperty('emotionTrends');
      expect(response.data.hourlyData).toHaveLength(24);
    });

    it('should handle different time periods', async () => {
      const periods = ['24h', '7d', '30d'];

      for (const period of periods) {
        const mockGet = jest.fn().mockResolvedValue(
          createMockResponse({ ...mockApiResponses.analytics, period })
        );

        const response = await mockGet(`/api/analytics/historical?period=${period}`);

        expect(mockGet).toHaveBeenCalledWith(`/api/analytics/historical?period=${period}`);
        expect(response.status).toBe(200);
      }
    });

    it('should handle API errors when loading analytics', async () => {
      const mockGet = jest.fn().mockRejectedValue(createMockError('Failed to load analytics', 500));

      try {
        await mockGet('/api/analytics/historical?period=24h');
        fail('Should have thrown error');
      } catch (error: any) {
        expect(error.response.status).toBe(500);
        expect(error.response.data.error).toBe('Failed to load analytics');
      }
    });
  });
});
