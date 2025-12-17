'use client';

import { useState } from 'react';

export interface AlertItem {
  id: string;
  ruleId: string;
  ruleName: string;
  message: string;
  severity: 'info' | 'warning' | 'critical';
  timestamp: Date;
  cameraId?: string;
  resolved: boolean;
}

interface AlertFeedPanelProps {
  alerts: AlertItem[];
  onResolve: (alertId: string) => void;
  onDismiss: (alertId: string) => void;
  onViewDetails: (alert: AlertItem) => void;
}

const severityConfig = {
  info: {
    color: 'text-blue-700',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    icon: 'ℹ️',
    label: 'Info',
  },
  warning: {
    color: 'text-orange-700',
    bgColor: 'bg-orange-50',
    borderColor: 'border-orange-200',
    icon: '⚠️',
    label: 'Warning',
  },
  critical: {
    color: 'text-red-700',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    icon: '🔴',
    label: 'Critical',
  },
};

export default function AlertFeedPanel({
  alerts,
  onResolve,
  onDismiss,
  onViewDetails,
}: AlertFeedPanelProps) {
  const [filter, setFilter] = useState<'all' | 'info' | 'warning' | 'critical'>('all');
  const [showResolved, setShowResolved] = useState(false);

  const filteredAlerts = alerts
    .filter(alert => showResolved || !alert.resolved)
    .filter(alert => filter === 'all' || alert.severity === filter)
    .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());

  const getRelativeTime = (timestamp: Date) => {
    const seconds = Math.floor((Date.now() - timestamp.getTime()) / 1000);
    
    if (seconds < 60) return `${seconds}s ago`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
  };

  const getCounts = () => {
    const unresolvedAlerts = alerts.filter(a => !a.resolved);
    return {
      total: unresolvedAlerts.length,
      info: unresolvedAlerts.filter(a => a.severity === 'info').length,
      warning: unresolvedAlerts.filter(a => a.severity === 'warning').length,
      critical: unresolvedAlerts.filter(a => a.severity === 'critical').length,
    };
  };

  const counts = getCounts();

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      {/* Header */}
      <div className="flex justify-between items-start mb-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-800">Alert Feed</h2>
          <p className="text-sm text-gray-600 mt-1">
            Recent system alerts
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`px-3 py-1 rounded-full text-xs font-semibold ${counts.critical > 0 ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-700'}`}>
            {counts.total} Active
          </span>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        <button
          onClick={() => setFilter('all')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            filter === 'all'
              ? 'bg-blue-100 text-blue-700'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          All ({counts.total})
        </button>
        <button
          onClick={() => setFilter('critical')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            filter === 'critical'
              ? 'bg-red-100 text-red-700'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          Critical ({counts.critical})
        </button>
        <button
          onClick={() => setFilter('warning')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            filter === 'warning'
              ? 'bg-orange-100 text-orange-700'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          Warning ({counts.warning})
        </button>
        <button
          onClick={() => setFilter('info')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            filter === 'info'
              ? 'bg-blue-100 text-blue-700'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          Info ({counts.info})
        </button>
        
        <div className="ml-auto flex items-center gap-2">
          <input
            type="checkbox"
            id="showResolved"
            checked={showResolved}
            onChange={(e) => setShowResolved(e.target.checked)}
            className="rounded border-gray-300"
          />
          <label htmlFor="showResolved" className="text-sm text-gray-700 cursor-pointer">
            Show resolved
          </label>
        </div>
      </div>

      {/* Alert List */}
      <div className="space-y-3 max-h-[500px] overflow-y-auto pr-2">
        {filteredAlerts.length > 0 ? (
          filteredAlerts.map((alert) => {
            const config = severityConfig[alert.severity];
            return (
              <div
                key={alert.id}
                className={`border-l-4 ${config.borderColor} ${config.bgColor} rounded-lg p-4 transition-all hover:shadow-md ${
                  alert.resolved ? 'opacity-50' : ''
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3 flex-1">
                    {/* Icon */}
                    <div className="text-2xl mt-1">{config.icon}</div>
                    
                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className={`text-xs font-bold px-2 py-1 rounded ${config.bgColor} ${config.color} border ${config.borderColor}`}>
                          {config.label.toUpperCase()}
                        </span>
                        <span className="text-xs text-gray-500">
                          {getRelativeTime(alert.timestamp)}
                        </span>
                        {alert.resolved && (
                          <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded font-medium">
                            ✓ Resolved
                          </span>
                        )}
                      </div>
                      
                      <p className={`font-medium ${config.color} mb-1`}>
                        {alert.message}
                      </p>
                      
                      <div className="flex items-center gap-3 text-xs text-gray-600">
                        <span>Rule: <span className="font-medium">{alert.ruleName}</span></span>
                        {alert.cameraId && (
                          <span>Camera: <span className="font-medium">{alert.cameraId}</span></span>
                        )}
                        <span className="text-gray-400">
                          {alert.timestamp.toLocaleString()}
                        </span>
                      </div>
                    </div>
                  </div>
                  
                  {/* Actions */}
                  <div className="flex flex-col gap-2">
                    <button
                      onClick={() => onViewDetails(alert)}
                      className="text-xs px-3 py-1 bg-white border border-gray-300 rounded hover:bg-gray-50 transition-colors font-medium"
                    >
                      Details
                    </button>
                    {!alert.resolved && (
                      <>
                        <button
                          onClick={() => onResolve(alert.id)}
                          className="text-xs px-3 py-1 bg-green-100 text-green-700 rounded hover:bg-green-200 transition-colors font-medium"
                        >
                          Resolve
                        </button>
                        <button
                          onClick={() => onDismiss(alert.id)}
                          className="text-xs px-3 py-1 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors font-medium"
                        >
                          Dismiss
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            );
          })
        ) : (
          <div className="flex flex-col items-center justify-center py-12 bg-gray-50 rounded-lg">
            <div className="text-6xl mb-4">🔔</div>
            <p className="text-gray-500 font-medium">No alerts to display</p>
            <p className="text-sm text-gray-400 mt-1">
              {filter === 'all' ? 'All clear!' : `No ${filter} alerts`}
            </p>
          </div>
        )}
      </div>

      {/* Summary Footer */}
      {filteredAlerts.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-200 flex items-center justify-between text-sm">
          <span className="text-gray-600">
            Showing {filteredAlerts.length} of {alerts.length} alerts
          </span>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            <span className="text-gray-600 font-medium">Live updates</span>
          </div>
        </div>
      )}
    </div>
  );
}
