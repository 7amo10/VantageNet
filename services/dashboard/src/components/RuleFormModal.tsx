'use client';

import { useState, useEffect } from 'react';

// Rule types and actions matching backend enums
export const RULE_TYPES = ['threshold', 'trend', 'duration', 'sentiment'] as const;
export const RULE_ACTIONS = ['log', 'alert', 'notification', 'webhook', 'email'] as const;
export const EMOTIONS = ['happy', 'sad', 'angry', 'surprised', 'neutral', 'disgusted', 'fearful'] as const;
export const SEVERITIES = ['info', 'warning', 'critical'] as const;
export const TREND_DIRECTIONS = ['improving', 'declining'] as const;

export type RuleType = typeof RULE_TYPES[number];
export type RuleAction = typeof RULE_ACTIONS[number];
export type Emotion = typeof EMOTIONS[number];
export type Severity = typeof SEVERITIES[number];
export type TrendDirection = typeof TREND_DIRECTIONS[number];

export interface Rule {
  id: string;
  name: string;
  type: RuleType;
  condition_json: Record<string, any>;
  action: RuleAction;
  enabled: boolean;
  created_at: string;
  updated_at: string;
  last_triggered?: string;
}

interface RuleFormModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (rule: Partial<Rule>) => Promise<void>;
  rule?: Rule | null;
  mode: 'create' | 'edit';
}

