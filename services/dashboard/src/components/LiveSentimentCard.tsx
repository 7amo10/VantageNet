'use client';

import React, { useEffect, useState, useCallback } from 'react';

interface LiveSentimentCardProps {
  emotion: string;
  moodScore: number;
  trend: 'up' | 'down' | 'stable';
  lastUpdate?: Date;
}

const emotionIcons: Record<string, string> = {
  happy: '😊',
  sad: '😢',
  angry: '😠',
  surprised: '😲',
  neutral: '😐',
  fear: '😨',
  disgust: '🤢',
};

const emotionColors: Record<string, string> = {
  happy: 'text-green-600',
  sad: 'text-blue-600',
  angry: 'text-red-600',
  surprised: 'text-yellow-600',
  neutral: 'text-gray-600',
  fear: 'text-purple-600',
  disgust: 'text-orange-600',
};

function LiveSentimentCard({ 
  emotion, 
  moodScore, 
  trend,
  lastUpdate 
}: LiveSentimentCardProps) {
  const [pulseAnimation, setPulseAnimation] = useState(false);

  useEffect(() => {
    // Trigger pulse animation on updates
    setPulseAnimation(true);
    const timer = setTimeout(() => setPulseAnimation(false), 300);
    return () => clearTimeout(timer);
  }, [emotion, moodScore]);

  const getTrendIcon = useCallback(() => {
    switch (trend) {
      case 'up':
        return <span className="text-green-500 text-2xl">↑</span>;
      case 'down':
        return <span className="text-red-500 text-2xl">↓</span>;
      case 'stable':
        return <span className="text-gray-500 text-2xl">→</span>;
    }
  }, [trend]);

  const getTrendText = useCallback(() => {
    switch (trend) {
      case 'up':
        return 'Improving';
      case 'down':
        return 'Declining';
      case 'stable':
        return 'Stable';
    }
  }, [trend]);

  const getMoodColor = useCallback(() => {
    if (moodScore >= 0.7) return 'text-green-600';
    if (moodScore >= 0.4) return 'text-yellow-600';
    return 'text-red-600';
  }, [moodScore]);

  const getMoodBackground = useCallback(() => {
    if (moodScore >= 0.7) return 'bg-green-50 border-green-200';
    if (moodScore >= 0.4) return 'bg-yellow-50 border-yellow-200';
    return 'bg-red-50 border-red-200';
  }, [moodScore]);

  return (
    <div 
      className={`
        bg-white rounded-lg shadow-lg p-8 border-2 transition-all duration-300
        ${getMoodBackground()}
        ${pulseAnimation ? 'scale-105 shadow-xl' : 'scale-100'}
      `}
    >
      {/* Header */}
      <div className="flex justify-between items-start mb-6">
        <div>
          <h2 className="text-lg font-semibold text-gray-700">Live Sentiment</h2>
          {lastUpdate && (
            <p className="text-xs text-gray-500 mt-1">
              Updated {new Date(lastUpdate).toLocaleTimeString()}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2 bg-white px-3 py-1 rounded-full shadow-sm">
          {getTrendIcon()}
          <span className="text-sm font-medium text-gray-700">{getTrendText()}</span>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex flex-col items-center justify-center py-6">
        {/* Emotion Icon */}
        <div className="text-8xl mb-4 transition-transform duration-300 hover:scale-110">
          {emotionIcons[emotion.toLowerCase()] || '😐'}
        </div>

        {/* Emotion Label */}
        <h3 className={`text-3xl font-bold capitalize mb-2 ${emotionColors[emotion.toLowerCase()] || 'text-gray-700'}`}>
          {emotion}
        </h3>

        {/* Mood Score */}
        <div className="w-full max-w-xs mt-4">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm font-medium text-gray-600">Mood Score</span>
            <span className={`text-2xl font-bold ${getMoodColor()}`}>
              {moodScore.toFixed(2)}
            </span>
          </div>
          
          {/* Progress Bar */}
          <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
            <div 
              className={`h-full transition-all duration-500 rounded-full ${
                moodScore >= 0.7 ? 'bg-green-500' :
                moodScore >= 0.4 ? 'bg-yellow-500' :
                'bg-red-500'
              }`}
              style={{ width: `${moodScore * 100}%` }}
            />
          </div>
          
          {/* Scale Labels */}
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>0.0</span>
            <span>0.5</span>
            <span>1.0</span>
          </div>
        </div>
      </div>

      {/* Live Indicator */}
      <div className="flex items-center justify-center mt-4 gap-2">
        <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
        <span className="text-sm text-gray-600 font-medium">Live</span>
      </div>
    </div>
  );
}

// Memoize component to prevent unnecessary re-renders
export default React.memo(LiveSentimentCard);
