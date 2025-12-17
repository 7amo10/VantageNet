'use client';

import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';

interface MoodDataPoint {
  timestamp: number;
  moodScore: number;
  emotion?: string;
}

interface MoodTrendChartProps {
  data: MoodDataPoint[];
  lastUpdate?: Date;
}

export default function MoodTrendChart({ data, lastUpdate }: MoodTrendChartProps) {
  // Filter to show only last 30 minutes
  const now = Date.now();
  const thirtyMinutesAgo = now - (30 * 60 * 1000);
  const recentData = data.filter(point => point.timestamp >= thirtyMinutesAgo);

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const dataPoint = payload[0].payload;
      return (
        <div className="bg-white px-4 py-3 rounded-lg shadow-lg border border-gray-200">
          <p className="text-xs text-gray-600 mb-1">
            {new Date(dataPoint.timestamp).toLocaleTimeString()}
          </p>
          <p className="text-sm font-semibold text-gray-800">
            Mood Score: <span className="text-blue-600">{dataPoint.moodScore.toFixed(2)}</span>
          </p>
          {dataPoint.emotion && (
            <p className="text-xs text-gray-600 mt-1 capitalize">
              Emotion: {dataPoint.emotion}
            </p>
          )}
        </div>
      );
    }
    return null;
  };

  const formatXAxis = (timestamp: number) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const getMoodColor = (score: number) => {
    if (score >= 0.7) return '#10b981'; // green
    if (score >= 0.4) return '#f59e0b'; // amber
    return '#ef4444'; // red
  };

  const averageMood = recentData.length > 0
    ? recentData.reduce((sum, point) => sum + point.moodScore, 0) / recentData.length
    : 0;

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-800">Mood Trend</h2>
          <p className="text-sm text-gray-600 mt-1">
            Last 30 minutes
          </p>
        </div>
        <div className="text-right">
          {lastUpdate && (
            <div className="text-xs text-gray-500">
              Updated {new Date(lastUpdate).toLocaleTimeString()}
            </div>
          )}
          <div className="text-xs font-medium text-gray-700 mt-1">
            Avg: <span className={averageMood >= 0.7 ? 'text-green-600' : averageMood >= 0.4 ? 'text-yellow-600' : 'text-red-600'}>
              {averageMood.toFixed(2)}
            </span>
          </div>
        </div>
      </div>

      {/* Chart */}
      {recentData.length > 0 ? (
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={recentData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
            <defs>
              <linearGradient id="moodGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis 
              dataKey="timestamp" 
              tickFormatter={formatXAxis}
              stroke="#9ca3af"
              style={{ fontSize: '12px' }}
              tickMargin={10}
            />
            <YAxis 
              domain={[0, 1]}
              ticks={[0, 0.25, 0.5, 0.75, 1.0]}
              stroke="#9ca3af"
              style={{ fontSize: '12px' }}
              tickMargin={5}
            />
            <Tooltip content={<CustomTooltip />} />
            <Line 
              type="monotone" 
              dataKey="moodScore" 
              stroke="#3b82f6" 
              strokeWidth={3}
              dot={{ fill: '#3b82f6', r: 4 }}
              activeDot={{ r: 6, fill: '#2563eb' }}
              animationDuration={500}
            />
          </LineChart>
        </ResponsiveContainer>
      ) : (
        <div className="flex items-center justify-center h-64 bg-gray-50 rounded-lg">
          <div className="text-center">
            <div className="text-6xl mb-4">📈</div>
            <p className="text-gray-500">No trend data available</p>
            <p className="text-sm text-gray-400 mt-1">Collecting data...</p>
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="mt-4 flex items-center justify-center gap-6 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-green-500 rounded-full" />
          <span className="text-gray-600">Positive (0.7-1.0)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-yellow-500 rounded-full" />
          <span className="text-gray-600">Neutral (0.4-0.7)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-red-500 rounded-full" />
          <span className="text-gray-600">Negative (0.0-0.4)</span>
        </div>
      </div>

      {/* Update Indicator */}
      <div className="flex items-center justify-center mt-4 gap-2">
        <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
        <span className="text-xs text-gray-600 font-medium">Real-time updates</span>
      </div>
    </div>
  );
}
