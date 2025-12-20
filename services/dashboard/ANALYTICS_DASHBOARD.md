# Analytics Dashboard - VANTA-30

## Overview

The Analytics Dashboard provides comprehensive insights into emotion detection data, sentiment trends, and system performance. It offers visualization tools, customizable filters, and data export capabilities for historical analysis.

## Features

### 1. **Overview Statistics Cards**
- **Total Detections**: Count of all face detections in selected period
- **Unique Faces**: Number of distinct faces identified
- **Average Confidence**: Mean confidence score of all detections

### 2. **Timeline Visualization**
- Line chart showing detections, emotions, and sentiments over time
- Configurable intervals: hourly, daily, weekly, monthly
- Interactive tooltips with detailed metrics

### 3. **Emotion Distribution**
- Pie chart displaying emotion breakdown
- Color-coded categories (happy, sad, angry, neutral, etc.)
- Percentage and count labels

### 4. **Sentiment Analysis**
- Pie chart showing positive/neutral/negative distribution
- Real-time sentiment trend tracking
- Comparison metrics

### 5. **Camera Performance**
- Bar chart comparing detection counts across cameras
- Active time tracking per camera
- Performance benchmarking

### 6. **Advanced Filtering**
- **Date Range**: Custom start/end dates or quick presets (Today, Last 7/30/90 Days)
- **Camera Selection**: Filter by specific camera or view all
- **Time Interval**: Adjust granularity (hour/day/week/month)

### 7. **Data Export**
- CSV export functionality
- Includes all analytics data within selected filters
- Formatted for Excel and data analysis tools

## Component Architecture

### Frontend Components

#### `AnalyticsFilters.tsx`
Provides filter controls and date range selection:
- Quick range presets (Today, 7d, 30d, 90d)
- Custom date picker with validation
- Camera dropdown populated from API
- Time interval selector
- Export button

#### `AnalyticsCharts.tsx`
Renders all visualization components:
- Uses Recharts library for charts
- Responsive design for all screen sizes
- Color-coded emotion/sentiment categories
- Interactive legends and tooltips

#### `Analytics.tsx` (Page)
Main analytics page component:
- State management for filters and data
- API integration with error handling
- Loading states and retry logic
- Coordinates all child components

### Backend API Endpoints

All endpoints under `/api/analytics/stats/`:

#### `GET /stats/timeline`
Returns time-series data for detections, emotions, and sentiments.

**Query Parameters:**
- `start_date` (required): Start date in YYYY-MM-DD format
- `end_date` (required): End date in YYYY-MM-DD format
- `interval` (optional): Time bucket size - "hour" | "day" | "week" | "month" (default: "hour")
- `camera_id` (optional): Filter by specific camera UUID

**Response:**
```json
{
  "timeline": [
    {
      "timestamp": "2024-12-20T10:00:00",
      "detections": 45,
      "emotions": 43,
      "sentiments": 42
    }
  ]
}
```

#### `GET /stats/detections`
Returns detection statistics summary.

**Query Parameters:**
- `start_date`, `end_date`, `camera_id` (same as above)

**Response:**
```json
{
  "total_detections": 1547,
  "unique_faces": 423,
  "avg_confidence": 0.8742
}
```

#### `GET /stats/emotions`
Returns emotion distribution breakdown.

**Query Parameters:**
- `start_date`, `end_date`, `camera_id`

**Response:**
```json
{
  "emotions": [
    {
      "emotion": "happy",
      "count": 523,
      "percentage": 45.2
    },
    {
      "emotion": "neutral",
      "count": 315,
      "percentage": 27.3
    }
  ]
}
```

#### `GET /stats/sentiments`
Returns sentiment distribution breakdown.

**Query Parameters:**
- `start_date`, `end_date`, `camera_id`

**Response:**
```json
{
  "sentiments": [
    {
      "sentiment": "positive",
      "count": 678,
      "percentage": 58.5
    },
    {
      "sentiment": "neutral",
      "count": 312,
      "percentage": 26.9
    },
    {
      "sentiment": "negative",
      "count": 169,
      "percentage": 14.6
    }
  ]
}
```

#### `GET /stats/cameras`
Returns per-camera performance statistics.

**Query Parameters:**
- `start_date`, `end_date`

**Response:**
```json
{
  "cameras": [
    {
      "camera_id": "uuid",
      "camera_name": "Main Entrance",
      "detections": 543,
      "active_time": 24
    }
  ]
}
```

#### `GET /stats/export`
Exports analytics data as CSV file.

**Query Parameters:**
- `start_date`, `end_date`, `camera_id`

