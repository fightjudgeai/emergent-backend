import React, { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import axios from 'axios';
import { 
  Activity, 
  Cpu, 
  Wifi, 
  AlertTriangle, 
  CheckCircle, 
  Clock, 
  Zap,
  RefreshCw,
  TrendingUp,
  Database
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL || import.meta.env.VITE_REACT_APP_BACKEND_URL;

export default function ICVSSMonitoringDashboard() {
  const [systemStatus, setSystemStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastUpdate, setLastUpdate] = useState(null);

  // Fetch system status
  const fetchSystemStatus = async () => {
    try {
      const response = await axios.get(`${API}/api/icvss/system/status`);
      setSystemStatus(response.data);
      setLastUpdate(new Date());
      setLoading(false);
    } catch (error) {
      console.error('[ICVSS] Error fetching system status:', error);
      setSystemStatus({
        status: "error",
        error: error.message
      });
      setLoading(false);
    }
  };

  // Auto-refresh every 5 seconds
  useEffect(() => {
    fetchSystemStatus();
    
    if (autoRefresh) {
      const interval = setInterval(fetchSystemStatus, 5000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  // Get status color
  const getStatusColor = (status) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-500';
      case 'degraded':
        return 'bg-yellow-500';
      case 'slow':
        return 'bg-orange-500';
      case 'error':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  // Get status icon
  const getStatusIcon = (status) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle className="w-6 h-6 text-green-500" />;
      case 'degraded':
      case 'slow':
        return <AlertTriangle className="w-6 h-6 text-yellow-500" />;
      case 'error':
        return <AlertTriangle className="w-6 h-6 text-red-500" />;
      default:
        return <Activity className="w-6 h-6 text-gray-500" />;
    }
  };

  if (loading) {
    return (
      <Card className="bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700 p-8">
        <div className="flex items-center justify-center">
          <RefreshCw className="w-8 h-8 text-purple-400 animate-spin" />
          <span className="ml-3 text-gray-300">Loading system status...</span>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card className="bg-gradient-to-br from-purple-950/30 to-blue-950/30 border-purple-600/30 p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Activity className="w-8 h-8 text-purple-400" />
            <div>
              <h2 className="text-3xl font-bold text-purple-400">ICVSS System Monitor</h2>
              <p className="text-sm text-gray-400 mt-1">Real-time system health and performance metrics</p>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            {/* Auto-refresh toggle */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-400">Auto-refresh</span>
              <button
                onClick={() => setAutoRefresh(!autoRefresh)}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  autoRefresh ? 'bg-purple-600' : 'bg-gray-600'
                }`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    autoRefresh ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
            
            {/* Manual refresh button */}
            <Button
              onClick={fetchSystemStatus}
              className="bg-purple-600 hover:bg-purple-700"
              size="sm"
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
          </div>
        </div>
        
        {lastUpdate && (
          <div className="mt-4 text-xs text-gray-500">
            Last updated: {lastUpdate.toLocaleTimeString()}
          </div>
        )}
      </Card>

      {/* Overall System Status */}
      <Card className="bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700 p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            {getStatusIcon(systemStatus?.status)}
            <div>
              <h3 className="text-2xl font-bold text-white">System Status</h3>
              <p className="text-sm text-gray-400">Overall health: <span className="capitalize font-semibold">{systemStatus?.status || 'unknown'}</span></p>
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <div className={`w-4 h-4 rounded-full ${getStatusColor(systemStatus?.status)} animate-pulse`} />
            <Badge className={`${getStatusColor(systemStatus?.status)} text-white text-lg px-4 py-1`}>
              {systemStatus?.status?.toUpperCase() || 'UNKNOWN'}
            </Badge>
          </div>
        </div>
      </Card>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Active Rounds */}
        <Card className="bg-gradient-to-br from-blue-950/50 to-blue-900/50 border-blue-600/30 p-6">
          <div className="flex items-center justify-between mb-3">
            <Database className="w-8 h-8 text-blue-400" />
            <div className="text-4xl font-black text-white">{systemStatus?.active_rounds || 0}</div>
          </div>
          <h4 className="text-sm text-blue-300 font-semibold">Active Rounds</h4>
          <p className="text-xs text-gray-400 mt-1">Currently open rounds</p>
        </Card>

        {/* Events Processed */}
        <Card className="bg-gradient-to-br from-purple-950/50 to-purple-900/50 border-purple-600/30 p-6">
          <div className="flex items-center justify-between mb-3">
            <Zap className="w-8 h-8 text-purple-400" />
            <div className="text-4xl font-black text-white">
              {systemStatus?.event_processing?.total_events_processed || 0}
            </div>
          </div>
          <h4 className="text-sm text-purple-300 font-semibold">Events Processed</h4>
          <p className="text-xs text-gray-400 mt-1">Total events handled</p>
        </Card>

        {/* Processing Latency */}
        <Card className="bg-gradient-to-br from-green-950/50 to-green-900/50 border-green-600/30 p-6">
          <div className="flex items-center justify-between mb-3">
            <Clock className="w-8 h-8 text-green-400" />
            <div className="text-4xl font-black text-white">
              {systemStatus?.event_processing?.processing_latency_ms || 0}
              <span className="text-xl ml-1">ms</span>
            </div>
          </div>
          <h4 className="text-sm text-green-300 font-semibold">Latency</h4>
          <p className="text-xs text-gray-400 mt-1">Avg processing time</p>
        </Card>

        {/* Active Connections */}
        <Card className="bg-gradient-to-br from-amber-950/50 to-amber-900/50 border-amber-600/30 p-6">
          <div className="flex items-center justify-between mb-3">
            <Wifi className="w-8 h-8 text-amber-400" />
            <div className="text-4xl font-black text-white">
              {systemStatus?.websocket?.active_connections || 0}
            </div>
          </div>
          <h4 className="text-sm text-amber-300 font-semibold">WS Connections</h4>
          <p className="text-xs text-gray-400 mt-1">Active WebSocket clients</p>
        </Card>
      </div>

      {/* Event Processing Details */}
      <Card className="bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700 p-6">
        <div className="flex items-center gap-3 mb-4">
          <TrendingUp className="w-6 h-6 text-purple-400" />
          <h3 className="text-xl font-bold text-white">Event Processing</h3>
        </div>
        
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-black/30 rounded-lg p-4">
            <div className="text-sm text-gray-400 mb-1">Recent (5min)</div>
            <div className="text-2xl text-white font-bold">
              {systemStatus?.event_processing?.events_last_5min || 0}
            </div>
          </div>
          
          <div className="bg-black/30 rounded-lg p-4">
            <div className="text-sm text-gray-400 mb-1">Error Rate</div>
            <div className="text-2xl text-white font-bold">
              {((systemStatus?.event_processing?.error_rate || 0) * 100).toFixed(2)}%
            </div>
          </div>
          
          <div className="bg-black/30 rounded-lg p-4">
            <div className="text-sm text-gray-400 mb-1">Dedup Rate</div>
            <div className="text-2xl text-white font-bold">
              {((systemStatus?.event_processing?.deduplication_rate || 0) * 100).toFixed(2)}%
            </div>
          </div>
          
          <div className="bg-black/30 rounded-lg p-4">
            <div className="text-sm text-gray-400 mb-1">Latency</div>
            <div className="text-2xl text-white font-bold">
              {systemStatus?.event_processing?.processing_latency_ms || 0}ms
            </div>
          </div>
        </div>
      </Card>

      {/* WebSocket Details */}
      <Card className="bg-gradient-to-br from-slate-900 to-slate-800 border-slate-700 p-6">
        <div className="flex items-center gap-3 mb-4">
          <Wifi className="w-6 h-6 text-blue-400" />
          <h3 className="text-xl font-bold text-white">WebSocket Connections</h3>
        </div>
        
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div className="bg-black/30 rounded-lg p-4">
            <div className="text-sm text-gray-400 mb-1">Active Connections</div>
            <div className="text-2xl text-white font-bold">
              {systemStatus?.websocket?.active_connections || 0}
            </div>
          </div>
          
          <div className="bg-black/30 rounded-lg p-4">
            <div className="text-sm text-gray-400 mb-1">Messages Sent</div>
            <div className="text-2xl text-white font-bold">
              {systemStatus?.websocket?.total_messages_sent || 0}
            </div>
          </div>
          
          <div className="bg-black/30 rounded-lg p-4">
            <div className="text-sm text-gray-400 mb-1">Connection Errors</div>
            <div className="text-2xl text-white font-bold">
              {systemStatus?.websocket?.connection_errors || 0}
            </div>
          </div>
        </div>
      </Card>

      {/* Fusion Engine Info */}
      <Card className="bg-gradient-to-br from-purple-950/30 to-blue-950/30 border-purple-600/30 p-6">
        <div className="flex items-center gap-3 mb-4">
          <Cpu className="w-6 h-6 text-purple-400" />
          <h3 className="text-xl font-bold text-white">Hybrid Scoring Engine</h3>
        </div>
        
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-black/30 rounded-lg p-4 text-center">
            <div className="text-sm text-gray-400 mb-1">CV Weight</div>
            <div className="text-3xl text-purple-400 font-bold">
              {((systemStatus?.fusion_engine?.cv_weight || 0.7) * 100).toFixed(0)}%
            </div>
          </div>
          
          <div className="bg-black/30 rounded-lg p-4 text-center">
            <div className="text-sm text-gray-400 mb-1">Judge Weight</div>
            <div className="text-3xl text-blue-400 font-bold">
              {((systemStatus?.fusion_engine?.judge_weight || 0.3) * 100).toFixed(0)}%
            </div>
          </div>
          
          <div className="bg-black/30 rounded-lg p-4 text-center">
            <div className="text-sm text-gray-400 mb-1">Status</div>
            <div className="flex items-center justify-center mt-2">
              {systemStatus?.fusion_engine?.active ? (
                <Badge className="bg-green-600 text-white">ACTIVE</Badge>
              ) : (
                <Badge className="bg-gray-600 text-white">INACTIVE</Badge>
              )}
            </div>
          </div>
        </div>
      </Card>

      {/* Error Display */}
      {systemStatus?.status === 'error' && systemStatus?.error && (
        <Card className="bg-gradient-to-br from-red-950/50 to-red-900/50 border-red-600/50 p-6">
          <div className="flex items-center gap-3 mb-3">
            <AlertTriangle className="w-6 h-6 text-red-400" />
            <h3 className="text-xl font-bold text-red-400">System Error</h3>
          </div>
          <p className="text-sm text-red-200">{systemStatus.error}</p>
        </Card>
      )}
    </div>
  );
}
