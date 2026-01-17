import { useState, useEffect, useCallback } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Monitor, Wifi, WifiOff, Users, RefreshCw, ChevronRight, Zap, Trophy, Flag, CheckCircle } from 'lucide-react';
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
  const [showRoundResult, setShowRoundResult] = useState(false);
  const [lastComputedRound, setLastComputedRound] = useState(null);

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

  // End Round - Compute score from all combined events
  const handleEndRound = async () => {
    if (!boutId || !currentRound) return;
    
    setIsLoading(true);
    try {
      // First refresh to get latest events from all devices
      const roundRes = await fetch(`${API}/api/sync/round-status/${boutId}/${currentRound}`);
      if (roundRes.ok) {
        const roundData = await roundRes.json();
        setRoundStatus(roundData);
        console.log('[CombinedSync] Pre-compute events:', roundData.total_events, 'from devices');
      }
      
      // Compute the round score from ALL combined events
      const response = await fetch(`${API}/api/sync/compute-round?bout_id=${boutId}&round_num=${currentRound}`, {
        method: 'POST'
      });

      if (response.ok) {
        const data = await response.json();
        console.log('[CombinedSync] Computed score:', data);
        setLastComputedRound(data);
        setShowRoundResult(true);
        toast.success(`Round ${currentRound}: ${data.card} (${data.total_events} events from ${data.devices?.length || 0} devices)`);
        
        // Refresh status to get updated scores
        const statusRes = await fetch(`${API}/api/sync/status/${boutId}`);
        if (statusRes.ok) {
          const statusData = await statusRes.json();
          setSyncStatus(statusData);
        }
        
        // Also refresh round status
        const roundRes2 = await fetch(`${API}/api/sync/round-status/${boutId}/${currentRound}`);
        if (roundRes2.ok) {
          const roundData2 = await roundRes2.json();
          setRoundStatus(roundData2);
        }
        
        if (onRoundComputed) {
          onRoundComputed(data);
        }
      } else {
        const errData = await response.json();
        console.error('[CombinedSync] Compute failed:', errData);
        toast.error(`Failed to compute: ${errData.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('[CombinedSync] End round error:', error);
      toast.error('Failed to compute round score');
    } finally {
      setIsLoading(false);
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
          setLastComputedRound(data.score);
          setShowRoundResult(true);
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
    <>
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
              Round {currentRound} - Combined Events (All Laptops)
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
                      <span className="text-red-400 font-bold">{count}</span>
                    </div>
                  ))}
                  {Object.keys(roundStatus.fighter1_types || {}).length === 0 && (
                    <div className="text-gray-500 italic">No events logged</div>
                  )}
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
                      <span className="text-blue-400 font-bold">{count}</span>
                    </div>
                  ))}
                  {Object.keys(roundStatus.fighter2_types || {}).length === 0 && (
                    <div className="text-gray-500 italic">No events logged</div>
                  )}
                </div>
              </div>
            </div>

            <div className="text-center text-xs text-gray-500">
              Total: {roundStatus.total_events} events from all devices combined
            </div>
          </div>
        )}

        {/* Device Status */}
        {roundStatus?.devices && (
          <div className="space-y-2">
            <div className="text-xs text-gray-400 uppercase tracking-wider">
              Connected Devices ({roundStatus.devices_total})
            </div>
            <div className="flex flex-wrap gap-2">
              {roundStatus.devices.map((device) => (
                <Badge 
                  key={device.device_id}
                  variant="outline"
                  className={device.ready ? 'border-green-400 text-green-400' : 'border-gray-600 text-gray-400'}
                >
                  {device.ready ? <CheckCircle className="w-3 h-3 mr-1" /> : <Wifi className="w-3 h-3 mr-1" />}
                  {device.device_name}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Unified Scores - Round by Round */}
        {syncStatus?.unified_scores?.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs text-gray-400 uppercase tracking-wider">
              Round Scores (Combined from All Laptops)
            </div>
            <div className="space-y-1">
              {syncStatus.unified_scores.map((round) => (
                <div key={round.round} className="flex items-center justify-between bg-gray-800/50 rounded px-3 py-2">
                  <span className="text-gray-400 font-medium">Round {round.round}</span>
                  <div className="flex items-center gap-3">
                    <span className="text-red-400 font-mono text-lg font-bold">{round.red_score}</span>
                    <span className="text-gray-500">-</span>
                    <span className="text-blue-400 font-mono text-lg font-bold">{round.blue_score}</span>
                  </div>
                  <span className="text-xs text-gray-500">{round.total_events || 0} events</span>
                </div>
              ))}
            </div>
            
            {/* Totals */}
            <div className="flex items-center justify-between bg-gradient-to-r from-amber-900/30 to-amber-800/20 border border-amber-500/30 rounded px-4 py-3 mt-2">
              <span className="text-amber-400 font-bold flex items-center gap-2">
                <Trophy className="w-4 h-4" />
                TOTAL
              </span>
              <div className="flex items-center gap-3">
                <span className="text-red-400 font-mono text-2xl font-bold">{syncStatus.unified_total_red}</span>
                <span className="text-gray-500 text-xl">-</span>
                <span className="text-blue-400 font-mono text-2xl font-bold">{syncStatus.unified_total_blue}</span>
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="grid grid-cols-2 gap-3">
          {/* End Round Button */}
          <Button
            onClick={handleEndRound}
            disabled={isLoading || (roundStatus?.total_events || 0) === 0}
            className="bg-amber-600 hover:bg-amber-700 text-white"
          >
            {isLoading ? (
              <RefreshCw className="w-4 h-4 animate-spin mr-2" />
            ) : (
              <Flag className="w-4 h-4 mr-2" />
            )}
            End Round {currentRound}
          </Button>

          {/* Next Round Button */}
          <Button
            onClick={handleNextRound}
            disabled={isLoading || isReady}
            className={`${isReady ? 'bg-yellow-600' : 'bg-green-600 hover:bg-green-700'} text-white`}
          >
            {isLoading ? (
              <RefreshCw className="w-4 h-4 animate-spin mr-2" />
            ) : isReady ? (
              <Users className="w-4 h-4 mr-2" />
            ) : (
              <ChevronRight className="w-4 h-4 mr-2" />
            )}
            {isReady 
              ? `Waiting (${(roundStatus?.devices_total || 0) - (roundStatus?.devices_ready || 0)} left)`
              : 'Next Round'
            }
          </Button>
        </div>
      </Card>

      {/* Round Result Dialog */}
      <Dialog open={showRoundResult} onOpenChange={setShowRoundResult}>
        <DialogContent className="bg-gray-900 border-gray-700 text-white max-w-md">
          <DialogHeader>
            <DialogTitle className="text-center text-xl flex items-center justify-center gap-2">
              <Trophy className="w-6 h-6 text-amber-400" />
              Round {lastComputedRound?.round_num || currentRound} Complete
            </DialogTitle>
          </DialogHeader>
          
          {lastComputedRound && (
            <div className="space-y-4 py-4">
              {/* Round Score */}
              <div className="text-center">
                <div className="text-6xl font-bold mb-2">
                  <span className="text-red-400">{lastComputedRound.red_score}</span>
                  <span className="text-gray-500 mx-2">-</span>
                  <span className="text-blue-400">{lastComputedRound.blue_score}</span>
                </div>
                <div className="text-gray-400">
                  Score Differential: {lastComputedRound.score_diff > 0 ? '+' : ''}{lastComputedRound.score_diff?.toFixed(1)}
                </div>
              </div>

              {/* Event Summary */}
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div className="bg-red-500/10 border border-red-500/30 rounded p-3">
                  <div className="text-red-400 font-medium mb-2">Red Corner</div>
                  <div className="text-gray-300">
                    {Object.entries(lastComputedRound.f1_counts || {}).map(([type, count]) => (
                      <div key={type} className="flex justify-between">
                        <span>{type}</span>
                        <span className="text-red-400">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="bg-blue-500/10 border border-blue-500/30 rounded p-3">
                  <div className="text-blue-400 font-medium mb-2">Blue Corner</div>
                  <div className="text-gray-300">
                    {Object.entries(lastComputedRound.f2_counts || {}).map(([type, count]) => (
                      <div key={type} className="flex justify-between">
                        <span>{type}</span>
                        <span className="text-blue-400">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Total Events */}
              <div className="text-center text-sm text-gray-400">
                {lastComputedRound.total_events} total events from {lastComputedRound.devices?.length || 0} devices
              </div>

              {/* All Round Scores */}
              {syncStatus?.unified_scores?.length > 0 && (
                <div className="border-t border-gray-700 pt-4">
                  <div className="text-xs text-gray-400 uppercase tracking-wider mb-2 text-center">
                    All Rounds
                  </div>
                  {syncStatus.unified_scores.map((round) => (
                    <div key={round.round} className="flex items-center justify-between py-1">
                      <span className="text-gray-400">Round {round.round}</span>
                      <div>
                        <span className="text-red-400 font-bold">{round.red_score}</span>
                        <span className="text-gray-500 mx-1">-</span>
                        <span className="text-blue-400 font-bold">{round.blue_score}</span>
                      </div>
                    </div>
                  ))}
                  <div className="flex items-center justify-between py-2 border-t border-gray-700 mt-2">
                    <span className="text-amber-400 font-bold">TOTAL</span>
                    <div>
                      <span className="text-red-400 font-bold text-lg">{syncStatus.unified_total_red}</span>
                      <span className="text-gray-500 mx-1">-</span>
                      <span className="text-blue-400 font-bold text-lg">{syncStatus.unified_total_blue}</span>
                    </div>
                  </div>
                </div>
              )}

              <Button 
                onClick={() => setShowRoundResult(false)} 
                className="w-full bg-gray-700 hover:bg-gray-600"
              >
                Continue
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
