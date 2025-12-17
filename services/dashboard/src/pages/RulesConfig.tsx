'use client';

import { useState, useEffect } from 'react';
import RuleFormModal, { Rule, RULE_TYPES, RULE_ACTIONS, EMOTIONS, SEVERITIES } from '@/components/RuleFormModal';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Format time ago
function timeAgo(dateString?: string): string {
  if (!dateString) return 'Never';
  const date = new Date(dateString);
  const now = new Date();
  const seconds = Math.floor((now.getTime() - date.getTime()) / 1000);
  
  if (seconds < 60) return 'Just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return date.toLocaleDateString();
}

// Format condition for display
function formatCondition(rule: Rule): string {
  const { type, condition_json } = rule;
  
  switch (type) {
    case 'threshold':
      return `${condition_json.emotion} > ${(condition_json.threshold * 100).toFixed(0)}%`;
    case 'trend':
      return `sentiment ${condition_json.direction} by ${(condition_json.magnitude_threshold * 100).toFixed(0)}%`;
    case 'duration':
      return `${condition_json.emotion} for ${condition_json.duration_seconds}s`;
    case 'sentiment':
      return `sentiment > ${(condition_json.sentiment_threshold * 100).toFixed(0)}%`;
    default:
      return 'Custom condition';
  }
}

