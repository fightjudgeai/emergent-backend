import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Monitor, Wifi, WifiOff, RefreshCw, Zap, Trophy, Flag, CheckCircle, AlertCircle, Users } from 'lucide-react';
import { toast } from 'sonner';
import useUnifiedScoring from '@/hooks/useUnifiedScoring';

/**
 * UnifiedScoringPanel - Server-Authoritative Scoring Display
 * 
 * CRITICAL: This component NEVER computes scores locally.
 * All scoring comes from the server's unified scoring API via WebSocket.
 * All 4 operator laptops see the SAME data because it comes from ONE source.
 */
export default function CombinedSyncPanel({ boutId, currentRound, onRoundComputed }) {
  const [deviceRole, setDeviceRole] = useState(localStorage.getItem('device_role') || 'RED_STRIKING');
  const [showRoundResult, setShowRoundResult] = useState(false);
  const [lastComputedRound, setLastComputedRound] = useState(null);

  // Use the unified scoring hook for WebSocket connection
  const {
    isConnected,
    connectionCount,
    lastUpdate,
    error,
    boutInfo,
    events,
    roundResults,
    runningTotals,
    isLoading,
    computeRound,
    finalizeFight,
    requestSync
  } = useUnifiedScoring(boutId, currentRound);

  // Save device role
  const handleDeviceRoleChange = (role) => {
    setDeviceRole(role);
    localStorage.setItem('device_role', role);
    toast.success(`Device role set to: ${role}`);
  };

  // END ROUND - Server computes from ALL events
  const handleEndRound = async () => {
    if (!boutId || !currentRound) return;
    
    console.log(`[UNIFIED] Computing round ${currentRound} from ALL events on server...`);
    
    const response = await computeRound(currentRound);
    
    if (response.success) {
      setLastComputedRound(response.result);
      setShowRoundResult(true);
      
      toast.success(
        `Round ${currentRound}: ${response.result.red_points}-${response.result.blue_points} (${response.result.total_events} events from ALL devices)`,
        { duration: 5000 }
      );
      
      if (onRoundComputed) {
        onRoundComputed(response.result);
      }
    } else {
      toast.error(`Failed to compute: ${response.error}`);
    }
  };

  // FINALIZE FIGHT
  const handleFinalizeFight = async () => {
    if (!boutId) return;
    
    const response = await finalizeFight();
    
    if (response.success) {
      toast.success(
        `FIGHT FINALIZED: ${response.result.fighter1_name} ${response.result.final_red} - ${response.result.final_blue} ${response.result.fighter2_name} | Winner: ${response.result.winner_name}`,
        { duration: 10000 }
      );
    } else {
      toast.error(`Failed to finalize: ${response.error}`);
    }
  };

  return (
    <>
      <Card className="p-4 bg-gray-900 border-gray-700 space-y-4">
        {/* Header with Connection Status */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Monitor className="w-5 h-5 text-green-400" />
            <span className="font-semibold text-white">Unified Scoring</span>
            <Badge 
              variant="outline" 
              className={isConnected ? 'text-green-400 border-green-400' : 'text-red-400 border-red-400'}
            >
              {isConnected ? (
                <><Wifi className="w-3 h-3 mr-1" />LIVE</>
              ) : (
                <><WifiOff className="w-3 h-3 mr-1" />OFFLINE</>
              )}
            </Badge>
            {connectionCount > 0 && (
              <Badge className="bg-purple-500/20 text-purple-400 border-purple-500/30">
                <Users className="w-3 h-3 mr-1" />
                {connectionCount} connected
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2">
            <select 
              value={deviceRole}
              onChange={(e) => handleDeviceRoleChange(e.target.value)}
              className="bg-gray-800 border border-gray-600 text-white text-xs rounded px-2 py-1"
              data-testid="device-role-selector"
            >
              <option value="RED_STRIKING">Red Striking</option>
              <option value="RED_GRAPPLING">Red Grappling</option>
              <option value="BLUE_STRIKING">Blue Striking</option>
              <option value="BLUE_GRAPPLING">Blue Grappling</option>
            </select>
            <Button size="sm" variant="ghost" onClick={requestSync} data-testid="refresh-sync-btn">
              <RefreshCw className="w-4 h-4" />
            </Button>
          </div>
        </div>
        
        {/* Info Bar */}
        <div className="text-xs text-gray-400 bg-gray-800/50 rounded p-2 flex justify-between">
          <span>Bout: {boutId}</span>
          <span>Round: {currentRound}</span>
          <span>Your Role: {deviceRole}</span>
          {lastUpdate && (
            <span className="text-green-400">
              Last sync: {new Date(lastUpdate).toLocaleTimeString()}
            </span>
          )}
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded p-2 text-red-400 text-sm flex items-center gap-2">
            <AlertCircle className="w-4 h-4" />
            {error}
          </div>
        )}

        {/* Current Round Events - FROM ALL DEVICES */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-400 uppercase tracking-wider">
              Round {currentRound} - Combined Events (ALL Devices)
            </span>
            <Badge className="bg-amber-500/20 text-amber-400">
              {events.allEvents} total
            </Badge>
          </div>
          
          <div className="grid grid-cols-2 gap-4">
            {/* Red Corner */}
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
              <div className="text-red-400 font-medium mb-2 flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Zap className="w-4 h-4" />
                  {boutInfo.fighter1}
                </span>
                <Badge className="bg-red-500/20 text-red-400 text-xs" data-testid="red-events-count">
                  {events.redTotal}
                </Badge>
              </div>
              <div className="space-y-1 text-xs max-h-32 overflow-y-auto" data-testid="red-events-list">
                {Object.entries(events.red).length === 0 ? (
                  <div className="text-gray-500 italic">No events</div>
                ) : (
                  Object.entries(events.red).sort((a, b) => b[1] - a[1]).map(([type, count]) => (
                    <div key={type} className="flex justify-between text-gray-300">
                      <span>{type}</span>
                      <span className="text-red-400 font-bold">{count}</span>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Blue Corner */}
            <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-3">
              <div className="text-blue-400 font-medium mb-2 flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Zap className="w-4 h-4" />
                  {boutInfo.fighter2}
                </span>
                <Badge className="bg-blue-500/20 text-blue-400 text-xs" data-testid="blue-events-count">
                  {events.blueTotal}
                </Badge>
              </div>
              <div className="space-y-1 text-xs max-h-32 overflow-y-auto" data-testid="blue-events-list">
                {Object.entries(events.blue).length === 0 ? (
                  <div className="text-gray-500 italic">No events</div>
                ) : (
                  Object.entries(events.blue).sort((a, b) => b[1] - a[1]).map(([type, count]) => (
                    <div key={type} className="flex justify-between text-gray-300">
                      <span>{type}</span>
                      <span className="text-blue-400 font-bold">{count}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Computed Round Scores */}
        {roundResults.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs text-gray-400 uppercase tracking-wider">
              Round Scores (Server Computed)
            </div>
            <div className="space-y-1" data-testid="round-scores-list">
              {roundResults.map((round) => (
                <div key={round.round_number} className="flex items-center justify-between bg-gray-800/50 rounded px-3 py-2">
                  <span className="text-gray-400 font-medium">Round {round.round_number}</span>
                  <div className="flex items-center gap-3">
                    <span className="text-red-400 font-mono text-lg font-bold">{round.red_points}</span>
                    <span className="text-gray-500">-</span>
                    <span className="text-blue-400 font-mono text-lg font-bold">{round.blue_points}</span>
                  </div>
                  <span className="text-xs text-gray-500">
                    Δ {round.delta > 0 ? '+' : ''}{round.delta?.toFixed?.(1) || round.delta}
                  </span>
                </div>
              ))}
            </div>
            
            {/* Running Totals */}
            <div className="flex items-center justify-between bg-gradient-to-r from-amber-900/30 to-amber-800/20 border border-amber-500/30 rounded px-4 py-3 mt-2" data-testid="running-totals">
              <span className="text-amber-400 font-bold flex items-center gap-2">
                <Trophy className="w-4 h-4" />
                TOTAL
              </span>
              <div className="flex items-center gap-3">
                <span className="text-red-400 font-mono text-2xl font-bold">{runningTotals.red}</span>
                <span className="text-gray-500 text-xl">-</span>
                <span className="text-blue-400 font-mono text-2xl font-bold">{runningTotals.blue}</span>
              </div>
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="grid grid-cols-2 gap-3">
          <Button
            onClick={handleEndRound}
            disabled={isLoading}
            className="bg-amber-600 hover:bg-amber-700 text-white"
            data-testid="end-round-btn"
          >
            {isLoading ? (
              <RefreshCw className="w-4 h-4 animate-spin mr-2" />
            ) : (
              <Flag className="w-4 h-4 mr-2" />
            )}
            End Round {currentRound}
          </Button>

          <Button
            onClick={handleFinalizeFight}
            disabled={isLoading || roundResults.length === 0}
            className="bg-green-600 hover:bg-green-700 text-white"
            data-testid="finalize-fight-btn"
          >
            {isLoading ? (
              <RefreshCw className="w-4 h-4 animate-spin mr-2" />
            ) : (
              <Trophy className="w-4 h-4 mr-2" />
            )}
            Finalize Fight
          </Button>
        </div>

        {/* Server Authority Notice */}
        <div className="text-xs text-center text-gray-500 flex items-center justify-center gap-1">
          <CheckCircle className="w-3 h-3 text-green-500" />
          Server-authoritative scoring - All devices see same data
          {isConnected && <span className="text-green-400 ml-1">(WebSocket connected)</span>}
        </div>
      </Card>

      {/* Round Result Dialog */}
      <Dialog open={showRoundResult} onOpenChange={setShowRoundResult}>
        <DialogContent className="bg-gray-900 border-gray-700 text-white max-w-md">
          <DialogHeader>
            <DialogTitle className="text-center text-xl flex items-center justify-center gap-2">
              <Trophy className="w-6 h-6 text-amber-400" />
              Round {lastComputedRound?.round_number || currentRound} Complete
            </DialogTitle>
          </DialogHeader>
          
          {lastComputedRound && (
            <div className="space-y-4 py-4">
              {/* Round Score */}
              <div className="text-center">
                <div className="text-6xl font-bold mb-2">
                  <span className="text-red-400">{lastComputedRound.red_points}</span>
                  <span className="text-gray-500 mx-2">-</span>
                  <span className="text-blue-400">{lastComputedRound.blue_points}</span>
                </div>
                <div className="text-gray-400">
                  Delta: {lastComputedRound.delta > 0 ? '+' : ''}{lastComputedRound.delta?.toFixed?.(2) || lastComputedRound.delta}
                </div>
                <div className="text-sm text-amber-400 mt-1">
                  Winner: {lastComputedRound.winner}
                </div>
              </div>

              {/* Event Breakdown */}
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div className="bg-red-500/10 border border-red-500/30 rounded p-3">
                  <div className="text-red-400 font-medium mb-2">{boutInfo.fighter1}</div>
                  <div className="text-gray-300 text-xs space-y-1">
                    {Object.entries(lastComputedRound.red_breakdown || {}).map(([type, count]) => (
                      <div key={type} className="flex justify-between">
                        <span>{type}</span>
                        <span className="text-red-400">{count}</span>
                      </div>
                    ))}
                    <div className="border-t border-red-500/30 pt-1 mt-1">
                      <div className="flex justify-between font-bold">
                        <span>Total Delta</span>
                        <span>{lastComputedRound.red_total?.toFixed?.(1) || lastComputedRound.red_total}</span>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="bg-blue-500/10 border border-blue-500/30 rounded p-3">
                  <div className="text-blue-400 font-medium mb-2">{boutInfo.fighter2}</div>
                  <div className="text-gray-300 text-xs space-y-1">
                    {Object.entries(lastComputedRound.blue_breakdown || {}).map(([type, count]) => (
                      <div key={type} className="flex justify-between">
                        <span>{type}</span>
                        <span className="text-blue-400">{count}</span>
                      </div>
                    ))}
                    <div className="border-t border-blue-500/30 pt-1 mt-1">
                      <div className="flex justify-between font-bold">
                        <span>Total Delta</span>
                        <span>{lastComputedRound.blue_total?.toFixed?.(1) || lastComputedRound.blue_total}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Total Events */}
              <div className="text-center text-sm text-gray-400 flex items-center justify-center gap-2">
                <AlertCircle className="w-4 h-4 text-amber-400" />
                {lastComputedRound.total_events} events from ALL 4 operator devices
              </div>

              {/* Running Totals */}
              {roundResults.length > 0 && (
                <div className="border-t border-gray-700 pt-4">
                  <div className="text-xs text-gray-400 uppercase tracking-wider mb-2 text-center">
                    All Rounds
                  </div>
                  {roundResults.map((round) => (
                    <div key={round.round_number} className="flex items-center justify-between py-1">
                      <span className="text-gray-400">Round {round.round_number}</span>
                      <div>
                        <span className="text-red-400 font-bold">{round.red_points}</span>
                        <span className="text-gray-500 mx-1">-</span>
                        <span className="text-blue-400 font-bold">{round.blue_points}</span>
                      </div>
                    </div>
                  ))}
                  <div className="flex items-center justify-between py-2 border-t border-gray-700 mt-2">
                    <span className="text-amber-400 font-bold">TOTAL</span>
                    <div>
                      <span className="text-red-400 font-bold text-lg">{runningTotals.red}</span>
                      <span className="text-gray-500 mx-1">-</span>
                      <span className="text-blue-400 font-bold text-lg">{runningTotals.blue}</span>
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
