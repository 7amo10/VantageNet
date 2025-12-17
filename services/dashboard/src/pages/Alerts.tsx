'use client';

import React, { useState } from 'react';
import AlertsList from '../components/AlertsList';
import AlertDetails from '../components/AlertDetails';
import './Alerts.css';

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

const Alerts: React.FC = () => {
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  // Handle alert selection
  const handleAlertSelect = (alert: Alert) => {
    setSelectedAlert(alert);
  };

  // Handle modal close
  const handleCloseDetails = () => {
    setSelectedAlert(null);
  };

  // Handle update (after acknowledge/dismiss)
  const handleUpdate = () => {
    setRefreshKey(prev => prev + 1);
  };

  return (
    <div className="alerts-page">
      {/* Header */}
      <div className="page-header">
        <h1>Alert Management</h1>
        <p className="page-description">
          Monitor and manage alerts triggered by emotion detection rules
        </p>
      </div>

      {/* Alerts List */}
      <AlertsList 
        key={refreshKey}
        onAlertSelect={handleAlertSelect} 
      />

      {/* Alert Details Modal */}
      <AlertDetails
        alert={selectedAlert}
        onClose={handleCloseDetails}
        onUpdate={handleUpdate}
      />
    </div>
  );
};

export default Alerts;