export default function RuleFormModal({ isOpen, onClose, onSave, rule, mode }: RuleFormModalProps) {
  const [formData, setFormData] = useState({
    name: '',
    type: 'threshold' as RuleType,
    action: 'alert' as RuleAction,
    enabled: true,
    // Threshold rule fields
    emotion: 'happy' as Emotion,
    threshold: 0.7,
    severity: 'warning' as Severity,
    // Trend rule fields
    direction: 'declining' as TrendDirection,
    magnitude_threshold: 0.3,
    window_size: 10,
    // Duration rule fields
    confidence: 0.6,
    duration_seconds: 30,
  });

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [isSaving, setIsSaving] = useState(false);

  // Initialize form with rule data when editing
  useEffect(() => {
    if (rule && mode === 'edit') {
      setFormData({
        name: rule.name,
        type: rule.type,
        action: rule.action,
        enabled: rule.enabled,
        emotion: rule.condition_json.emotion || 'happy',
        threshold: rule.condition_json.threshold || 0.7,
        severity: rule.condition_json.severity || 'warning',
        direction: rule.condition_json.direction || 'declining',
        magnitude_threshold: rule.condition_json.magnitude_threshold || 0.3,
        window_size: rule.condition_json.window_size || 10,
        confidence: rule.condition_json.min_confidence || rule.condition_json.confidence || 0.6,
        duration_seconds: rule.condition_json.duration_seconds || 30,
      });
    } else if (mode === 'create') {
      // Reset form for create mode
      setFormData({
        name: '',
        type: 'threshold',
        action: 'alert',
        enabled: true,
        emotion: 'happy',
        threshold: 0.7,
        severity: 'warning',
        direction: 'declining',
        magnitude_threshold: 0.3,
        window_size: 10,
        confidence: 0.6,
        duration_seconds: 30,
      });
    }
    setErrors({});
  }, [rule, mode, isOpen]);

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.name.trim()) {
      newErrors.name = 'Rule name is required';
    } else if (formData.name.length > 200) {
      newErrors.name = 'Rule name must be less than 200 characters';
    }

    // Type-specific validation
    if (formData.type === 'threshold') {
      if (formData.threshold < 0 || formData.threshold > 1) {
        newErrors.threshold = 'Threshold must be between 0.0 and 1.0';
      }
    } else if (formData.type === 'trend') {
      if (formData.magnitude_threshold < 0 || formData.magnitude_threshold > 1) {
        newErrors.magnitude_threshold = 'Magnitude threshold must be between 0.0 and 1.0';
      }
      if (formData.window_size < 2) {
        newErrors.window_size = 'Window size must be at least 2';
      }
    } else if (formData.type === 'duration') {
      if (formData.confidence < 0 || formData.confidence > 1) {
        newErrors.confidence = 'Confidence must be between 0.0 and 1.0';
      }
      if (formData.duration_seconds <= 0) {
        newErrors.duration_seconds = 'Duration must be greater than 0 seconds';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const buildConditionJson = (): Record<string, any> => {
    switch (formData.type) {
      case 'threshold':
        return {
          emotion: formData.emotion,
          threshold: formData.threshold,
          severity: formData.severity,
        };
      case 'trend':
        return {
          direction: formData.direction,
          magnitude_threshold: formData.magnitude_threshold,
          window_size: formData.window_size,
          severity: formData.severity,
        };
      case 'duration':
        return {
          emotion: formData.emotion,
          min_confidence: formData.confidence,
          duration_seconds: formData.duration_seconds,
          severity: formData.severity,
        };
      case 'sentiment':
        return {
          sentiment_threshold: formData.threshold,
          severity: formData.severity,
        };
      default:
        return {};
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsSaving(true);

    try {
      const ruleData: Partial<Rule> = {
        name: formData.name,
        type: formData.type,
        action: formData.action,
        enabled: formData.enabled,
        condition_json: buildConditionJson(),
      };

      if (mode === 'edit' && rule) {
        ruleData.id = rule.id;
      }

      await onSave(ruleData);
      onClose();
    } catch (error) {
      console.error('Error saving rule:', error);
      setErrors({ submit: 'Failed to save rule. Please try again.' });
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center sticky top-0 bg-white">
          <h2 className="text-2xl font-bold text-gray-900">
            {mode === 'create' ? 'Create New Rule' : 'Edit Rule'}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
            type="button"
          >
            ×
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="px-6 py-4 space-y-6">
          {/* Rule Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Rule Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                errors.name ? 'border-red-500' : 'border-gray-300'
              }`}
              placeholder="e.g., High Anger Detection"
              maxLength={200}
            />
            {errors.name && <p className="mt-1 text-sm text-red-600">{errors.name}</p>}
          </div>

          {/* Rule Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Rule Type <span className="text-red-500">*</span>
            </label>
            <select
              value={formData.type}
              onChange={(e) => setFormData({ ...formData, type: e.target.value as RuleType })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={mode === 'edit'} // Can't change type when editing
            >
              <option value="threshold">Threshold - Trigger when emotion exceeds threshold</option>
              <option value="trend">Trend - Detect sentiment trend changes</option>
              <option value="duration">Duration - Trigger after sustained emotion</option>
              <option value="sentiment">Sentiment - Overall sentiment threshold</option>
            </select>
            {mode === 'edit' && (
              <p className="mt-1 text-sm text-gray-500">Rule type cannot be changed after creation</p>
            )}
          </div>

          {/* Type-specific fields */}
          {formData.type === 'threshold' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Emotion <span className="text-red-500">*</span>
                </label>
                <select
                  value={formData.emotion}
                  onChange={(e) => setFormData({ ...formData, emotion: e.target.value as Emotion })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  {EMOTIONS.map((emotion) => (
                    <option key={emotion} value={emotion}>
                      {emotion.charAt(0).toUpperCase() + emotion.slice(1)}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Threshold: {formData.threshold.toFixed(2)}
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={formData.threshold}
                  onChange={(e) => setFormData({ ...formData, threshold: parseFloat(e.target.value) })}
                  className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>0.0 (Low)</span>
                  <span>0.5 (Medium)</span>
                  <span>1.0 (High)</span>
                </div>
                {errors.threshold && <p className="mt-1 text-sm text-red-600">{errors.threshold}</p>}
              </div>
            </>
          )}

          {formData.type === 'trend' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Trend Direction <span className="text-red-500">*</span>
                </label>
                <select
                  value={formData.direction}
                  onChange={(e) => setFormData({ ...formData, direction: e.target.value as TrendDirection })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  <option value="improving">Improving - Sentiment getting more positive</option>
                  <option value="declining">Declining - Sentiment getting more negative</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Magnitude Threshold: {formData.magnitude_threshold.toFixed(2)}
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={formData.magnitude_threshold}
                  onChange={(e) => setFormData({ ...formData, magnitude_threshold: parseFloat(e.target.value) })}
                  className="w-full"
                />
                <p className="text-xs text-gray-500 mt-1">Minimum change to trigger the rule</p>
                {errors.magnitude_threshold && <p className="mt-1 text-sm text-red-600">{errors.magnitude_threshold}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Window Size (samples)
                </label>
                <input
                  type="number"
                  min="2"
                  max="100"
                  value={formData.window_size}
                  onChange={(e) => setFormData({ ...formData, window_size: parseInt(e.target.value) || 10 })}
                  className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                    errors.window_size ? 'border-red-500' : 'border-gray-300'
                  }`}
                />
                <p className="text-xs text-gray-500 mt-1">Number of samples to analyze for trend</p>
                {errors.window_size && <p className="mt-1 text-sm text-red-600">{errors.window_size}</p>}
              </div>
            </>
          )}

          {formData.type === 'duration' && (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Emotion <span className="text-red-500">*</span>
                </label>
                <select
                  value={formData.emotion}
                  onChange={(e) => setFormData({ ...formData, emotion: e.target.value as Emotion })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  {EMOTIONS.map((emotion) => (
                    <option key={emotion} value={emotion}>
                      {emotion.charAt(0).toUpperCase() + emotion.slice(1)}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Confidence Threshold: {formData.confidence.toFixed(2)}
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.01"
                  value={formData.confidence}
                  onChange={(e) => setFormData({ ...formData, confidence: parseFloat(e.target.value) })}
                  className="w-full"
                />
                <p className="text-xs text-gray-500 mt-1">Minimum confidence for emotion detection</p>
                {errors.confidence && <p className="mt-1 text-sm text-red-600">{errors.confidence}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Duration (seconds)
                </label>
                <input
                  type="number"
                  min="1"
                  max="3600"
                  value={formData.duration_seconds}
                  onChange={(e) => setFormData({ ...formData, duration_seconds: parseInt(e.target.value) || 30 })}
                  className={`w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                    errors.duration_seconds ? 'border-red-500' : 'border-gray-300'
                  }`}
                />
                <p className="text-xs text-gray-500 mt-1">How long the emotion must persist</p>
                {errors.duration_seconds && <p className="mt-1 text-sm text-red-600">{errors.duration_seconds}</p>}
              </div>
            </>
          )}

          {formData.type === 'sentiment' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Sentiment Threshold: {formData.threshold.toFixed(2)}
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={formData.threshold}
                onChange={(e) => setFormData({ ...formData, threshold: parseFloat(e.target.value) })}
                className="w-full"
              />
              <p className="text-xs text-gray-500 mt-1">Overall sentiment score threshold</p>
              {errors.threshold && <p className="mt-1 text-sm text-red-600">{errors.threshold}</p>}
            </div>
          )}

          {/* Common fields for all types */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Severity <span className="text-red-500">*</span>
            </label>
            <select
              value={formData.severity}
              onChange={(e) => setFormData({ ...formData, severity: e.target.value as Severity })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="info">ℹ️ Info - Informational alerts</option>
              <option value="warning">⚠️ Warning - Important but not critical</option>
              <option value="critical">🚨 Critical - Requires immediate attention</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Action <span className="text-red-500">*</span>
            </label>
            <select
              value={formData.action}
              onChange={(e) => setFormData({ ...formData, action: e.target.value as RuleAction })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              {RULE_ACTIONS.map((action) => (
                <option key={action} value={action}>
                  {action.charAt(0).toUpperCase() + action.slice(1)}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center">
            <input
              type="checkbox"
              id="enabled"
              checked={formData.enabled}
              onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
              className="w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
            />
            <label htmlFor="enabled" className="ml-2 text-sm font-medium text-gray-700">
              Enable rule immediately
            </label>
          </div>

          {errors.submit && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3">
              <p className="text-sm text-red-800">{errors.submit}</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end space-x-3 pt-4 border-t border-gray-200">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
              disabled={isSaving}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
              disabled={isSaving}
            >
              {isSaving ? 'Saving...' : mode === 'create' ? 'Create Rule' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
