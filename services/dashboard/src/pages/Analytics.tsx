'use client';

import { useState, useEffect } from 'react';

interface SentimentData {
  timestamp: string;
  sentiment: number;
  emotion: string;
}

export default function Analytics() {
  const [timeRange, setTimeRange] = useState('24h');
  const [sentimentData, setSentimentData] = useState<SentimentData[]>([]);

  useEffect(() => {
    // Mock data for Sprint 1
    setSentimentData([
      { timestamp: '10:00', sentiment: 0.3, emotion: 'happy' },
      { timestamp: '11:00', sentiment: 0.5, emotion: 'happy' },
      { timestamp: '12:00', sentiment: -0.2, emotion: 'sad' },
      { timestamp: '13:00', sentiment: 0.1, emotion: 'neutral' },
      { timestamp: '14:00', sentiment: 0.4, emotion: 'happy' },
    ]);
  }, [timeRange]);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Analytics</h1>
          <p className="text-gray-600 mt-2">Sentiment trends and emotion insights</p>
        </div>
        <select
          value={timeRange}
          onChange={(e) => setTimeRange(e.target.value)}
          className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="1h">Last Hour</option>
          <option value="24h">Last 24 Hours</option>
          <option value="7d">Last 7 Days</option>
          <option value="30d">Last 30 Days</option>
        </select>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <MetricCard
          title="Average Sentiment"
          value="0.42"
          change="+12%"
          trend="up"
        />
        <MetricCard
          title="Total Interactions"
          value="1,247"
          change="+8%"
          trend="up"
        />
        <MetricCard
          title="Dominant Emotion"
          value="Happy"
          change="67%"
          trend="neutral"
        />
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Sentiment Over Time</h2>
        <div className="flex items-center justify-center h-64 bg-gray-100 rounded">
          <p className="text-gray-500">Chart visualization will appear here (Sprint 2)</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Emotion Distribution</h2>
          <div className="space-y-3">
            <EmotionBar label="Happy" percentage={45} color="bg-green-500" />
            <EmotionBar label="Neutral" percentage={30} color="bg-gray-500" />
            <EmotionBar label="Sad" percentage={15} color="bg-blue-500" />
            <EmotionBar label="Angry" percentage={10} color="bg-red-500" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Top Cameras by Activity</h2>
          <div className="space-y-3">
            <CameraActivity name="Main Entrance" count={543} />
            <CameraActivity name="Lobby Area" count={412} />
            <CameraActivity name="Reception" count={292} />
          </div>
        </div>
      </div>
    </div>
  );
}

interface MetricCardProps {
  title: string;
  value: string;
  change: string;
  trend: 'up' | 'down' | 'neutral';
}

function MetricCard({ title, value, change, trend }: MetricCardProps) {
  const trendColors = {
    up: 'text-green-600',
    down: 'text-red-600',
    neutral: 'text-gray-600',
  };

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <p className="text-sm text-gray-600">{title}</p>
      <p className="text-3xl font-bold mt-2">{value}</p>
      <p className={`text-sm mt-1 ${trendColors[trend]}`}>{change} from previous period</p>
    </div>
  );
}

interface EmotionBarProps {
  label: string;
  percentage: number;
  color: string;
}

function EmotionBar({ label, percentage, color }: EmotionBarProps) {
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-700">{label}</span>
        <span className="text-gray-600">{percentage}%</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div className={`${color} h-2 rounded-full`} style={{ width: `${percentage}%` }} />
      </div>
    </div>
  );
}

interface CameraActivityProps {
  name: string;
  count: number;
}

function CameraActivity({ name, count }: CameraActivityProps) {
  return (
    <div className="flex justify-between items-center py-2 border-b border-gray-200 last:border-0">
      <span className="text-gray-700">{name}</span>
      <span className="font-semibold">{count} faces</span>
    </div>
  );
}
