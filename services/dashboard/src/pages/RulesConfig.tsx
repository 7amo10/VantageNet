'use client';

import { useState } from 'react';

interface Rule {
  id: string;
  name: string;
  condition: string;
  action: string;
  enabled: boolean;
}

export default function RulesConfig() {
  const [rules, setRules] = useState<Rule[]>([
    {
      id: '1',
      name: 'High Negative Alert',
      condition: 'sentiment < -0.5',
      action: 'Send notification',
      enabled: true,
    },
    {
      id: '2',
      name: 'Crowd Detection',
      condition: 'faces > 10',
      action: 'Log event',
      enabled: true,
    },
  ]);

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Rules Configuration</h1>
          <p className="text-gray-600 mt-2">Manage sentiment analysis rules and alerts</p>
        </div>
        <button className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
          + New Rule
        </button>
      </div>

      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold">Active Rules</h2>
        </div>
        <div className="divide-y divide-gray-200">
          {rules.map((rule) => (
            <RuleItem key={rule.id} rule={rule} />
          ))}
        </div>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-800">
          <strong>Note:</strong> Rule configuration and real-time updates will be implemented in Sprint 2.
        </p>
      </div>
    </div>
  );
}

interface RuleItemProps {
  rule: Rule;
}

function RuleItem({ rule }: RuleItemProps) {
  return (
    <div className="px-6 py-4 flex items-center justify-between hover:bg-gray-50">
      <div className="flex-1">
        <div className="flex items-center space-x-3">
          <h3 className="font-medium text-gray-900">{rule.name}</h3>
          <span
            className={`px-2 py-1 text-xs rounded-full ${
              rule.enabled
                ? 'bg-green-100 text-green-800'
                : 'bg-gray-100 text-gray-800'
            }`}
          >
            {rule.enabled ? 'Enabled' : 'Disabled'}
          </span>
        </div>
        <p className="text-sm text-gray-600 mt-1">
          When <code className="bg-gray-100 px-2 py-0.5 rounded">{rule.condition}</code> then{' '}
          <strong>{rule.action}</strong>
        </p>
      </div>
      <div className="flex space-x-2">
        <button className="px-3 py-1 text-sm text-blue-600 hover:bg-blue-50 rounded">
          Edit
        </button>
        <button className="px-3 py-1 text-sm text-red-600 hover:bg-red-50 rounded">
          Delete
        </button>
      </div>
    </div>
  );
}
