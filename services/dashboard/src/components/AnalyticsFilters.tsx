'use client';

import React, { useState, useEffect } from 'react';
import './AnalyticsFilters.css';

interface Camera {
  id: string;
  name: string;
}

interface AnalyticsFiltersProps {
  onFilterChange: (filters: FilterValues) => void;
  onExport: () => void;
}

export interface FilterValues {
  startDate: string;
  endDate: string;
  cameraId: string;
  interval: string;
}

const AnalyticsFilters: React.FC<AnalyticsFiltersProps> = ({ onFilterChange, onExport }) => {
  const [cameras, setCameras] = useState<Camera[]>([]);
  const [filters, setFilters] = useState<FilterValues>({
    startDate: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    endDate: new Date().toISOString().split('T')[0],
    cameraId: '',
    interval: 'hour',
  });

  useEffect(() => {
    fetchCameras();
  }, []);

  const fetchCameras = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/cameras/');
      if (response.ok) {
        const data = await response.json();
        setCameras(data.cameras || []);
      }
    } catch (error) {
      console.error('Failed to fetch cameras:', error);
    }
  };

  const handleFilterChange = (field: keyof FilterValues, value: string) => {
    const newFilters = { ...filters, [field]: value };
    setFilters(newFilters);
    onFilterChange(newFilters);
  };

  const handlePresetRange = (days: number) => {
    const endDate = new Date();
    const startDate = new Date(Date.now() - days * 24 * 60 * 60 * 1000);
    const newFilters = {
      ...filters,
      startDate: startDate.toISOString().split('T')[0],
      endDate: endDate.toISOString().split('T')[0],
    };
    setFilters(newFilters);
    onFilterChange(newFilters);
  };

  return (
    <div className="analytics-filters">
      <div className="filters-header">
        <h2>Analytics Dashboard</h2>
        <button className="export-button" onClick={onExport}>
          📊 Export CSV
        </button>
      </div>

      <div className="filters-container">
        {/* Date Range Presets */}
        <div className="filter-group">
          <label>Quick Range</label>
          <div className="preset-buttons">
            <button onClick={() => handlePresetRange(1)} className="preset-btn">
              Today
            </button>
            <button onClick={() => handlePresetRange(7)} className="preset-btn">
              Last 7 Days
            </button>
            <button onClick={() => handlePresetRange(30)} className="preset-btn">
              Last 30 Days
            </button>
            <button onClick={() => handlePresetRange(90)} className="preset-btn">
              Last 90 Days
            </button>
          </div>
        </div>

        {/* Custom Date Range */}
        <div className="filter-row">
          <div className="filter-group">
            <label htmlFor="start-date">Start Date</label>
            <input
              type="date"
              id="start-date"
              value={filters.startDate}
              onChange={(e) => handleFilterChange('startDate', e.target.value)}
              max={filters.endDate}
            />
          </div>

          <div className="filter-group">
            <label htmlFor="end-date">End Date</label>
            <input
              type="date"
              id="end-date"
              value={filters.endDate}
              onChange={(e) => handleFilterChange('endDate', e.target.value)}
              min={filters.startDate}
              max={new Date().toISOString().split('T')[0]}
            />
          </div>

          <div className="filter-group">
            <label htmlFor="camera">Camera</label>
            <select
              id="camera"
              value={filters.cameraId}
              onChange={(e) => handleFilterChange('cameraId', e.target.value)}
            >
              <option value="">All Cameras</option>
              {cameras.map((camera) => (
                <option key={camera.id} value={camera.id}>
                  {camera.name}
                </option>
              ))}
            </select>
          </div>

          <div className="filter-group">
            <label htmlFor="interval">Time Interval</label>
            <select
              id="interval"
              value={filters.interval}
              onChange={(e) => handleFilterChange('interval', e.target.value)}
            >
              <option value="hour">Hourly</option>
              <option value="day">Daily</option>
              <option value="week">Weekly</option>
              <option value="month">Monthly</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsFilters;
