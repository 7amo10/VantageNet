'use client';

import React, { useState, useEffect } from 'react';
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
  const [filters, setFilters] = useState<FilterValues>({
    startDate: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    endDate: new Date().toISOString().split('T')[0],
    cameraId: '',
    interval: 'hour',
  });

  useEffect(() => {
    fetchAnalyticsData();
  }, [filters]);

  const buildQueryParams = () => {
    const params = new URLSearchParams();
    params.append('start_date', filters.startDate);
    params.append('end_date', filters.endDate);
    if (filters.cameraId) {
      params.append('camera_id', filters.cameraId);
    }
    params.append('interval', filters.interval);
    return params.toString();
  };

  const fetchAnalyticsData = async () => {
    setLoading(true);
    setError(null);

    try {
      const queryParams = buildQueryParams();
      
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
    } catch (err) {
      console.error('Error fetching analytics:', err);
      setError('Failed to load analytics data');
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (newFilters: FilterValues) => {
    setFilters(newFilters);
  };

  const handleExport = async () => {
    try {
      const queryParams = buildQueryParams();
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
  };

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

export default Analytics;

