import React, { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import axios from 'axios';
import { Activity, TrendingUp, AlertCircle, CheckCircle, Database, Wifi, Clock, Zap } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL || import.meta.env.VITE_REACT_APP_BACKEND_URL;

export default function ICVSSMonitor() {
  const [stats, setStats] = useState(null);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchStats = async () => {
    try {
      const [statsRes, healthRes] = await Promise.all([
        axios.get(`${API}/api/icvss/stats`),
        axios.get(`${API}/api/icvss/health`)
      ]);
      
      setStats(statsRes.data);
      setHealth(healthRes.data);
      setLoading(false);
    } catch (error) {
      console.error('[Monitor] Error fetching stats:', error);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
    
    let interval;
    if (autoRefresh) {
      interval = setInterval(fetchStats, 5000); // Refresh every 5 seconds
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [autoRefresh]);

  if (loading) {
    return (
      <Card className="bg-gradient-to-br from-gray-900 to-gray-950 border-gray-800 p-6">
        <div className="text-center text-gray-400">Loading system monitor...</div>
      </Card>
    );
  }

  const isHealthy = health?.status === 'healthy';
  const totalConnections = stats?.websocket_connections?.total_cv_feed +
    stats?.websocket_connections?.total_judge_feed +
    stats?.websocket_connections?.total_score_feed +
    stats?.websocket_connections?.total_broadcast_feed || 0;

  return (
    <Card className="bg-gradient-to-br from-gray-900 to-gray-950 border-gray-800 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Activity className="w-6 h-6 text-blue-400" />
          <h2 className="text-2xl font-bold text-white">ICVSS System Monitor</h2>
          {isHealthy ? (
            <CheckCircle className="w-5 h-5 text-green-500" />
          ) : (
            <AlertCircle className="w-5 h-5 text-red-500 animate-pulse" />
          )}
        </div>
        
        <div className="flex items-center gap-3">
          <Button
            onClick={fetchStats}
            className="bg-blue-600 hover:bg-blue-700"
            size="sm"
          >
            Refresh
          </Button>
          
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-400">Auto-refresh</span>
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="w-4 h-4"
            />
          </div>
        </div>
      </div>

      {/* Status Overview */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {/* Health Status */}
        <div className={`rounded-lg p-4 border-2 ${isHealthy ? 'bg-green-900/20 border-green-600/30' : 'bg-red-900/20 border-red-600/30'}`}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-400">Health</span>
            {isHealthy ? (
              <CheckCircle className="w-4 h-4 text-green-500" />
            ) : (
              <AlertCircle className="w-4 h-4 text-red-500" />
            )}
          </div>
          <div className={`text-2xl font-bold ${isHealthy ? 'text-green-400' : 'text-red-400'}`}>
            {health?.status?.toUpperCase() || 'UNKNOWN'}
          </div>
        </div>

        {/* Active Rounds */}
        <div className="bg-blue-900/20 border-2 border-blue-600/30 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-400">Active Rounds</span>
            <Activity className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-bold text-blue-400">
            {stats?.active_rounds || 0}
          </div>
        </div>

        {/* Events Processed */}
        <div className="bg-purple-900/20 border-2 border-purple-600/30 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-400">Events Processed</span>
            <Zap className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-bold text-purple-400">
            {stats?.event_processor?.total_processed || 0}
          </div>
        </div>

        {/* WebSocket Connections */}
        <div className="bg-amber-900/20 border-2 border-amber-600/30 rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-400">WS Connections</span>
            <Wifi className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold text-amber-400">
            {totalConnections}
          </div>
        </div>
      </div>

      {/* Event Processor Stats */}
      <div className="grid grid-cols-2 gap-6 mb-6">
        <div className="bg-black/30 rounded-lg p-4 border border-gray-800">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Database className="w-5 h-5 text-blue-400" />
            Event Processor
          </h3>
          
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-400">Total Processed:</span>
              <span className="text-white font-semibold">{stats?.event_processor?.total_processed || 0}</span>
            </div>
            
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-400">Dedup Window:</span>
              <Badge className="bg-blue-600/20 text-blue-400 border-blue-600/30">
                {stats?.event_processor?.dedup_window_ms || 100}ms
              </Badge>
            </div>
            
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-400">Confidence Threshold:</span>
              <Badge className="bg-green-600/20 text-green-400 border-green-600/30">
                {((stats?.event_processor?.confidence_threshold || 0.6) * 100).toFixed(0)}%
              </Badge>
            </div>
          </div>
        </div>

        {/* WebSocket Connections Breakdown */}
        <div className="bg-black/30 rounded-lg p-4 border border-gray-800">
          <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
            <Wifi className="w-5 h-5 text-amber-400" />
            WebSocket Feeds
          </h3>
          
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-400">CV Feed:</span>
              <Badge className="bg-purple-600/20 text-purple-400 border-purple-600/30">
                {stats?.websocket_connections?.total_cv_feed || 0} connections
              </Badge>
            </div>
            
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-400">Judge Feed:</span>
              <Badge className="bg-blue-600/20 text-blue-400 border-blue-600/30">
                {stats?.websocket_connections?.total_judge_feed || 0} connections
              </Badge>
            </div>
            
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-400">Score Feed:</span>
              <Badge className="bg-green-600/20 text-green-400 border-green-600/30">
                {stats?.websocket_connections?.total_score_feed || 0} connections
              </Badge>
            </div>
            
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-400">Broadcast Feed:</span>
              <Badge className="bg-amber-600/20 text-amber-400 border-amber-600/30">
                {stats?.websocket_connections?.total_broadcast_feed || 0} connections
              </Badge>
            </div>
          </div>
        </div>
      </div>

      {/* System Info */}
      <div className="bg-black/30 rounded-lg p-4 border border-gray-800">
        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Clock className="w-5 h-5 text-gray-400" />
          System Information
        </h3>
        
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <div className="text-gray-400 mb-1">Service</div>
            <div className="text-white font-semibold">{health?.service || 'ICVSS'}</div>
          </div>
          
          <div>
            <div className="text-gray-400 mb-1">Version</div>
            <div className="text-white font-semibold">{health?.version || '1.0.0'}</div>
          </div>
          
          <div>
            <div className="text-gray-400 mb-1">Last Updated</div>
            <div className="text-white font-semibold">
              {stats?.timestamp ? new Date(stats.timestamp).toLocaleTimeString() : 'N/A'}
            </div>
          </div>
        </div>
      </div>

      {/* Performance Indicators */}
      <div className="mt-4 grid grid-cols-3 gap-3">
        <div className={`p-3 rounded-lg text-center ${
          (stats?.event_processor?.total_processed || 0) > 0 ? 'bg-green-900/20 border border-green-600/30' : 'bg-gray-900/20 border border-gray-600/30'
        }`}>
          <div className="text-xs text-gray-400 mb-1">Event Processing</div>
          <div className={`text-sm font-semibold ${
            (stats?.event_processor?.total_processed || 0) > 0 ? 'text-green-400' : 'text-gray-400'
          }`}>
            {(stats?.event_processor?.total_processed || 0) > 0 ? 'Active' : 'Idle'}
          </div>
        </div>
        
        <div className={`p-3 rounded-lg text-center ${
          totalConnections > 0 ? 'bg-green-900/20 border border-green-600/30' : 'bg-gray-900/20 border border-gray-600/30'
        }`}>
          <div className="text-xs text-gray-400 mb-1">WebSocket Status</div>
          <div className={`text-sm font-semibold ${
            totalConnections > 0 ? 'text-green-400' : 'text-gray-400'
          }`}>
            {totalConnections > 0 ? 'Connected' : 'No Connections'}
          </div>
        </div>
        
        <div className={`p-3 rounded-lg text-center ${
          isHealthy ? 'bg-green-900/20 border border-green-600/30' : 'bg-red-900/20 border border-red-600/30'
        }`}>
          <div className="text-xs text-gray-400 mb-1">Overall Status</div>
          <div className={`text-sm font-semibold ${
            isHealthy ? 'text-green-400' : 'text-red-400'
          }`}>
            {isHealthy ? 'Operational' : 'Degraded'}
          </div>
        </div>
      </div>
    </Card>
  );
}
