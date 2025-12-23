'use client';

import React, { useMemo } from 'react';
import { PieChart, Pie, Cell, Legend, Tooltip, ResponsiveContainer } from 'recharts';

interface EmotionData {
  name: string;
  value: number;
  percentage: number;
}

interface EmotionDistributionChartProps {
  emotions: Record<string, number>;
  lastUpdate?: Date;
}

const EMOTION_COLORS: Record<string, string> = {
  happy: '#10b981',      // green-500
  sad: '#3b82f6',        // blue-500
  angry: '#ef4444',      // red-500
  surprised: '#f59e0b',  // amber-500
  neutral: '#6b7280',    // gray-500
  fear: '#8b5cf6',       // purple-500
  disgust: '#f97316',    // orange-500
};

function EmotionDistributionChart({ 
  emotions, 
  lastUpdate 
}: EmotionDistributionChartProps) {
  // Convert emotions object to chart data - memoized to prevent recalculation
  const chartData: EmotionData[] = useMemo(() => {
    const total = Object.values(emotions).reduce((sum, val) => sum + val, 0);
    
    return Object.entries(emotions)
      .filter(([_, value]) => value > 0)
      .map(([name, value]) => ({
        name: name.charAt(0).toUpperCase() + name.slice(1),
        value,
        percentage: total > 0 ? (value / total) * 100 : 0,
      }))
      .sort((a, b) => b.value - a.value);
  }, [emotions]);
  
  const total = useMemo(() => 
    Object.values(emotions).reduce((sum, val) => sum + val, 0), 
    [emotions]
  );

  const renderCustomLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percentage }: any) => {
    if (percentage < 5) return null; // Don't show labels for small slices
    
    const RADIAN = Math.PI / 180;
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    return (
      <text 
        x={x} 
        y={y} 
        fill="white" 
        textAnchor={x > cx ? 'start' : 'end'} 
        dominantBaseline="central"
        className="text-sm font-bold"
      >
        {`${percentage.toFixed(0)}%`}
      </text>
    );
  };

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white px-4 py-2 rounded-lg shadow-lg border border-gray-200">
          <p className="font-semibold text-gray-800">{payload[0].name}</p>
          <p className="text-sm text-gray-600">
            Count: <span className="font-medium">{payload[0].value}</span>
          </p>
          <p className="text-sm text-gray-600">
            Percentage: <span className="font-medium">{payload[0].payload.percentage.toFixed(1)}%</span>
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-800">Emotion Distribution</h2>
          <p className="text-sm text-gray-600 mt-1">
            Real-time emotion breakdown
          </p>
        </div>
        {lastUpdate && (
          <div className="text-xs text-gray-500">
            Updated {new Date(lastUpdate).toLocaleTimeString()}
          </div>
        )}
      </div>

      {/* Chart */}
      {chartData.length > 0 ? (
        <>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={renderCustomLabel}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
                animationDuration={500}
              >
                {chartData.map((entry, index) => (
                  <Cell 
                    key={`cell-${index}`} 
                    fill={EMOTION_COLORS[entry.name.toLowerCase()] || '#6b7280'} 
                  />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>

          {/* Custom Legend with Percentages */}
          <div className="mt-6 grid grid-cols-2 gap-3">
            {chartData.map((item) => (
              <div 
                key={item.name}
                className="flex items-center justify-between p-2 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <div 
                    className="w-4 h-4 rounded-full"
                    style={{ backgroundColor: EMOTION_COLORS[item.name.toLowerCase()] }}
                  />
                  <span className="text-sm font-medium text-gray-700">
                    {item.name}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-600">
                    {item.value}
                  </span>
                  <span className="text-xs font-semibold text-gray-700 bg-white px-2 py-1 rounded">
                    {item.percentage.toFixed(1)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="flex items-center justify-center h-64 bg-gray-50 rounded-lg">
          <div className="text-center">
            <div className="text-6xl mb-4">📊</div>
            <p className="text-gray-500">No emotion data available</p>
            <p className="text-sm text-gray-400 mt-1">Waiting for live data...</p>
          </div>
        </div>
      )}

      {/* Update Frequency Indicator */}
      <div className="flex items-center justify-center mt-4 gap-2 text-sm text-gray-600">
        <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
        <span>Updates every 2 seconds</span>
      </div>
    </div>
  );
}

// Memoize component to prevent unnecessary re-renders
export default React.memo(EmotionDistributionChart, (prevProps, nextProps) => {
  // Custom comparison: only re-render if emotions or lastUpdate changed
  return (
    JSON.stringify(prevProps.emotions) === JSON.stringify(nextProps.emotions) &&
    prevProps.lastUpdate?.getTime() === nextProps.lastUpdate?.getTime()
  );
});
