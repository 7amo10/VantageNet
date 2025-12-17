# Live Video Stream Viewer

## Overview

The Live Video Stream Viewer provides real-time HLS video streaming with emotion detection overlays. It displays camera feeds with color-coded bounding boxes around detected faces, showing emotion labels and confidence scores in real-time.

## Features

### 1. HLS Video Streaming
- **Browser-compatible**: Uses HLS (HTTP Live Streaming) for universal browser support
- **Low latency**: Stream latency < 3 seconds
- **hls.js library**: JavaScript HLS player with adaptive bitrate streaming
- **Native Safari support**: Falls back to native HLS for Safari browsers
- **Auto-recovery**: Automatically reconnects on network errors

### 2. Camera Selection
- **Dropdown selector**: Easy camera switching without page reload
- **Auto-population**: Fetches available cameras from API Gateway
- **Status indicators**: Shows online/offline status for each camera
- **Currently playing**: Highlights the active camera
- **Metadata display**: Shows camera name and location

### 3. Face Detection Overlay
- **Real-time annotations**: Bounding boxes drawn via HTML5 canvas
- **Emotion labels**: Shows emotion name and confidence percentage
- **Color-coded boxes**: Visual emotion identification
  - 🟢 Happy: Green
  - 🔴 Angry: Red
  - 🔵 Sad: Blue
  - 🟡 Surprised: Amber
  - ⚪ Neutral: Gray
  - 🟣 Fear: Purple
  - 🟠 Disgust: Orange
- **Face counter**: Displays total detected faces

### 4. Stream Controls
- **Play/Pause**: Manual video control
- **Annotation toggle**: Show/hide bounding boxes and labels
- **Status indicator**: Live, Connecting, Error, or Offline
- **Stream info**: Camera ID and stream URL display

### 5. Performance Optimization
- **Canvas animation**: Efficient requestAnimationFrame rendering
- **Face buffer**: Keeps last 20 detected faces
- **Scaled coordinates**: Responsive bounding box scaling
- **Low memory**: < 500MB for video playback

## Components

### VideoStreamPlayer.tsx

Main HLS video player with canvas overlay for annotations.

**Props:**
- `cameraId`: Camera identifier
- `streamUrl`: HLS stream URL (m3u8 format)
- `faces`: Array of detected faces with bounding boxes
- `autoPlay`: Auto-start playback (default: true)
- `showAnnotations`: Display face overlays (default: true)
- `onError`: Error callback
- `onStreamReady`: Stream ready callback

**Features:**
- HLS.js initialization with low-latency mode
- Canvas overlay synchronized with video
- Emotion-based color coding
- Automatic error recovery
- Play/pause controls

### CameraSelector.tsx

Dropdown component for camera selection.

**Props:**
- `cameras`: Array of camera objects
- `selectedCameraId`: Currently selected camera ID
- `onCameraChange`: Callback when camera changes
- `isLoading`: Loading state

**Features:**
- Dropdown menu with camera list
- Status indicators (online/offline)
- Selected camera highlighting
- Location metadata display

### Video Page (/app/video/page.tsx)

Main page that integrates video player and camera selector.

**Features:**
- Camera fetching from API
- WebSocket integration for real-time faces
- Stream statistics tracking
- Annotation toggle control
- Responsive layout

## API Integration

### Camera List API

**Endpoint:** `GET http://localhost:8000/api/cameras`

**Response:**
```json
{
  "cameras": [
    {
      "id": "camera_1",
      "name": "Main Entrance",
      "status": "online",
      "location": "Building A - Floor 1"
    }
  ]
}
```

### HLS Stream URL

**Format:** `http://localhost:8001/stream/{camera_id}.m3u8`

**Example:** `http://localhost:8001/stream/camera_1.m3u8`

### WebSocket Emotion Events

**Event Type:** `emotion_event`

**Payload:**
```json
{
  "type": "emotion_event",
  "timestamp": "2025-12-17T12:00:00Z",
  "data": {
    "camera_id": "camera_1",
    "face_id": "face_123",
    "emotion": "happy",
    "confidence": 0.89,
    "bbox": {
      "x": 100,
      "y": 150,
      "width": 80,
      "height": 100
    }
  }
}
```

## Usage

### Accessing the Video Viewer

Navigate to `/video` in the dashboard:
```
http://localhost:3000/video
```

### Selecting a Camera

1. Click the camera dropdown
2. Select desired camera from list
3. Stream loads automatically
4. Annotations appear in real-time

### Toggling Annotations

- Check/uncheck "Show Annotations" toggle
- Annotations can be hidden for cleaner view
- Face counter still displays total count

### Manual Controls

- **Play/Pause**: Click button in bottom-right corner
- **Stream Status**: Check indicator in top-left corner
- **Face Count**: View counter in bottom-left corner

## Technical Implementation

### HLS.js Configuration

```typescript
const hls = new Hls({
  enableWorker: true,
  lowLatencyMode: true,
  backBufferLength: 90,
});
```

### Canvas Drawing

Bounding boxes are drawn using HTML5 Canvas API:

