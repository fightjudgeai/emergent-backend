import { memo, useState, useEffect, useCallback } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Users, RefreshCw, Wifi, Monitor, Activity, Zap } from "lucide-react";

const API_BASE = process.env.REACT_APP_BACKEND_URL || '';

/**
 * Multi-Device Event Scoreboard
 * Shows combined events from ALL devices (4 laptops) as ONE unified score
 */
export const MultiJudgeScoreboard = memo(function MultiJudgeScoreboard({ boutId, refreshInterval = 2000 }) {
  const [syncStatus, setSyncStatus] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);

  const fetchSyncStatus = useCallback(async () => {
    if (!boutId) return;
    
    try {
      const response = await fetch(`${API_BASE}/api/sync/status/${boutId}`);
      if (response.ok) {
        const data = await response.json();
        setSyncStatus(data);
        setLastUpdate(new Date());
      }
    } catch (error) {
      console.error('[MultiDevice] Fetch error:', error);
    }
  }, [boutId]);

  // Compute round score from all events
  const computeRound = useCallback(async (roundNum) => {
    if (!boutId) return;
    setIsLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/sync/compute-round?bout_id=${boutId}&round_num=${roundNum}`, {
        method: 'POST'
      });
      if (response.ok) {
        await fetchSyncStatus(); // Refresh after computing
      }
    } catch (error) {
      console.error('[MultiDevice] Compute error:', error);
    } finally {
      setIsLoading(false);
    }
  }, [boutId, fetchSyncStatus]);

  // Auto-refresh
  useEffect(() => {
    if (!boutId) return;
    fetchSyncStatus();
    const interval = setInterval(fetchSyncStatus, refreshInterval);
    return () => clearInterval(interval);
  }, [boutId, refreshInterval, fetchSyncStatus]);

  if (!syncStatus) {
    return (
      <div className="p-4 text-center text-gray-400">
        <Monitor className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p>Waiting for sync data...</p>
      </div>
    );
  }

  const { devices, unified_scores, unified_total_red, unified_total_blue, fighter1, fighter2, active_devices, total_events, events_by_round } = syncStatus;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Monitor className="w-5 h-5 text-lb-gold" />
          <span className="text-lg font-semibold text-white">
            Combined Scoring
          </span>
          <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded-full">
            {active_devices || 0} Devices
          </span>
        </div>
        <Button
          size="sm"
          variant="ghost"
          onClick={fetchSyncStatus}
          disabled={isLoading}
          className="h-8"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
        </Button>
      </div>

      {/* Unified Totals */}
      <Card className="bg-gray-900/80 border-lb-gold/30 p-4">
        <div className="text-center mb-2">
          <span className="text-xs text-gray-400 uppercase tracking-wider">Combined Score (All Devices)</span>
        </div>
        <div className="grid grid-cols-3 gap-4 items-center">
          <div className="text-center">
            <div className="text-sm text-red-400 mb-1">{fighter1}</div>
            <div className="text-4xl font-bold text-red-500">{unified_total_red || 0}</div>
          </div>
          <div className="text-center">
            <div className="text-2xl text-gray-500">VS</div>
          </div>
          <div className="text-center">
            <div className="text-sm text-blue-400 mb-1">{fighter2}</div>
            <div className="text-4xl font-bold text-blue-500">{unified_total_blue || 0}</div>
          </div>
        </div>
      </Card>

      {/* Round-by-Round Scores */}
      {unified_scores && unified_scores.length > 0 && (
        <Card className="bg-gray-900/60 border-gray-700 p-4">
          <div className="text-xs text-gray-400 uppercase tracking-wider mb-3">Round Scores</div>
          <div className="space-y-2">
            {unified_scores.map((round) => (
              <div key={round.round} className="flex items-center justify-between bg-gray-800/50 rounded px-3 py-2">
                <span className="text-gray-400">RD {round.round}</span>
                <div className="flex items-center gap-4">
                  <span className="text-red-400 font-mono text-lg">{round.red_score || round.unified_red}</span>
                  <span className="text-gray-500">-</span>
                  <span className="text-blue-400 font-mono text-lg">{round.blue_score || round.unified_blue}</span>
                </div>
                <div className="flex items-center gap-2">
                  {round.total_events && (
                    <span className="text-xs text-gray-500">{round.total_events} events</span>
                  )}
                  {round.num_devices && (
                    <span className="text-xs text-green-400">({round.num_devices} devices)</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Events Per Round */}
      {events_by_round && Object.keys(events_by_round).length > 0 && (
        <Card className="bg-gray-900/60 border-gray-700 p-4">
          <div className="text-xs text-gray-400 uppercase tracking-wider mb-3">Events Logged (All Devices)</div>
          <div className="space-y-2">
            {Object.entries(events_by_round).map(([roundNum, stats]) => (
              <div key={roundNum} className="flex items-center justify-between bg-gray-800/50 rounded px-3 py-2">
                <span className="text-gray-400">Round {roundNum}</span>
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-1">
                    <Zap className="w-3 h-3 text-red-400" />
                    <span className="text-red-400 font-mono">{stats.fighter1_events}</span>
                  </div>
                  <span className="text-gray-600">|</span>
                  <div className="flex items-center gap-1">
                    <Zap className="w-3 h-3 text-blue-400" />
                    <span className="text-blue-400 font-mono">{stats.fighter2_events}</span>
                  </div>
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => computeRound(parseInt(roundNum))}
                  className="h-6 px-2 text-xs"
                  disabled={isLoading}
                >
                  Compute
                </Button>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Connected Devices */}
      {devices && devices.length > 0 && (
        <Card className="bg-gray-900/60 border-gray-700 p-4">
          <div className="text-xs text-gray-400 uppercase tracking-wider mb-3">
            Connected Devices ({devices.length})
          </div>
          <div className="space-y-2">
            {devices.map((device) => (
              <div key={device.device_id} className="flex items-center justify-between bg-gray-800/50 rounded px-3 py-2">
                <div className="flex items-center gap-2">
                  <Wifi className="w-3 h-3 text-green-400" />
                  <span className="text-white text-sm">{device.device_name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Activity className="w-3 h-3 text-lb-gold" />
                  <span className="text-xs text-gray-400">{device.event_count} events</span>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Total Events */}
      <div className="text-center text-xs text-gray-500">
        Total: {total_events || 0} events from {active_devices || 0} devices
      </div>
    </div>
  );
});

/**
 * Compact Device Status Indicator
 */
export const JudgeStatusIndicator = memo(function JudgeStatusIndicator({ boutId, refreshInterval = 5000 }) {
  const [status, setStatus] = useState({ devices: [], total_events: 0 });

  useEffect(() => {
    if (!boutId) return;

    const fetchStatus = async () => {
      try {
        const response = await fetch(`${API_BASE}/api/sync/status/${boutId}`);
        if (response.ok) {
          const data = await response.json();
          setStatus({
            devices: data.devices || [],
            total_events: data.total_events || 0
          });
        }
      } catch (error) {
        console.error('[DeviceStatus] Error:', error);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, refreshInterval);
    return () => clearInterval(interval);
  }, [boutId, refreshInterval]);

  return (
    <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-900/80 border border-gray-700 rounded-lg">
      <Monitor className="w-4 h-4 text-lb-gold" />
      <span className="text-xs text-gray-400">Devices:</span>
      <div className="flex gap-1">
        {status.devices.length === 0 ? (
          <span className="text-xs text-gray-500">None connected</span>
        ) : (
          status.devices.slice(0, 4).map((device) => (
            <div
              key={device.device_id}
              className="flex items-center gap-1 px-2 py-0.5 bg-green-500/20 text-green-400 rounded text-xs"
              title={`${device.device_name}: ${device.event_count} events`}
            >
              <Wifi className="w-3 h-3" />
              {device.device_name.split(' ')[0]}
            </div>
          ))
        )}
      </div>
      {status.total_events > 0 && (
        <span className="text-xs text-lb-gold ml-1">({status.total_events} events)</span>
      )}
    </div>
  );
});

export default MultiJudgeScoreboard;
