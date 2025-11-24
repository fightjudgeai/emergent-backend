import React, { useState, useEffect } from 'react';
import { Video, Camera, Activity, AlertCircle, CheckCircle, XCircle, Play, Square, Eye } from 'lucide-react';

const RealtimeCVPanel = ({ boutId }) => {
  const [cvState, setCVState] = useState({
    activeStreams: [],
    recentDetections: [],
    models: [],
    stats: null,
    isLoading: false
  });
  
  const [showDashboard, setShowDashboard] = useState(false);
  const [streamConfig, setStreamConfig] = useState({
    camera_id: 'main_camera',
    stream_url: '',
    stream_type: 'rtsp',
    fps_target: 30,
    analysis_fps: 10,
    enable_pose_estimation: true,
    enable_action_detection: true
  });

  const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

  // Load CV models on mount
  useEffect(() => {
    loadCVModels();
    loadActiveStreams();
    
    // Refresh every 5 seconds
    const interval = setInterval(() => {
      loadActiveStreams();
      if (boutId) {
        loadRecentDetections();
        loadStats();
      }
    }, 5000);
    
    return () => clearInterval(interval);
  }, [boutId]);

  const loadCVModels = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/realtime-cv/models`);
      const data = await response.json();
      setCVState(prev => ({ ...prev, models: data.models || [] }));
    } catch (error) {
      console.error('Error loading CV models:', error);
    }
  };

  const loadActiveStreams = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/realtime-cv/streams/active`);
      const data = await response.json();
      setCVState(prev => ({ ...prev, activeStreams: data.active_streams || [] }));
    } catch (error) {
      console.error('Error loading active streams:', error);
    }
  };

  const loadRecentDetections = async () => {
    if (!boutId) return;
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/realtime-cv/detections/${boutId}?limit=20`);
      const data = await response.json();
      setCVState(prev => ({ ...prev, recentDetections: data.detections || [] }));
    } catch (error) {
      console.error('Error loading detections:', error);
    }
  };

  const loadStats = async () => {
    if (!boutId) return;
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/realtime-cv/stats/${boutId}`);
      const data = await response.json();
      setCVState(prev => ({ ...prev, stats: data }));
    } catch (error) {
      console.error('Error loading stats:', error);
    }
  };

  const startStream = async () => {
    if (!streamConfig.stream_url || !boutId) {
      alert('Please enter a stream URL');
      return;
    }

    setCVState(prev => ({ ...prev, isLoading: true }));
    
    try {
      const response = await fetch(`${BACKEND_URL}/api/realtime-cv/streams/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...streamConfig,
          bout_id: boutId
        })
      });
      
      const data = await response.json();
      
      if (response.ok) {
        alert(`Stream started: ${data.stream_id}`);
        loadActiveStreams();
      } else {
        alert(`Error: ${data.detail || 'Failed to start stream'}`);
      }
    } catch (error) {
      console.error('Error starting stream:', error);
      alert('Failed to start stream');
    } finally {
      setCVState(prev => ({ ...prev, isLoading: false }));
    }
  };

  const stopStream = async (streamId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/realtime-cv/streams/stop/${streamId}`, {
        method: 'POST'
      });
      
      if (response.ok) {
        alert('Stream stopped');
        loadActiveStreams();
      } else {
        alert('Failed to stop stream');
      }
    } catch (error) {
      console.error('Error stopping stream:', error);
    }
  };

  const simulateFrames = async () => {
    if (!boutId) return;
    
    setCVState(prev => ({ ...prev, isLoading: true }));
    
    try {
      const response = await fetch(
        `${BACKEND_URL}/api/realtime-cv/simulate/frame?bout_id=${boutId}&camera_id=main&frame_count=10`,
        { method: 'POST' }
      );
      
      const data = await response.json();
      
      if (response.ok) {
        alert(`Simulated 10 frames: ${data.total_detections} detections found`);
        loadRecentDetections();
        loadStats();
      }
    } catch (error) {
      console.error('Error simulating frames:', error);
    } finally {
      setCVState(prev => ({ ...prev, isLoading: false }));
    }
  };

  const getActionColor = (actionType) => {
    const colors = {
      'punch_thrown': 'bg-red-500',
      'kick_thrown': 'bg-orange-500',
      'knee_thrown': 'bg-yellow-500',
      'takedown_attempt': 'bg-blue-500',
      'strike_landed': 'bg-green-500',
      'clinch_engaged': 'bg-purple-500',
      'submission_attempt': 'bg-pink-500'
    };
    return colors[actionType] || 'bg-gray-500';
  };

  return (
    <div className="bg-gradient-to-br from-indigo-900 via-purple-900 to-pink-900 rounded-lg p-6 text-white shadow-lg">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Video className="w-6 h-6 text-cyan-400" />
          <h3 className="text-xl font-bold">Real-Time CV System</h3>
        </div>
        <button
          onClick={() => setShowDashboard(!showDashboard)}
          className="px-4 py-2 bg-cyan-600 hover:bg-cyan-700 rounded-lg flex items-center gap-2 transition-colors"
        >
          <Eye className="w-4 h-4" />
          {showDashboard ? 'Hide Dashboard' : 'Show Dashboard'}
        </button>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="bg-black/30 rounded-lg p-3 backdrop-blur-sm">
          <div className="text-xs text-gray-300 mb-1">Active Streams</div>
          <div className="text-2xl font-bold text-cyan-400">{cvState.activeStreams.length}</div>
        </div>
        <div className="bg-black/30 rounded-lg p-3 backdrop-blur-sm">
          <div className="text-xs text-gray-300 mb-1">Loaded Models</div>
          <div className="text-2xl font-bold text-green-400">
            {cvState.models.filter(m => m.is_loaded).length}/{cvState.models.length}
          </div>
        </div>
        <div className="bg-black/30 rounded-lg p-3 backdrop-blur-sm">
          <div className="text-xs text-gray-300 mb-1">Total Detections</div>
          <div className="text-2xl font-bold text-purple-400">
            {cvState.stats?.total_detections || 0}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="flex gap-3 mb-4">
        <button
          onClick={simulateFrames}
          disabled={!boutId || cvState.isLoading}
          className="flex-1 px-4 py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 rounded-lg font-semibold disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center justify-center gap-2"
        >
          <Activity className="w-4 h-4" />
          Simulate CV Detection
        </button>
      </div>

      {/* Active Streams */}
      {cvState.activeStreams.length > 0 && (
        <div className="bg-black/30 rounded-lg p-4 backdrop-blur-sm mb-4">
          <div className="text-sm font-semibold mb-2 flex items-center gap-2">
            <Play className="w-4 h-4 text-green-400" />
            Active Streams ({cvState.activeStreams.length})
          </div>
          <div className="space-y-2">
            {cvState.activeStreams.map(stream => (
              <div key={stream.stream_id} className="flex items-center justify-between bg-black/20 rounded p-2">
                <div>
                  <div className="text-sm font-medium">{stream.camera_id}</div>
                  <div className="text-xs text-gray-400">{stream.stream_type.toUpperCase()} • {stream.fps_target} FPS</div>
                </div>
                <button
                  onClick={() => stopStream(stream.stream_id)}
                  className="px-3 py-1 bg-red-600 hover:bg-red-700 rounded text-xs flex items-center gap-1"
                >
                  <Square className="w-3 h-3" />
                  Stop
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Detections */}
      {cvState.recentDetections.length > 0 && (
        <div className="bg-black/30 rounded-lg p-4 backdrop-blur-sm">
          <div className="text-sm font-semibold mb-2">Recent Detections (Last 10)</div>
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {cvState.recentDetections.slice(0, 10).map((detection, idx) => (
              <div key={idx} className="flex items-center justify-between text-xs bg-black/20 rounded p-2">
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${getActionColor(detection.action_type)}`}></div>
                  <span className="font-medium">{detection.action_type.replace('_', ' ')}</span>
                  <span className="text-gray-400">• {detection.fighter_id}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-gray-400">{(detection.confidence * 100).toFixed(0)}%</span>
                  {detection.power_estimate && (
                    <span className="text-orange-400">⚡{detection.power_estimate.toFixed(1)}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* CV Dashboard Modal */}
      {showDashboard && (
        <CVManagementDashboard
          boutId={boutId}
          cvState={cvState}
          streamConfig={streamConfig}
          setStreamConfig={setStreamConfig}
          onStartStream={startStream}
          onClose={() => setShowDashboard(false)}
        />
      )}
    </div>
  );
};

// CV Management Dashboard Component
const CVManagementDashboard = ({ boutId, cvState, streamConfig, setStreamConfig, onStartStream, onClose }) => {
  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="bg-gradient-to-br from-gray-900 to-gray-800 rounded-xl max-w-6xl w-full max-h-[90vh] overflow-y-auto p-6 text-white">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <Camera className="w-8 h-8 text-cyan-400" />
            <h2 className="text-2xl font-bold">CV Management Dashboard</h2>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg"
          >
            Close
          </button>
        </div>

        {/* Stream Configuration */}
        <div className="bg-black/30 rounded-lg p-6 mb-6">
          <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
            <Video className="w-5 h-5 text-green-400" />
            Start New Video Stream
          </h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm mb-1">Camera ID</label>
              <input
                type="text"
                value={streamConfig.camera_id}
                onChange={(e) => setStreamConfig(prev => ({ ...prev, camera_id: e.target.value }))}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg"
                placeholder="main_camera"
              />
            </div>
            <div>
              <label className="block text-sm mb-1">Stream Type</label>
              <select
                value={streamConfig.stream_type}
                onChange={(e) => setStreamConfig(prev => ({ ...prev, stream_type: e.target.value }))}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg"
              >
                <option value="rtsp">RTSP (IP Camera)</option>
                <option value="rtmp">RTMP (Streaming)</option>
                <option value="http">HTTP (Stream URL)</option>
                <option value="webcam">Webcam</option>
              </select>
            </div>
            <div className="col-span-2">
              <label className="block text-sm mb-1">Stream URL</label>
              <input
                type="text"
                value={streamConfig.stream_url}
                onChange={(e) => setStreamConfig(prev => ({ ...prev, stream_url: e.target.value }))}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg"
                placeholder="rtsp://192.168.1.100:554/stream or http://camera-url/stream.m3u8"
              />
              <div className="text-xs text-gray-400 mt-1">
                Examples: rtsp://camera-ip:554/stream, http://stream-url/video.m3u8, or "0" for webcam
              </div>
            </div>
            <div>
              <label className="block text-sm mb-1">Target FPS</label>
              <input
                type="number"
                value={streamConfig.fps_target}
                onChange={(e) => setStreamConfig(prev => ({ ...prev, fps_target: parseInt(e.target.value) }))}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg"
                min="10"
                max="60"
              />
            </div>
            <div>
              <label className="block text-sm mb-1">Analysis FPS</label>
              <input
                type="number"
                value={streamConfig.analysis_fps}
                onChange={(e) => setStreamConfig(prev => ({ ...prev, analysis_fps: parseInt(e.target.value) }))}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-lg"
                min="1"
                max="30"
              />
            </div>
            <div className="col-span-2 flex gap-4">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={streamConfig.enable_pose_estimation}
                  onChange={(e) => setStreamConfig(prev => ({ ...prev, enable_pose_estimation: e.target.checked }))}
                  className="w-4 h-4"
                />
                <span className="text-sm">Enable Pose Estimation</span>
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={streamConfig.enable_action_detection}
                  onChange={(e) => setStreamConfig(prev => ({ ...prev, enable_action_detection: e.target.checked }))}
                  className="w-4 h-4"
                />
                <span className="text-sm">Enable Action Detection</span>
              </label>
            </div>
          </div>
          <button
            onClick={onStartStream}
            disabled={!streamConfig.stream_url || !boutId}
            className="mt-4 w-full px-6 py-3 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 rounded-lg font-semibold disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            <Play className="w-5 h-5" />
            Start Video Stream Analysis
          </button>
        </div>

        {/* Loaded Models */}
        <div className="bg-black/30 rounded-lg p-6 mb-6">
          <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
            <Activity className="w-5 h-5 text-purple-400" />
            Loaded CV Models ({cvState.models.filter(m => m.is_loaded).length}/{cvState.models.length})
          </h3>
          <div className="grid grid-cols-3 gap-4">
            {cvState.models.map((model, idx) => (
              <div key={idx} className="bg-black/20 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  {model.is_loaded ? (
                    <CheckCircle className="w-4 h-4 text-green-400" />
                  ) : (
                    <XCircle className="w-4 h-4 text-red-400" />
                  )}
                  <span className="font-semibold text-sm">{model.model_name}</span>
                </div>
                <div className="text-xs text-gray-400 space-y-1">
                  <div>Type: {model.model_type}</div>
                  <div>Framework: {model.framework}</div>
                  <div>Version: {model.version}</div>
                  <div>Inference: {model.inference_time_ms.toFixed(1)}ms</div>
                  {model.accuracy && <div>Accuracy: {(model.accuracy * 100).toFixed(0)}%</div>}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Detection Statistics */}
        {cvState.stats && cvState.stats.total_detections > 0 && (
          <div className="bg-black/30 rounded-lg p-6">
            <h3 className="text-lg font-bold mb-4">Detection Statistics</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-sm text-gray-400 mb-2">Total Detections</div>
                <div className="text-3xl font-bold text-cyan-400">{cvState.stats.total_detections}</div>
              </div>
              <div>
                <div className="text-sm text-gray-400 mb-2">Average Confidence</div>
                <div className="text-3xl font-bold text-green-400">
                  {(cvState.stats.avg_confidence * 100).toFixed(0)}%
                </div>
              </div>
            </div>
            {cvState.stats.actions && Object.keys(cvState.stats.actions).length > 0 && (
              <div className="mt-4">
                <div className="text-sm font-semibold mb-2">Action Breakdown</div>
                <div className="grid grid-cols-3 gap-2">
                  {Object.entries(cvState.stats.actions).map(([action, count]) => (
                    <div key={action} className="bg-black/20 rounded p-2 text-xs">
                      <div className="font-medium">{action.replace('_', ' ')}</div>
                      <div className="text-gray-400">{count} detections</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default RealtimeCVPanel;
