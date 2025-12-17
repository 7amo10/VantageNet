'use client';

import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

interface CrowdSizeGaugeProps {
  currentCount: number;
  history: { timestamp: number; count: number }[];
  lastUpdate?: Date;
}

const getThresholdInfo = (count: number) => {
  if (count === 0) return { label: 'Empty', color: 'text-gray-600', bgColor: 'bg-gray-100', barColor: 'bg-gray-400' };
  if (count <= 5) return { label: 'Low', color: 'text-green-600', bgColor: 'bg-green-50', barColor: 'bg-green-500' };
  if (count <= 20) return { label: 'Moderate', color: 'text-yellow-600', bgColor: 'bg-yellow-50', barColor: 'bg-yellow-500' };
  if (count <= 50) return { label: 'High', color: 'text-orange-600', bgColor: 'bg-orange-50', barColor: 'bg-orange-500' };
  return { label: 'Very High', color: 'text-red-600', bgColor: 'bg-red-50', barColor: 'bg-red-500' };
};

export default function CrowdSizeGauge({
  currentCount,
  history,
  lastUpdate
}: CrowdSizeGaugeProps) {
  const threshold = getThresholdInfo(currentCount);
  
  // Prepare sparkline data (last 5 minutes)
  const sparklineData = history.slice(-30); // Assuming 1 data point every 10 seconds

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white px-3 py-2 rounded-lg shadow-lg border border-gray-200">
          <p className="text-xs text-gray-600">
            {new Date(payload[0].payload.timestamp).toLocaleTimeString()}
          </p>
          <p className="text-sm font-semibold text-gray-800">
            {payload[0].value} faces
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className={`bg-white rounded-lg shadow-lg p-6 border-2 ${threshold.bgColor} border-gray-200`}>
      {/* Header */}
      <div className="flex justify-between items-start mb-6">
        <div>
          <h2 className="text-lg font-semibold text-gray-800">Crowd Size</h2>
          <p className="text-sm text-gray-600 mt-1">
            Detected faces in view
          </p>
        </div>
        {lastUpdate && (
          <div className="text-xs text-gray-500">
            {new Date(lastUpdate).toLocaleTimeString()}
          </div>
        )}
      </div>

      {/* Main Gauge Display */}
      <div className="flex flex-col items-center justify-center mb-6">
        {/* Count Circle */}
        <div className={`relative w-40 h-40 rounded-full flex items-center justify-center ${threshold.bgColor} border-4 ${threshold.barColor.replace('bg-', 'border-')}`}>
          <div className="text-center">
            <div className="text-5xl font-bold ${threshold.color}">
              {currentCount}
            </div>
            <div className="text-sm text-gray-600 mt-1">
              faces
            </div>
          </div>
        </div>

        {/* Threshold Label */}
        <div className={`mt-4 px-6 py-2 rounded-full ${threshold.bgColor} border ${threshold.barColor.replace('bg-', 'border-')}`}>
          <span className={`text-lg font-semibold ${threshold.color}`}>
            {threshold.label}
          </span>
        </div>
      </div>

      {/* Threshold Indicators */}
      <div className="mb-6">
        <div className="text-xs font-medium text-gray-600 mb-2">Thresholds</div>
        <div className="grid grid-cols-4 gap-2">
          <div className={`p-2 rounded text-center ${currentCount <= 5 && currentCount > 0 ? 'bg-green-100 border-2 border-green-500' : 'bg-gray-50'}`}>
            <div className="text-xs font-semibold text-gray-700">0-5</div>
            <div className="text-xs text-gray-600">Low</div>
          </div>
          <div className={`p-2 rounded text-center ${currentCount > 5 && currentCount <= 20 ? 'bg-yellow-100 border-2 border-yellow-500' : 'bg-gray-50'}`}>
            <div className="text-xs font-semibold text-gray-700">5-20</div>
            <div className="text-xs text-gray-600">Moderate</div>
          </div>
          <div className={`p-2 rounded text-center ${currentCount > 20 && currentCount <= 50 ? 'bg-orange-100 border-2 border-orange-500' : 'bg-gray-50'}`}>
            <div className="text-xs font-semibold text-gray-700">20-50</div>
            <div className="text-xs text-gray-600">High</div>
          </div>
          <div className={`p-2 rounded text-center ${currentCount > 50 ? 'bg-red-100 border-2 border-red-500' : 'bg-gray-50'}`}>
            <div className="text-xs font-semibold text-gray-700">50+</div>
            <div className="text-xs text-gray-600">Very High</div>
          </div>
        </div>
      </div>

      {/* Sparkline - Past 5 Minutes */}
      <div>
        <div className="text-xs font-medium text-gray-600 mb-2">Past 5 Minutes</div>
        {sparklineData.length > 0 ? (
          <ResponsiveContainer width="100%" height={80}>
            <AreaChart data={sparklineData}>
              <defs>
                <linearGradient id="crowdGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.1}/>
                </linearGradient>
              </defs>
              <XAxis 
                dataKey="timestamp" 
                hide={true}
              />
              <YAxis hide={true} />
              <Tooltip content={<CustomTooltip />} />
              <Area 
                type="monotone" 
                dataKey="count" 
                stroke="#3b82f6" 
                strokeWidth={2}
                fill="url(#crowdGradient)" 
                animationDuration={300}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-20 bg-gray-50 rounded flex items-center justify-center">
            <span className="text-xs text-gray-400">Loading history...</span>
          </div>
        )}
      </div>

      {/* Live Indicator */}
      <div className="flex items-center justify-center mt-4 gap-2">
        <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
        <span className="text-xs text-gray-600 font-medium">Real-time tracking</span>
      </div>
    </div>
  );
}
