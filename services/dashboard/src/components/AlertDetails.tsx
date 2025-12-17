'use client';

import React, { useState } from 'react';
import './AlertDetails.css';

interface Alert {
  id: string;
  rule_id: string;
  rule_name: string;
  camera_id: string;
  camera_name: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  triggered_at: string;
  acknowledged: boolean;
  acknowledged_at?: string;
  acknowledged_by?: string;
  metadata?: Record<string, any>;
}

interface AlertDetailsProps {
  alert: Alert | null;
  onClose: () => void;
  onUpdate: () => void;
}

const AlertDetails: React.FC<AlertDetailsProps> = ({ alert, onClose, onUpdate }) => {
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!alert) return null;

  // Get severity color class
  const getSeverityClass = (severity: string): string => {
    switch (severity) {
      case 'critical':
        return 'severity-critical';
      case 'high':
        return 'severity-high';
      case 'medium':
        return 'severity-medium';
      case 'low':
        return 'severity-low';
      default:
        return '';
    }
  };

  // Format timestamp
  const formatTimestamp = (timestamp: string): string => {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  };

  // Handle acknowledge
  const handleAcknowledge = async () => {
    try {
      setProcessing(true);
      setError(null);

      const response = await fetch(`http://localhost:8000/api/alerts/${alert.id}/`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          acknowledged: true
        })
      });

      if (!response.ok) {
        throw new Error(`Failed to acknowledge alert: ${response.statusText}`);
      }

      onUpdate();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to acknowledge alert');
      console.error('Error acknowledging alert:', err);
    } finally {
      setProcessing(false);
    }
  };

  // Handle dismiss
  const handleDismiss = async () => {
    if (!confirm('Are you sure you want to dismiss this alert? This action cannot be undone.')) {
      return;
    }

    try {
      setProcessing(true);
      setError(null);

      const response = await fetch(`http://localhost:8000/api/alerts/${alert.id}/`, {
        method: 'DELETE'
      });

      if (!response.ok) {
        throw new Error(`Failed to dismiss alert: ${response.statusText}`);
      }

      onUpdate();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to dismiss alert');
      console.error('Error dismissing alert:', err);
    } finally {
      setProcessing(false);
    }
  };

  // Render metadata if available
  const renderMetadata = () => {
    if (!alert.metadata || Object.keys(alert.metadata).length === 0) {
      return <p className="no-metadata">No additional metadata</p>;
    }

    return (
      <div className="metadata-grid">
        {Object.entries(alert.metadata).map(([key, value]) => (
          <div key={key} className="metadata-item">
            <span className="metadata-key">{key}:</span>
            <span className="metadata-value">
              {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
            </span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="alert-details-overlay" onClick={onClose}>
      <div className="alert-details-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <h2>Alert Details</h2>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        {/* Content */}
        <div className="modal-content">
          {error && <div className="error-message">{error}</div>}

          {/* Severity Badge */}
          <div className="detail-section">
            <h3>Severity</h3>
            <span className={`severity-badge ${getSeverityClass(alert.severity)}`}>
              {alert.severity.toUpperCase()}
            </span>
          </div>

          {/* Message */}
          <div className="detail-section">
            <h3>Message</h3>
            <p className="alert-message">{alert.message}</p>
          </div>

          {/* Rule Information */}
          <div className="detail-section">
            <h3>Rule Information</h3>
            <div className="info-grid">
              <div className="info-item">
                <span className="info-label">Rule Name:</span>
                <span className="info-value">{alert.rule_name}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Rule ID:</span>
                <span className="info-value">{alert.rule_id}</span>
              </div>
            </div>
          </div>

          {/* Camera Information */}
          <div className="detail-section">
            <h3>Camera Information</h3>
            <div className="info-grid">
              <div className="info-item">
                <span className="info-label">Camera Name:</span>
                <span className="info-value">{alert.camera_name}</span>
              </div>
              <div className="info-item">
                <span className="info-label">Camera ID:</span>
                <span className="info-value">{alert.camera_id}</span>
              </div>
            </div>
          </div>

          {/* Timestamp Information */}
          <div className="detail-section">
            <h3>Timestamp</h3>
            <div className="info-grid">
              <div className="info-item">
                <span className="info-label">Triggered At:</span>
                <span className="info-value">{formatTimestamp(alert.triggered_at)}</span>
              </div>
              {alert.acknowledged && (
                <>
                  <div className="info-item">
                    <span className="info-label">Acknowledged At:</span>
                    <span className="info-value">
                      {alert.acknowledged_at ? formatTimestamp(alert.acknowledged_at) : 'N/A'}
                    </span>
                  </div>
                  {alert.acknowledged_by && (
                    <div className="info-item">
                      <span className="info-label">Acknowledged By:</span>
                      <span className="info-value">{alert.acknowledged_by}</span>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>

          {/* Status */}
          <div className="detail-section">
            <h3>Status</h3>
            {alert.acknowledged ? (
              <span className="status-badge status-acknowledged">✓ Acknowledged</span>
            ) : (
              <span className="status-badge status-active">● Active</span>
            )}
          </div>

          {/* Metadata */}
          <div className="detail-section">
            <h3>Additional Metadata</h3>
            {renderMetadata()}
          </div>
        </div>

        {/* Actions */}
        <div className="modal-actions">
          {!alert.acknowledged && (
            <button
              className="acknowledge-button"
              onClick={handleAcknowledge}
              disabled={processing}
            >
              {processing ? 'Processing...' : 'Acknowledge'}
            </button>
          )}
          <button
            className="dismiss-button"
            onClick={handleDismiss}
            disabled={processing}
          >
            {processing ? 'Processing...' : 'Dismiss'}
          </button>
          <button className="cancel-button" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default AlertDetails;