export default function RulesConfig() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedRule, setSelectedRule] = useState<Rule | null>(null);
  const [modalMode, setModalMode] = useState<'create' | 'edit'>('create');
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  // Fetch rules from API
  const fetchRules = async () => {
    try {
      setLoading(true);
      setError(null);
      console.log('Fetching rules from:', `${API_BASE_URL}/api/rules/`);
      const response = await fetch(`${API_BASE_URL}/api/rules/`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      console.log('Response status:', response.status);
      if (!response.ok) {
        const errorText = await response.text();
        console.error('Response error:', errorText);
        throw new Error(`Failed to fetch rules: ${response.status} ${response.statusText}`);
      }
      const data = await response.json();
      console.log('Fetched rules:', data);
      setRules(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error('Error fetching rules:', err);
      if (err instanceof TypeError && err.message.includes('fetch')) {
        setError('Cannot connect to API server. Please ensure the API Gateway is running on http://localhost:8000');
      } else {
        setError(err instanceof Error ? err.message : 'Failed to load rules');
      }
      setRules([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRules();
  }, []);

  // Create rule
  const handleCreateRule = async (ruleData: Partial<Rule>) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/rules/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(ruleData),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to create rule: ${response.statusText}`);
      }
      
      await fetchRules();
      setIsModalOpen(false);
      setSelectedRule(null);
    } catch (err) {
      console.error('Error creating rule:', err);
      throw err;
    }
  };

  // Update rule
  const handleUpdateRule = async (ruleData: Partial<Rule>) => {
    if (!ruleData.id) return;
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/rules/${ruleData.id}/`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(ruleData),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to update rule: ${response.statusText}`);
      }
      
      await fetchRules();
      setIsModalOpen(false);
      setSelectedRule(null);
    } catch (err) {
      console.error('Error updating rule:', err);
      throw err;
    }
  };

  // Delete rule
  const handleDeleteRule = async (ruleId: string) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/rules/${ruleId}/`, {
        method: 'DELETE',
      });
      
      if (!response.ok) {
        throw new Error(`Failed to delete rule: ${response.statusText}`);
      }
      
      await fetchRules();
      setDeleteConfirm(null);
    } catch (err) {
      console.error('Error deleting rule:', err);
      alert('Failed to delete rule');
    }
  };

  // Toggle rule enabled status
  const handleToggleEnabled = async (rule: Rule) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/rules/${rule.id}/`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !rule.enabled }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to toggle rule: ${response.statusText}`);
      }
      
      await fetchRules();
    } catch (err) {
      console.error('Error toggling rule:', err);
      alert('Failed to toggle rule');
    }
  };

  // Open create modal
  const handleOpenCreate = () => {
    setSelectedRule(null);
    setModalMode('create');
    setIsModalOpen(true);
  };

  // Open edit modal
  const handleOpenEdit = (rule: Rule) => {
    setSelectedRule(rule);
    setModalMode('edit');
    setIsModalOpen(true);
  };

  // Get severity badge color
  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'info': return 'bg-blue-100 text-blue-800';
      case 'warning': return 'bg-yellow-100 text-yellow-800';
      case 'critical': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Rules Configuration</h1>
          <p className="text-gray-600 mt-2">
            Create and manage emotion detection rules with custom triggers and actions
          </p>
        </div>
        <button
          onClick={handleOpenCreate}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center space-x-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          <span>New Rule</span>
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-600">Total Rules</div>
          <div className="text-2xl font-bold text-gray-900">{rules.length}</div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-600">Enabled</div>
          <div className="text-2xl font-bold text-green-600">
            {rules.filter(r => r.enabled).length}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-600">Disabled</div>
          <div className="text-2xl font-bold text-gray-500">
            {rules.filter(r => !r.enabled).length}
          </div>
        </div>
        <div className="bg-white rounded-lg shadow p-4">
          <div className="text-sm text-gray-600">Recently Triggered</div>
          <div className="text-2xl font-bold text-blue-600">
            {rules.filter(r => r.last_triggered).length}
          </div>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <p className="mt-2 text-gray-600">Loading rules...</p>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-start space-x-3">
          <svg className="w-5 h-5 text-red-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="flex-1">
            <h3 className="text-sm font-medium text-red-800">Error Loading Rules</h3>
            <p className="text-sm text-red-700 mt-1">{error}</p>
            <button
              onClick={fetchRules}
              className="mt-2 text-sm text-red-800 underline hover:text-red-900"
            >
              Try again
            </button>
          </div>
        </div>
      )}

      {/* Rules List */}
      {!loading && !error && (
        <>
          {rules.length === 0 ? (
            <div className="bg-white rounded-lg shadow p-12 text-center">
              <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <h3 className="mt-2 text-lg font-medium text-gray-900">No rules configured</h3>
              <p className="mt-1 text-sm text-gray-500">
                Get started by creating your first emotion detection rule
              </p>
              <button
                onClick={handleOpenCreate}
                className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Create Rule
              </button>
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="divide-y divide-gray-200">
                {rules.map((rule) => (
                  <div key={rule.id} className="p-6 hover:bg-gray-50 transition-colors">
                    <div className="flex items-start justify-between">
                      {/* Rule Info */}
                      <div className="flex-1">
                        <div className="flex items-center space-x-3">
                          <h3 className="text-lg font-semibold text-gray-900">{rule.name}</h3>
                          <span
                            className={`px-2 py-1 text-xs font-medium rounded-full ${
                              rule.enabled
                                ? 'bg-green-100 text-green-800'
                                : 'bg-gray-100 text-gray-600'
                            }`}
                          >
                            {rule.enabled ? '● Enabled' : '○ Disabled'}
                          </span>
                          <span className={`px-2 py-1 text-xs font-medium rounded-full ${getSeverityColor(rule.condition_json.severity)}`}>
                            {rule.condition_json.severity || 'warning'}
                          </span>
                        </div>

                        <div className="mt-2 flex items-center space-x-4 text-sm text-gray-600">
                          <span className="flex items-center">
                            <span className="font-medium mr-1">Type:</span>
                            {rule.type.charAt(0).toUpperCase() + rule.type.slice(1)}
                          </span>
                          <span className="flex items-center">
                            <span className="font-medium mr-1">Action:</span>
                            {rule.action.charAt(0).toUpperCase() + rule.action.slice(1)}
                          </span>
                        </div>

                        <p className="mt-2 text-sm text-gray-700">
                          <span className="font-medium">Condition:</span> {formatCondition(rule)}
                        </p>

                        <div className="mt-2 flex items-center space-x-4 text-xs text-gray-500">
                          <span>Created {timeAgo(rule.created_at)}</span>
                          {rule.last_triggered && (
                            <span className="text-blue-600">
                              ● Last triggered {timeAgo(rule.last_triggered)}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Actions */}
                      <div className="flex items-center space-x-2 ml-4">
                        <button
                          onClick={() => handleToggleEnabled(rule)}
                          className={`p-2 rounded-lg transition-colors ${
                            rule.enabled
                              ? 'text-green-600 hover:bg-green-50'
                              : 'text-gray-400 hover:bg-gray-100'
                          }`}
                          title={rule.enabled ? 'Disable rule' : 'Enable rule'}
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                        </button>
                        <button
                          onClick={() => handleOpenEdit(rule)}
                          className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                          title="Edit rule"
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                          </svg>
                        </button>
                        {deleteConfirm === rule.id ? (
                          <div className="flex items-center space-x-1">
                            <button
                              onClick={() => handleDeleteRule(rule.id)}
                              className="px-2 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700"
                            >
                              Confirm
                            </button>
                            <button
                              onClick={() => setDeleteConfirm(null)}
                              className="px-2 py-1 text-xs bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                            >
                              Cancel
                            </button>
                          </div>
                        ) : (
                          <button
                            onClick={() => setDeleteConfirm(rule.id)}
                            className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                            title="Delete rule"
                          >
                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Rule Form Modal */}
      <RuleFormModal
        isOpen={isModalOpen}
        onClose={() => {
          setIsModalOpen(false);
          setSelectedRule(null);
        }}
        onSave={modalMode === 'create' ? handleCreateRule : handleUpdateRule}
        rule={selectedRule}
        mode={modalMode}
      />
    </div>
  );
}