**Response:**
- Content-Type: `text/csv`
- File download with structured analytics data

## Usage Guide

### Accessing the Dashboard
1. Navigate to `http://localhost:3000/analytics`
2. Click the 📈 Analytics link in the navigation menu

### Viewing Analytics

**Quick Analysis (Last 7 Days):**
1. Dashboard loads with default 7-day view
2. Review overview stats cards
3. Examine timeline trends
4. Check emotion/sentiment distribution

**Custom Date Range:**
1. Click "Start Date" and "End Date" pickers
2. Select desired date range
3. Data automatically refreshes
4. Use quick buttons (Today, Last 7 Days, etc.) for presets

**Camera-Specific Analysis:**
1. Open "Camera" dropdown in filters
2. Select specific camera or "All Cameras"
3. View filtered results

**Adjust Time Granularity:**
1. Select "Time Interval" dropdown
2. Choose: Hourly, Daily, Weekly, or Monthly
3. Timeline chart updates accordingly

### Exporting Data

1. Set desired filters (date range, camera)
2. Click "📊 Export CSV" button
3. File downloads automatically
4. Open in Excel, Google Sheets, or analysis tools

## Data Flow

```
User Interaction → AnalyticsFilters
                    ↓
            Analytics Page State
                    ↓
            API Requests (Parallel)
                    ↓
        Backend Analytics Router
                    ↓
         PostgreSQL Database
                    ↓
        Response Aggregation
                    ↓
        AnalyticsCharts Rendering
```

## Technical Details

### Frontend Technologies
- **React 18** with TypeScript
- **Recharts 2.10** for data visualization
- **Next.js 14** App Router
- **CSS Modules** for styling

### Backend Technologies
- **FastAPI** with async/await
- **asyncpg** for PostgreSQL connections
- **Pydantic** for data validation
- **Python 3.11**

### Database Schema
The analytics API queries the following tables:
- `detections`: Face detection records
- `emotions`: Emotion classification results
- `sentiment_results`: Sentiment analysis data
- `cameras`: Camera metadata
- `rules`: Rule configurations
- `alerts`: Triggered alert records

## Performance Considerations

### Frontend Optimizations
- Parallel API requests for faster loading
- Lazy loading of chart libraries
- Responsive design for mobile devices
- Error boundaries for graceful failures

### Backend Optimizations
- Database query optimization with indexes
- Result caching for common queries
- Connection pooling for database access
- Efficient aggregation queries

### Limitations
- Export limited to 10,000 records per request
- Charts optimized for up to 1000 data points
- Time ranges beyond 1 year may have slower load times

## Troubleshooting

### Issue: "No data found"
**Solution:**
- Verify date range includes system activity
- Check camera filter isn't excluding all data
- Ensure detection services are running

### Issue: "Failed to load analytics data"
**Solution:**
- Check API gateway is running: `docker ps`
- Verify database connection: `docker logs vantage-postgres`
- Review API logs: `docker logs vantage-api-gateway`

### Issue: Charts not rendering
**Solution:**
- Clear browser cache
- Check browser console for errors
- Verify Recharts library loaded correctly
- Try different browser

### Issue: Export not downloading
**Solution:**
- Check browser download settings
- Verify popup blocker isn't active
- Try smaller date range
- Check API response in Network tab

## Future Enhancements

Potential features for future sprints:
- Real-time analytics with WebSocket updates
- Advanced filtering (by emotion, sentiment threshold)
- Comparison mode (week-over-week, month-over-month)
- Custom report scheduling
- Dashboard widgets and layout customization
- Heatmap visualizations
- Predictive analytics and trend forecasting

## API Response Error Codes

- **200 OK**: Successful request
- **400 Bad Request**: Invalid query parameters
- **404 Not Found**: Endpoint not found
- **500 Internal Server Error**: Database or server error

## Development Notes

### Adding New Chart Types
1. Import chart component from Recharts
2. Add data fetching endpoint in Analytics.tsx
3. Create chart rendering in AnalyticsCharts.tsx
4. Update types in component props

### Extending Filters
1. Add filter state in AnalyticsFilters.tsx
2. Update FilterValues interface
3. Pass to parent via onFilterChange
4. Include in API query parameters

### Database Query Optimization
- Add indexes on frequently queried columns
- Use EXPLAIN ANALYZE for slow queries
- Consider materialized views for complex aggregations

## Related Documentation

- [API Documentation](../docs/API.md)
- [Database Schema](../docs/database-schema.md)
- [Alert Management](./ALERTS_MANAGEMENT.md)
- [Rules Configuration](./RULES_CONFIGURATION.md)
