'use client';

import { useState, useEffect } from 'react';

interface Camera {
  id: string;
  name: string;
  status: 'online' | 'offline';
  location?: string;
}

interface CameraSelectorProps {
  cameras: Camera[];
  selectedCameraId: string;
  onCameraChange: (cameraId: string) => void;
  isLoading?: boolean;
}

export default function CameraSelector({
  cameras,
  selectedCameraId,
  onCameraChange,
  isLoading = false,
}: CameraSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);

  const selectedCamera = cameras.find(c => c.id === selectedCameraId);

  const handleSelect = (cameraId: string) => {
    onCameraChange(cameraId);
    setIsOpen(false);
  };

  return (
    <div className="relative inline-block w-full max-w-xs">
      {/* Selected camera button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isLoading}
        className="w-full flex items-center justify-between bg-white border-2 border-gray-300 rounded-lg px-4 py-3 hover:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <div className="flex items-center gap-3">
          {/* Camera icon */}
          <div className="text-2xl">📹</div>
          
          {/* Camera info */}
          <div className="text-left">
            <div className="font-semibold text-gray-800">
              {selectedCamera?.name || 'Select Camera'}
            </div>
            {selectedCamera?.location && (
              <div className="text-xs text-gray-500">{selectedCamera.location}</div>
            )}
          </div>
        </div>

        {/* Status indicator */}
        <div className="flex items-center gap-2">
          {selectedCamera && (
            <div className={`w-2 h-2 rounded-full ${selectedCamera.status === 'online' ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
          )}
          
          {/* Dropdown arrow */}
          <svg
            className={`w-5 h-5 text-gray-600 transition-transform ${isOpen ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {/* Dropdown menu */}
      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />

          {/* Options */}
          <div className="absolute z-20 w-full mt-2 bg-white border-2 border-gray-300 rounded-lg shadow-xl max-h-80 overflow-y-auto">
            {cameras.length > 0 ? (
              <ul className="py-2">
                {cameras.map((camera) => {
                  const isSelected = camera.id === selectedCameraId;
                  return (
                    <li key={camera.id}>
                      <button
                        onClick={() => handleSelect(camera.id)}
                        className={`w-full flex items-center justify-between px-4 py-3 hover:bg-blue-50 transition-colors ${
                          isSelected ? 'bg-blue-100' : ''
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          {/* Camera icon */}
                          <div className="text-xl">📹</div>
                          
                          {/* Camera info */}
                          <div className="text-left">
                            <div className={`font-medium ${isSelected ? 'text-blue-700' : 'text-gray-800'}`}>
                              {camera.name}
                            </div>
                            {camera.location && (
                              <div className="text-xs text-gray-500">{camera.location}</div>
                            )}
                          </div>
                        </div>

                        <div className="flex items-center gap-2">
                          {/* Status indicator */}
                          <div className="flex items-center gap-1">
                            <div className={`w-2 h-2 rounded-full ${camera.status === 'online' ? 'bg-green-500' : 'bg-red-500'}`} />
                            <span className={`text-xs font-medium ${camera.status === 'online' ? 'text-green-700' : 'text-red-700'}`}>
                              {camera.status}
                            </span>
                          </div>

                          {/* Selected checkmark */}
                          {isSelected && (
                            <svg className="w-5 h-5 text-blue-600" fill="currentColor" viewBox="0 0 20 20">
                              <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                            </svg>
                          )}
                        </div>
                      </button>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <div className="px-4 py-8 text-center text-gray-500">
                <div className="text-4xl mb-2">📹</div>
                <p className="font-medium">No cameras available</p>
                <p className="text-sm mt-1">Check your camera connections</p>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
