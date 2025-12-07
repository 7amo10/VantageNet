'use client';

import { useState } from 'react';

interface Settings {
  cameraRefreshRate: number;
  enableNotifications: boolean;
  alertThreshold: number;
  apiEndpoint: string;
  wsEndpoint: string;
}

export default function Settings() {
  const [settings, setSettings] = useState<Settings>({
    cameraRefreshRate: 30,
    enableNotifications: true,
    alertThreshold: -0.5,
    apiEndpoint: 'http://localhost:8000',
    wsEndpoint: 'ws://localhost:8000/ws/live',
  });

  const handleSave = () => {
    // Will implement save functionality in Sprint 2
    alert('Settings saved! (Mock action for Sprint 1)');
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-600 mt-2">Configure dashboard and system preferences</p>
      </div>

      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold">General Settings</h2>
        </div>
        <div className="p-6 space-y-6">
          <SettingItem
            label="Camera Refresh Rate"
            description="How often to refresh camera feeds (seconds)"
          >
            <input
              type="number"
              value={settings.cameraRefreshRate}
              onChange={(e) =>
                setSettings({ ...settings, cameraRefreshRate: parseInt(e.target.value) })
              }
              className="px-3 py-2 border border-gray-300 rounded-lg w-32"
            />
          </SettingItem>

          <SettingItem
            label="Enable Notifications"
            description="Receive browser notifications for alerts"
          >
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={settings.enableNotifications}
                onChange={(e) =>
                  setSettings({ ...settings, enableNotifications: e.target.checked })
                }
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
            </label>
          </SettingItem>

          <SettingItem
            label="Alert Threshold"
            description="Sentiment value below which alerts are triggered"
          >
            <input
              type="number"
              step="0.1"
              value={settings.alertThreshold}
              onChange={(e) =>
                setSettings({ ...settings, alertThreshold: parseFloat(e.target.value) })
              }
              className="px-3 py-2 border border-gray-300 rounded-lg w-32"
            />
          </SettingItem>
        </div>
      </div>

      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold">API Configuration</h2>
        </div>
        <div className="p-6 space-y-6">
          <SettingItem
            label="API Gateway Endpoint"
            description="REST API base URL"
          >
            <input
              type="text"
              value={settings.apiEndpoint}
              onChange={(e) => setSettings({ ...settings, apiEndpoint: e.target.value })}
              className="px-3 py-2 border border-gray-300 rounded-lg w-full max-w-md"
            />
          </SettingItem>

          <SettingItem
            label="WebSocket Endpoint"
            description="Real-time updates WebSocket URL"
          >
            <input
              type="text"
              value={settings.wsEndpoint}
              onChange={(e) => setSettings({ ...settings, wsEndpoint: e.target.value })}
              className="px-3 py-2 border border-gray-300 rounded-lg w-full max-w-md"
            />
          </SettingItem>
        </div>
      </div>

      <div className="flex justify-end space-x-4">
        <button className="px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">
          Reset to Defaults
        </button>
        <button
          onClick={handleSave}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          Save Settings
        </button>
      </div>
    </div>
  );
}

interface SettingItemProps {
  label: string;
  description: string;
  children: React.ReactNode;
}

function SettingItem({ label, description, children }: SettingItemProps) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex-1">
        <p className="font-medium text-gray-900">{label}</p>
        <p className="text-sm text-gray-600 mt-1">{description}</p>
      </div>
      <div className="ml-6">{children}</div>
    </div>
  );
}