```typescript
// Scale coordinates to canvas size
const scaleX = canvas.width / video.videoWidth;
const scaleY = canvas.height / video.videoHeight;

// Draw box
ctx.strokeStyle = emotionColor;
ctx.lineWidth = 3;
ctx.strokeRect(x, y, width, height);

// Draw label
ctx.fillStyle = emotionColor;
ctx.fillRect(labelX, labelY, textWidth + 10, 20);
ctx.fillStyle = '#ffffff';
ctx.fillText(label, labelX + 5, labelY + 15);
```

### Animation Loop

```typescript
const drawAnnotations = () => {
  // Clear canvas
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  
  // Draw each face
  faces.forEach(face => {
    // Draw bounding box and label
  });
  
  // Continue loop
  requestAnimationFrame(drawAnnotations);
};
```

### Error Handling

**Network Errors:**
- Automatic reconnection every 5 seconds
- Displays "Reconnecting..." status
- Tracks reconnection attempts

**Media Errors:**
- Attempts automatic media recovery
- Falls back to error state if recovery fails

**Fatal Errors:**
- Displays error message overlay
- Provides manual retry option

## Performance Metrics

### Stream Performance
- **Latency**: < 3 seconds
- **FPS**: 30 fps (video native)
- **Resolution**: Depends on source (typically 720p or 1080p)

### Browser Compatibility
- ✅ Chrome/Edge: Full support via hls.js
- ✅ Firefox: Full support via hls.js
- ✅ Safari: Native HLS support
- ✅ Mobile browsers: Full support

### Memory Usage
- **Idle**: ~100MB
- **Single stream**: ~250MB
- **With annotations**: ~350MB
- **Target**: < 500MB

## Configuration

### Environment Variables

Create `.env.local`:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_STREAM_URL=http://localhost:8001
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/live
```

### Stream Settings

Adjust in VideoStreamPlayer.tsx:
```typescript
// HLS configuration
const hls = new Hls({
  enableWorker: true,        // Use web worker
  lowLatencyMode: true,      // Reduce buffering
  backBufferLength: 90,      // Keep 90s buffer
  maxBufferLength: 30,       // Max 30s ahead
});
```

### Annotation Settings

```typescript
// Face buffer size
const MAX_FACES = 20;

// Canvas refresh rate
requestAnimationFrame(drawAnnotations); // 60 FPS

// Bounding box style
const BORDER_WIDTH = 3;
const LABEL_HEIGHT = 20;
```

## Troubleshooting

### Stream Not Loading

**Problem**: "Stream Offline" or stuck on "Connecting..."

**Solutions:**
1. Check Video Ingestion service is running
2. Verify stream URL is accessible: `http://localhost:8001/stream/camera_1.m3u8`
3. Check camera is online in selector
4. Clear browser cache and reload

### No Annotations Appearing

**Problem**: Video plays but no bounding boxes

**Solutions:**
1. Verify "Show Annotations" toggle is enabled
2. Check WebSocket connection status
3. Confirm emotion-detection service is publishing events
4. Check browser console for errors

### High CPU/Memory Usage

**Problem**: Browser becomes slow or unresponsive

**Solutions:**
1. Disable annotations temporarily
2. Close other browser tabs
3. Reduce video quality in Video Ingestion config
4. Check for memory leaks in dev tools

### Stream Stuttering

**Problem**: Video playback is choppy

**Solutions:**
1. Check network bandwidth
2. Reduce HLS segment size
3. Increase buffer length
4. Disable other network-heavy applications

## Development

### Running Locally

```bash
cd services/dashboard
npm install hls.js
npm run dev
```

### Testing Video Stream

Create test HLS stream:
```bash
ffmpeg -re -i test_video.mp4 \
  -c:v libx264 -c:a aac \
  -f hls -hls_time 2 -hls_list_size 3 \
  output.m3u8
```

### Testing WebSocket Annotations

Send test emotion event:
```javascript
ws.send(JSON.stringify({
  type: 'emotion_event',
  data: {
    camera_id: 'camera_1',
    face_id: 'test_face',
    emotion: 'happy',
    confidence: 0.95,
    bbox: { x: 100, y: 100, width: 80, height: 100 }
  }
}));
```

## Multi-Camera Layout (Future)

### 2x2 Grid Layout

Planned feature for displaying multiple camera streams simultaneously:

```typescript
<div className="grid grid-cols-2 gap-4">
  {cameras.slice(0, 4).map(camera => (
    <VideoStreamPlayer
      key={camera.id}
      cameraId={camera.id}
      streamUrl={getStreamUrl(camera.id)}
    />
  ))}
</div>
```

**Requirements:**
- Load balancing for multiple streams
- Synchronized playback
- Per-camera face tracking
- Grid layout controls

## Related Documentation

- [Video Ingestion Service](../video-ingestion/README.md)
- [Emotion Detection Service](../emotion-detection/README.md)
- [API Gateway WebSocket](../../docs/API.md#websocket)
- [HLS.js Documentation](https://github.com/video-dev/hls.js/)

## Future Enhancements

- [ ] Multi-camera grid layout (2x2, 3x3)
- [ ] Recording and playback controls
- [ ] Snapshot capture functionality
- [ ] Fullscreen mode
- [ ] Picture-in-picture support
- [ ] Zoom and pan controls
- [ ] Emotion history timeline
- [ ] Face tracking across frames
- [ ] Export annotated video clips
- [ ] Custom annotation styles
