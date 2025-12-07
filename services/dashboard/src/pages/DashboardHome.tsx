'use client';

import { useEffect, useState } from 'react';

interface DashboardStats {
  totalCameras: number;
  activeCameras: number;
  totalFaces: number;
  averageSentiment: number;
}

export default function DashboardHome() {
  const [stats, setStats] = useState<DashboardStats>({
    totalCameras: 0,
    activeCameras: 0,
    totalFaces: 0,
    averageSentiment: 0,
  });

  useEffect(() => {
    // Mock data for Sprint 1
    setStats({
      totalCameras: 3,
      activeCameras: 2,
      totalFaces: 15,
      averageSentiment: 0.42,
    });
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600 mt-2">Real-time emotion analytics overview</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Cameras"
          value={stats.totalCameras}
          icon="📹"
        />
        <StatCard
          title="Active Cameras"
          value={stats.activeCameras}
          icon="🟢"
        />
        <StatCard
          title="Faces Detected"
          value={stats.totalFaces}
          icon="👥"
        />
        <StatCard
          title="Avg Sentiment"
          value={stats.averageSentiment.toFixed(2)}
          icon="😊"
        />
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Live Feed</h2>
        <div className="flex items-center justify-center h-64 bg-gray-100 rounded">
          <p className="text-gray-500">Camera feed will appear here (Sprint 2)</p>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-xl font-semibold mb-4">Recent Alerts</h2>
        <div className="space-y-3">
          <AlertItem
            message="High negative sentiment detected in Camera 1"
            timestamp="2 minutes ago"
            severity="warning"
          />
          <AlertItem
            message="All cameras operational"
            timestamp="15 minutes ago"
            severity="info"
          />
        </div>
      </div>
    </div>
  );
}

interface StatCardProps {
  title: string;
  value: string | number;
  icon: string;
}

function StatCard({ title, value, icon }: StatCardProps) {
  return (
    <div className="bg-white rounded-lg shadow p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-600">{title}</p>
          <p className="text-2xl font-bold mt-1">{value}</p>
        </div>
        <span className="text-4xl">{icon}</span>
      </div>
    </div>
  );
}

interface AlertItemProps {
  message: string;
  timestamp: string;
  severity: 'info' | 'warning' | 'error';
}

function AlertItem({ message, timestamp, severity }: AlertItemProps) {
  const colors = {
    info: 'border-blue-200 bg-blue-50',
    warning: 'border-yellow-200 bg-yellow-50',
    error: 'border-red-200 bg-red-50',
  };

  return (
    <div className={`border-l-4 p-4 rounded ${colors[severity]}`}>
      <p className="font-medium">{message}</p>
      <p className="text-sm text-gray-600 mt-1">{timestamp}</p>
    </div>
  );
}
