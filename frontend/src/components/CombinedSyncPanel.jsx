import { useState, useEffect, useCallback } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Monitor, Wifi, WifiOff, Users, RefreshCw, ChevronRight, Zap, Trophy } from 'lucide-react';
import { toast } from 'sonner';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * CombinedSyncPanel - Shows combined events from all 4 laptops
 * Each laptop scores different aspects, all combine into ONE unified score
 */
export default function CombinedSyncPanel({ boutId, currentRound, onRoundComputed }) {
  const [syncStatus, setSyncStatus] = useState(null);
  const [roundStatus, setRoundStatus] = useState(null);
  const [deviceId, setDeviceId] = useState(null);
  const [isRegistered, setIsRegistered] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Generate or get device ID
  useEffect(() => {
    let storedDeviceId = localStorage.getItem('sync_device_id');
    if (!storedDeviceId) {
      storedDeviceId = `device-${Date.now()}-${Math.random().toString(36).substr(2, 6)}`;
      localStorage.setItem('sync_device_id', storedDeviceId);
    }
    setDeviceId(storedDeviceId);
  }, []);

  // Register device when component mounts
  useEffect(() => {
    if (boutId && deviceId) {
      registerDevice();
    }
  }, [boutId, deviceId]);

  // Poll for sync status
  useEffect(() => {
    if (!boutId || !isRegistered) return;

    const fetchStatus = async () => {
      try {
        // Get overall sync status
        const statusRes = await fetch(`${API}/api/sync/status/${boutId}`);
        if (statusRes.ok) {
          const data = await statusRes.json();
          setSyncStatus(data);
        }

        // Get current round status
        if (currentRound) {
          const roundRes = await fetch(`${API}/api/sync/round-status/${boutId}/${currentRound}`);
          if (roundRes.ok) {
            const data = await roundRes.json();
            setRoundStatus(data);
          }
        }
      } catch (error) {
        console.error('[CombinedSync] Fetch error:', error);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 2000);
    return () => clearInterval(interval);
  }, [boutId, currentRound, isRegistered]);

  const registerDevice = async () => {
    try {
      const profile = JSON.parse(localStorage.getItem('judgeProfile') || '{}');
      const deviceName = localStorage.getItem('sync_device_name') || `Laptop ${deviceId.slice(-4)}`;
      
      const response = await fetch(`${API}/api/sync/register-device`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bout_id: boutId,
          device_id: deviceId,
          account_id: profile.judgeId || 'default',
          device_name: deviceName
        })
      });

      if (response.ok) {
        setIsRegistered(true);
        toast.success('Device synced for combined scoring');
      }
    } catch (error) {
      console.error('[CombinedSync] Register error:', error);
    }
  };

  const handleNextRound = async () => {
    if (!boutId || !deviceId || !currentRound) return;
    
    setIsLoading(true);
    try {
      const profile = JSON.parse(localStorage.getItem('judgeProfile') || '{}');
      
      const response = await fetch(`${API}/api/sync/next-round`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bout_id: boutId,
          device_id: deviceId,
          account_id: profile.judgeId || 'default',
          current_round: currentRound
        })
      });

      if (response.ok) {
        const data = await response.json();
        setIsReady(true);
        
        if (data.all_ready && data.round_computed) {
          toast.success(`Round ${currentRound} computed: ${data.score?.card}`);
          if (onRoundComputed) {
            onRoundComputed(data.score);
          }
          setIsReady(false);
        } else {
          toast.info(`Waiting for ${data.waiting_for?.length || 0} more device(s)...`);
        }
      }
    } catch (error) {
      console.error('[CombinedSync] Next round error:', error);
      toast.error('Failed to signal next round');
    } finally {
      setIsLoading(false);
    }
  };

  const setDeviceName = (name) => {
    localStorage.setItem('sync_device_name', name);
    registerDevice();
  };

  if (!isRegistered) {
    return (
      <Card className="p-4 bg-gray-900 border-gray-700">
        <div className="flex items-center gap-2 text-gray-400">
          <WifiOff className="w-4 h-4" />
          <span>Connecting to sync...</span>
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-4 bg-gray-900 border-gray-700 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Monitor className="w-5 h-5 text-green-400" />
          <span className="font-semibold text-white">Combined Scoring</span>
          <Badge variant="outline" className="text-green-400 border-green-400">
            {syncStatus?.connected_devices || 0} Devices
          </Badge>
        </div>
        <Button size="sm" variant="ghost" onClick={registerDevice}>
          <RefreshCw className="w-4 h-4" />
        </Button>
      </div>

      {/* Current Round Events (Combined from ALL devices) */}
      {roundStatus && (
        <div className="space-y-2">
          <div className="text-xs text-gray-400 uppercase tracking-wider">
            Round {currentRound} - Combined Events
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            {/* Fighter 1 Events */}
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
              <div className="text-red-400 font-medium mb-2 flex items-center gap-2">
                <Zap className="w-4 h-4" />
                {roundStatus.fighter1} 
                <Badge className="bg-red-500/20 text-red-400 text-xs">
                  {roundStatus.fighter1_events} events
                </Badge>
              </div>
              <div className="space-y-1 text-xs">
                {Object.entries(roundStatus.fighter1_types || {}).map(([type, count]) => (
                  <div key={type} className="flex justify-between text-gray-300">
                    <span>{type}</span>
                    <span className="text-red-400">{count}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Fighter 2 Events */}
            <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3">
              <div className="text-blue-400 font-medium mb-2 flex items-center gap-2">
                <Zap className="w-4 h-4" />
                {roundStatus.fighter2}
                <Badge className="bg-blue-500/20 text-blue-400 text-xs">
                  {roundStatus.fighter2_events} events
                </Badge>
              </div>
              <div className="space-y-1 text-xs">
                {Object.entries(roundStatus.fighter2_types || {}).map(([type, count]) => (
                  <div key={type} className="flex justify-between text-gray-300">
                    <span>{type}</span>
                    <span className="text-blue-400">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <div className="text-center text-xs text-gray-500">
            Total: {roundStatus.total_events} events from all devices
          </div>
        </div>
      )}

      {/* Device Status */}
      {roundStatus?.devices && (
        <div className="space-y-2">
          <div className="text-xs text-gray-400 uppercase tracking-wider">
            Devices ({roundStatus.devices_ready}/{roundStatus.devices_total} ready)
          </div>
          <div className="flex flex-wrap gap-2">
            {roundStatus.devices.map((device) => (
              <Badge 
                key={device.device_id}
                variant="outline"
                className={device.ready ? 'border-green-400 text-green-400' : 'border-gray-600 text-gray-400'}
              >
                {device.ready ? <Wifi className="w-3 h-3 mr-1" /> : <WifiOff className="w-3 h-3 mr-1" />}
                {device.device_name}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Unified Scores */}
      {syncStatus?.unified_scores?.length > 0 && (
        <div className="space-y-2">
          <div className="text-xs text-gray-400 uppercase tracking-wider">
            Round Scores (Combined)
          </div>
          <div className="space-y-1">
            {syncStatus.unified_scores.map((round) => (
              <div key={round.round} className="flex items-center justify-between bg-gray-800/50 rounded px-3 py-1.5">
                <span className="text-gray-400">Round {round.round}</span>
                <div className="flex items-center gap-2">
                  <span className="text-red-400 font-mono">{round.red_score}</span>
                  <span className="text-gray-500">-</span>
                  <span className="text-blue-400 font-mono">{round.blue_score}</span>
                </div>
              </div>
            ))}
          </div>
          
          {/* Totals */}
          <div className="flex items-center justify-between bg-gray-800 rounded px-3 py-2 mt-2">
            <span className="text-white font-medium">TOTAL</span>
            <div className="flex items-center gap-2">
              <span className="text-red-400 font-bold text-lg">{syncStatus.unified_total_red}</span>
              <span className="text-gray-500">-</span>
              <span className="text-blue-400 font-bold text-lg">{syncStatus.unified_total_blue}</span>
            </div>
          </div>
        </div>
      )}

      {/* Next Round Button */}
      <Button
        onClick={handleNextRound}
        disabled={isLoading || isReady}
        className={`w-full ${isReady ? 'bg-yellow-600' : 'bg-green-600 hover:bg-green-700'}`}
      >
        {isLoading ? (
          <RefreshCw className="w-4 h-4 animate-spin mr-2" />
        ) : isReady ? (
          <Users className="w-4 h-4 mr-2" />
        ) : (
          <ChevronRight className="w-4 h-4 mr-2" />
        )}
        {isReady 
          ? `Waiting for ${(roundStatus?.devices_total || 0) - (roundStatus?.devices_ready || 0)} device(s)...`
          : 'Next Round (Compute Score)'
        }
      </Button>
    </Card>
  );
}
