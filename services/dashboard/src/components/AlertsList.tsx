'use client';

import React, { useState, useEffect } from 'react';
import './AlertsList.css';

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

interface AlertsListProps {
  onAlertSelect?: (alert: Alert) => void;
}

const AlertsList: React.FC<AlertsListProps> = ({ onAlertSelect }) => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Filters
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  
  // Sorting
  const [sortBy, setSortBy] = useState<string>('triggered_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  
  // Pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(10);

  // Fetch alerts
  const fetchAlerts = async () => {
    try {
      setLoading(true);
      setError(null);

      // Build query params
      const params = new URLSearchParams();
      if (severityFilter !== 'all') params.append('severity', severityFilter);
      if (statusFilter !== 'all') params.append('status', statusFilter);
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      params.append('sort_by', sortBy);
      params.append('sort_order', sortOrder);
      params.append('page', currentPage.toString());
      params.append('limit', itemsPerPage.toString());

      const response = await fetch(`http://localhost:8000/api/alerts/?${params.toString()}`);
      
      if (!response.ok) {
        throw new Error(`Failed to fetch alerts: ${response.statusText}`);
      }

      const data = await response.json();
      setAlerts(data.alerts || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch alerts');
      console.error('Error fetching alerts:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, [severityFilter, statusFilter, startDate, endDate, sortBy, sortOrder, currentPage]);

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
    return date.toLocaleString();
  };

  // Handle sort
  const handleSort = (field: string) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('desc');
    }
  };

  // Reset filters
  const resetFilters = () => {
    setSeverityFilter('all');
    setStatusFilter('all');
    setStartDate('');
    setEndDate('');
    setCurrentPage(1);
  };

  if (loading) {
    return <div className="loading">Loading alerts...</div>;
  }

  if (error) {
    return (
      <div className="error-container">
        <p className="error">{error}</p>
        <button onClick={fetchAlerts}>Retry</button>
      </div>
    );
  }

  return (
    <div className="alerts-list-container">
      {/* Filters Section */}
      <div className="filters-section">
        <h3>Filters</h3>
        
        <div className="filters-row">
          <div className="filter-group">
            <label>Severity:</label>
            <select 
              value={severityFilter} 
              onChange={(e) => setSeverityFilter(e.target.value)}
            >
              <option value="all">All</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>

          <div className="filter-group">
            <label>Status:</label>
            <select 
              value={statusFilter} 
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="all">All</option>
              <option value="active">Active</option>
              <option value="acknowledged">Acknowledged</option>
            </select>
          </div>

          <div className="filter-group">
            <label>From:</label>
            <input 
              type="date" 
              value={startDate} 
              onChange={(e) => setStartDate(e.target.value)}
            />
          </div>

          <div className="filter-group">
            <label>To:</label>
            <input 
              type="date" 
              value={endDate} 
              onChange={(e) => setEndDate(e.target.value)}
            />
          </div>

          <button className="reset-button" onClick={resetFilters}>
            Reset Filters
          </button>
        </div>
      </div>

      {/* Alerts Table */}
      <div className="alerts-table-container">
        <table className="alerts-table">
          <thead>
            <tr>
              <th onClick={() => handleSort('severity')} className="sortable">
                Severity {sortBy === 'severity' && (sortOrder === 'asc' ? '↑' : '↓')}
              </th>
              <th onClick={() => handleSort('rule_name')} className="sortable">
                Rule {sortBy === 'rule_name' && (sortOrder === 'asc' ? '↑' : '↓')}
              </th>
              <th onClick={() => handleSort('camera_name')} className="sortable">
                Camera {sortBy === 'camera_name' && (sortOrder === 'asc' ? '↑' : '↓')}
              </th>
              <th>Message</th>
              <th onClick={() => handleSort('triggered_at')} className="sortable">
                Triggered At {sortBy === 'triggered_at' && (sortOrder === 'asc' ? '↑' : '↓')}
              </th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {alerts.length === 0 ? (
              <tr>
                <td colSpan={7} className="no-alerts">
                  No alerts found
                </td>
              </tr>
            ) : (
              alerts.map((alert) => (
                <tr key={alert.id} className={alert.acknowledged ? 'acknowledged-row' : ''}>
                  <td>
                    <span className={`severity-badge ${getSeverityClass(alert.severity)}`}>
                      {alert.severity.toUpperCase()}
                    </span>
                  </td>
                  <td>{alert.rule_name}</td>
                  <td>{alert.camera_name}</td>
                  <td className="message-cell">{alert.message}</td>
                  <td>{formatTimestamp(alert.triggered_at)}</td>
                  <td>
                    {alert.acknowledged ? (
                      <span className="status-acknowledged">✓ Acknowledged</span>
                    ) : (
                      <span className="status-active">● Active</span>
                    )}
                  </td>
                  <td>
                    <button 
                      className="view-button"
                      onClick={() => onAlertSelect && onAlertSelect(alert)}
                    >
                      View
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="pagination">
        <button 
          onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
          disabled={currentPage === 1}
        >
          Previous
        </button>
        <span>Page {currentPage}</span>
        <button 
          onClick={() => setCurrentPage(p => p + 1)}
          disabled={alerts.length < itemsPerPage}
        >
          Next
        </button>
      </div>
    </div>
  );
};

export default AlertsList;
