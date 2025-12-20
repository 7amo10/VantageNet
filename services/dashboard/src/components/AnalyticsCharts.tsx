'use client';

import React from 'react';
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import './AnalyticsCharts.css';

interface TimelineData {
  timestamp: string;
  detections: number;
  emotions: number;
  sentiments: number;
}

interface DetectionStats {
  total_detections: number;
  unique_faces: number;
  avg_confidence: number;
}

interface EmotionData {
  emotion: string;
  count: number;
  percentage: number;
}

interface SentimentData {
  sentiment: string;
  count: number;
  percentage: number;
}

interface CameraStats {
  camera_id: string;
  camera_name: string;
  detections: number;
  active_time: number;
}

interface AnalyticsChartsProps {
  timelineData: TimelineData[];
  detectionStats: DetectionStats;
  emotionData: EmotionData[];
  sentimentData: SentimentData[];
  cameraStats: CameraStats[];
}

const COLORS = {
  primary: '#3b82f6',
  success: '#10b981',
  warning: '#f59e0b',
  danger: '#ef4444',
  info: '#06b6d4',
  purple: '#8b5cf6',
  pink: '#ec4899',
};

const EMOTION_COLORS: { [key: string]: string } = {
  happy: COLORS.success,
  sad: COLORS.info,
  angry: COLORS.danger,
  surprised: COLORS.warning,
  neutral: '#6b7280',
  fear: COLORS.purple,
  disgust: COLORS.pink,
};

const SENTIMENT_COLORS: { [key: string]: string } = {
  positive: COLORS.success,
  neutral: COLORS.warning,
  negative: COLORS.danger,
};

const AnalyticsCharts: React.FC<AnalyticsChartsProps> = ({
  timelineData,
  detectionStats,
  emotionData,
  sentimentData,
  cameraStats,
}) => {
  return (
    <div className="analytics-charts">
      {/* Overview Stats Cards */}
      <div className="stats-cards">
        <div className="stat-card">
          <div className="stat-icon" style={{ backgroundColor: COLORS.primary }}>
            👤
          </div>
          <div className="stat-content">
            <div className="stat-value">{detectionStats.total_detections.toLocaleString()}</div>
            <div className="stat-label">Total Detections</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ backgroundColor: COLORS.success }}>
            🎭
          </div>
          <div className="stat-content">
            <div className="stat-value">{detectionStats.unique_faces.toLocaleString()}</div>
            <div className="stat-label">Unique Faces</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ backgroundColor: COLORS.warning }}>
            📊
          </div>
          <div className="stat-content">
            <div className="stat-value">{(detectionStats.avg_confidence * 100).toFixed(1)}%</div>
            <div className="stat-label">Avg Confidence</div>
          </div>
        </div>
      </div>

      {/* Timeline Chart */}
      <div className="chart-card">
        <h3>Detection Timeline</h3>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={timelineData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="timestamp" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="detections" stroke={COLORS.primary} strokeWidth={2} />
            <Line type="monotone" dataKey="emotions" stroke={COLORS.success} strokeWidth={2} />
            <Line type="monotone" dataKey="sentiments" stroke={COLORS.warning} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Emotion and Sentiment Distribution */}
      <div className="charts-row">
        <div className="chart-card">
          <h3>Emotion Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={emotionData}
                dataKey="count"
                nameKey="emotion"
                cx="50%"
                cy="50%"
                outerRadius={100}
                label={(entry) => `${entry.emotion}: ${entry.percentage.toFixed(1)}%`}
              >
                {emotionData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={EMOTION_COLORS[entry.emotion.toLowerCase()] || COLORS.info} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-card">
          <h3>Sentiment Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={sentimentData}
                dataKey="count"
                nameKey="sentiment"
                cx="50%"
                cy="50%"
                outerRadius={100}
                label={(entry) => `${entry.sentiment}: ${entry.percentage.toFixed(1)}%`}
              >
                {sentimentData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={SENTIMENT_COLORS[entry.sentiment.toLowerCase()] || COLORS.info} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Camera Performance */}
      <div className="chart-card">
        <h3>Camera Performance</h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={cameraStats}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="camera_name" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Bar dataKey="detections" fill={COLORS.primary} />
            <Bar dataKey="active_time" fill={COLORS.success} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

export default AnalyticsCharts;
