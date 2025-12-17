# Live Emotion Dashboard

## Overview

The Live Emotion Dashboard provides real-time monitoring and visualization of crowd sentiment analysis. It displays live emotion detection, sentiment scores, crowd size, and system alerts through an interactive web interface.

## Features

### 1. Live Sentiment Card
- Displays the dominant emotion detected in real-time
- Shows overall mood score (0.0 to 1.0)
- Indicates trend (↑ up, ↓ down, → stable)
- Updates every 1 second with smooth animations

### 2. Emotion Distribution Chart
- Pie chart visualization of emotion distribution
- Shows percentages for all 7 emotions:
  - Happy 😊
  - Sad 😢
  - Angry 😠
  - Surprised 😲
  - Neutral 😐
  - Fear 😨
  - Disgust 🤢
- Real-time updates with automatic decay for stale data

### 3. Crowd Size Gauge
- Current crowd size with threshold indicators:
  - Empty (0)
  - Low (1-5)
  - Moderate (6-20)
  - High (21-50)
  - Very High (50+)
- Sparkline chart showing crowd size history (last 5 minutes)

### 4. Mood Trend Chart
- Line chart showing mood score over time
- Displays last 30 minutes of data
- Color-coded by mood level:
  - Green: High mood (≥0.7)
  - Yellow: Moderate mood (0.4-0.7)
  - Red: Low mood (<0.4)
- Interactive tooltips with timestamp and emotion

### 5. Alert Feed Panel
- Real-time alert notifications
- Filter by severity: Info, Warning, Critical
- Actions:
  - Resolve alert
  - Dismiss alert
  - View details
- Shows relative timestamps (e.g., "5s ago", "2m ago")

## WebSocket Connection

The dashboard connects to the API Gateway WebSocket endpoint at:
```
ws://localhost:8000/ws/live
```

### Message Types

1. **sentiment_update**: Overall sentiment analysis
   ```json
   {
     "type": "sentiment_update",
     "timestamp": "2025-12-17T10:30:00Z",
     "data": {
       "camera_id": "camera_1",
       "sentiment_score": 0.75,
       "dominant_emotion": "happy",
       "face_count": 12
     }
   }
   ```

2. **emotion_event**: Individual emotion detection
   ```json
   {
     "type": "emotion_event",
     "timestamp": "2025-12-17T10:30:00Z",
     "data": {
       "camera_id": "camera_1",
       "emotion": "happy",
       "confidence": 0.89,
       "face_id": "face_123"
     }
   }
   ```

3. **alert**: System alert notification
   ```json
   {
     "type": "alert",
     "timestamp": "2025-12-17T10:30:00Z",
     "data": {
       "alert_id": "alert_456",
       "rule_id": "rule_123",
       "rule_name": "High Anger Detection",
       "message": "Anger threshold exceeded",
       "severity": "critical",
       "camera_id": "camera_1"
     }
   }
   ```

## Technical Implementation

### Components

- **LiveDashboard.tsx**: Main dashboard page
  - Manages WebSocket connection
  - Handles state updates
  - Coordinates all child components

- **LiveSentimentCard.tsx**: Sentiment display
  - Pulse animation on updates
  - Trend calculation
  - Emoji-based emotion display

- **EmotionDistributionChart.tsx**: Pie chart
  - Uses Recharts library
  - Custom tooltips
  - Automatic data normalization

- **CrowdSizeGauge.tsx**: Crowd monitoring
  - Threshold-based color coding
  - Sparkline area chart
  - Historical data tracking

- **MoodTrendChart.tsx**: Trend visualization
  - Line chart with time-series data
  - 30-minute rolling window
  - Dynamic color based on mood

- **AlertFeedPanel.tsx**: Alert management
  - Filter and sort capabilities
  - Alert state management
  - Action handlers

### State Management

The dashboard uses React hooks for state management:
- `useState` for local component state
- `useCallback` for memoized callbacks
- `useRef` for tracking previous values
- `useEffect` for WebSocket lifecycle

### Performance Optimizations

1. **Data Decay**: Emotion distribution decays 5% every 2 seconds to prevent stale data
2. **Rolling Windows**: Mood trend and crowd history maintain fixed-size buffers
3. **Memoization**: Event handlers are memoized to prevent unnecessary re-renders
4. **Conditional Updates**: Components only re-render when their specific data changes

## Usage

### Accessing the Dashboard

Navigate to `/live` in the dashboard application:
```
http://localhost:3000/live
```

### Connection Status

The dashboard displays connection status in the top-right corner:
- 🟢 Green pulsing dot: Connected
- 🔴 Red dot: Disconnected

### Automatic Reconnection

The WebSocket service automatically attempts to reconnect if the connection is lost:
- Maximum 5 reconnection attempts
- 2-second delay between attempts
- Exponential backoff on failures

## Configuration

### Environment Variables

Create a `.env.local` file:
```env
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/live
```

### Customization

Adjust thresholds and timings in the component files:
- Emotion decay rate: `LiveDashboard.tsx` line 180
- Crowd size thresholds: `CrowdSizeGauge.tsx` line 12
- Mood color ranges: `MoodTrendChart.tsx` line 50
- Alert history size: `LiveDashboard.tsx` line 144

## Troubleshooting

### WebSocket Connection Issues

1. **Cannot connect**: Verify API Gateway is running
2. **Frequent disconnections**: Check network stability
3. **No data updates**: Confirm emotion-detection service is publishing events

### Performance Issues

1. **Slow rendering**: Reduce data retention windows
2. **High memory usage**: Decrease history buffer sizes
3. **Choppy animations**: Disable emotion decay or reduce update frequency

## Development

### Running Locally

```bash
cd services/dashboard
npm install
npm run dev
```

### Building for Production

```bash
npm run build
npm start
```

### Testing WebSocket

Use the browser console to monitor WebSocket messages:
```javascript
// Enable verbose logging
localStorage.setItem('debug', 'websocket:*');
```

## Future Enhancements

- [ ] Multi-camera selection and switching
- [ ] Customizable dashboard layout
- [ ] Historical data playback
- [ ] Export data to CSV/JSON
- [ ] Alert acknowledgment workflow
- [ ] Camera health monitoring
- [ ] Performance metrics dashboard
- [ ] User preferences and themes

## Related Documentation

- [API Gateway WebSocket API](../../docs/API.md#websocket)
- [Emotion Detection Service](../emotion-detection/README.md)
- [Sentiment Analysis Service](../sentiment-analysis/README.md)
- [Alert Schema](../../docs/ALERT_SCHEMA.md)
