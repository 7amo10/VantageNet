'use client';

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import AnalyticsFilters, { FilterValues } from '@/components/AnalyticsFilters';
import AnalyticsCharts from '@/components/AnalyticsCharts';
import './Analytics.css';

interface AnalyticsData {
  timeline: any[];
  detections: any;
  emotions: any[];
  sentiments: any[];
  cameras: any[];
}

const Analytics: React.FC = () => {
  const [data, setData] = useState<AnalyticsData>({
    timeline: [],
    detections: { total_detections: 0, unique_faces: 0, avg_confidence: 0 },
    emotions: [],
    sentiments: [],
    cameras: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date>(new Date());
  const hasLoadedOnce = useRef(false);
  const [filters, setFilters] = useState<FilterValues>({
    startDate: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    // Add 1 day to end date to include all of today's data
    endDate: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    cameraId: '',
    interval: 'hour',
  });

  // Memoize query params to avoid recalculation
  const queryParams = useMemo(() => {
    const params = new URLSearchParams();
    params.append('start_date', filters.startDate);
    params.append('end_date', filters.endDate);
    if (filters.cameraId) {
      params.append('camera_id', filters.cameraId);
    }
    params.append('interval', filters.interval);
    return params.toString();
  }, [filters.startDate, filters.endDate, filters.cameraId, filters.interval]);

  // Memoize fetch function with useCallback
  const fetchAnalyticsData = useCallback(async () => {
    // Only show loading on initial load, not on refresh
    if (!hasLoadedOnce.current) setLoading(true);
    setError(null);

    try {
      const [timelineRes, detectionsRes, emotionsRes, sentimentsRes, camerasRes] = await Promise.all([
        fetch(`http://localhost:8000/api/analytics/stats/timeline?${queryParams}`),
        fetch(`http://localhost:8000/api/analytics/stats/detections?${queryParams}`),
        fetch(`http://localhost:8000/api/analytics/stats/emotions?${queryParams}`),
        fetch(`http://localhost:8000/api/analytics/stats/sentiments?${queryParams}`),
        fetch(`http://localhost:8000/api/analytics/stats/cameras?${queryParams}`),
      ]);

      if (!timelineRes.ok || !detectionsRes.ok || !emotionsRes.ok || !sentimentsRes.ok || !camerasRes.ok) {
        throw new Error('Failed to fetch analytics data');
      }

      const [timeline, detections, emotions, sentiments, cameras] = await Promise.all([
        timelineRes.json(),
        detectionsRes.json(),
        emotionsRes.json(),
        sentimentsRes.json(),
        camerasRes.json(),
      ]);

      setData({
        timeline: timeline.timeline || [],
        detections: detections,
        emotions: emotions.emotions || [],
        sentiments: sentiments.sentiments || [],
        cameras: cameras.cameras || [],
      });
      setLastUpdated(new Date());
      hasLoadedOnce.current = true;
    } catch (err) {
      console.error('Error fetching analytics:', err);
      setError('Failed to load analytics data');
    } finally {
      setLoading(false);
    }
  }, [queryParams]);

  useEffect(() => {
    fetchAnalyticsData();

    // Auto-refresh every 10 seconds for real-time updates
    const refreshInterval = setInterval(() => {
      fetchAnalyticsData();
    }, 10000);

    return () => clearInterval(refreshInterval);
  }, [fetchAnalyticsData]);

  // Memoize filter change handler
  const handleFilterChange = useCallback((newFilters: FilterValues) => {
    setFilters(newFilters);
  }, []);

  // Memoize export handler
  const handleExport = useCallback(async () => {
    try {
      const response = await fetch(`http://localhost:8000/api/analytics/stats/export?${queryParams}`);

      if (!response.ok) {
        throw new Error('Export failed');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `analytics_${filters.startDate}_to_${filters.endDate}.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      console.error('Export failed:', err);
      alert('Failed to export data');
    }
  }, [queryParams, filters.startDate, filters.endDate]);

  return (
    <div className="analytics-page">
      <AnalyticsFilters onFilterChange={handleFilterChange} onExport={handleExport} />

      {loading && (
        <div className="loading-container">
          <div className="spinner"></div>
          <p>Loading analytics data...</p>
        </div>
      )}

      {error && (
        <div className="error-container">
          <p>❌ {error}</p>
          <button onClick={fetchAnalyticsData}>Retry</button>
        </div>
      )}

      {!loading && !error && (
        <AnalyticsCharts
          timelineData={data.timeline}
          detectionStats={data.detections}
          emotionData={data.emotions}
          sentimentData={data.sentiments}
          cameraStats={data.cameras}
        />
      )}
    </div>
  );
};

// Memoize the entire component to prevent unnecessary re-renders
export default React.memo(Analytics);

