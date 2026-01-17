import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { 
  Monitor, 
  Trophy, 
  Flag, 
  Users, 
  Zap,
  RefreshCw,
  Maximize,
  Clock,
  Target,
  Award,
  Settings
} from 'lucide-react';
import { toast } from 'sonner';
import OperatorAssignmentPanel from './OperatorAssignmentPanel';

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * Supervisor Dashboard - Combined Scoring View
 * 
 * This is the SINGLE SOURCE OF TRUTH display.
 * Polls server every 500ms to show combined events from all 3 operators.
 * Designed to stream to arena big screen.
 */
export default function SupervisorDashboard() {
  const { boutId: paramBoutId } = useParams();
  const [boutId, setBoutId] = useState(paramBoutId || '');
  const [isConnected, setIsConnected] = useState(false);
  const [currentRound, setCurrentRound] = useState(1);
  const [totalRounds, setTotalRounds] = useState(5);
  const [isFullscreen, setIsFullscreen] = useState(false);
  
  // Bout info
  const [boutInfo, setBoutInfo] = useState({
    fighter1: 'Red Corner',
    fighter2: 'Blue Corner'
  });
  
  // Events aggregated by corner
  const [redEvents, setRedEvents] = useState({});
  const [blueEvents, setBlueEvents] = useState({});
  const [redTotal, setRedTotal] = useState(0);
  const [blueTotal, setBlueTotal] = useState(0);
  const [totalEvents, setTotalEvents] = useState(0);
  
  // Round results
  const [roundResults, setRoundResults] = useState([]);
  const [runningTotals, setRunningTotals] = useState({ red: 0, blue: 0 });
  
  // UI state
  const [isLoading, setIsLoading] = useState(false);
  const [showRoundResult, setShowRoundResult] = useState(false);
  const [lastRoundResult, setLastRoundResult] = useState(null);
  const [showFinalResult, setShowFinalResult] = useState(false);
  const [finalResult, setFinalResult] = useState(null);
  const [lastPollTime, setLastPollTime] = useState(null);
  const [showAssignmentPanel, setShowAssignmentPanel] = useState(false);
  const [operatorCount, setOperatorCount] = useState(0);

  // Fetch operator count
  const fetchOperatorCount = useCallback(async () => {
    if (!boutId) return;
    try {
      const response = await fetch(`${API}/api/operators/list?bout_id=${boutId}`);
      if (response.ok) {
        const data = await response.json();
        const assigned = (data.operators || []).filter(op => op.assigned_role).length;
        setOperatorCount(assigned);
      }
    } catch (e) {
      // Silent fail
    }
  }, [boutId]);

  // Poll operator count
  useEffect(() => {
    if (!boutId) return;
    fetchOperatorCount();
    const interval = setInterval(fetchOperatorCount, 5000);
    return () => clearInterval(interval);
  }, [boutId, fetchOperatorCount]);

  // Poll server for events
  const fetchEvents = useCallback(async () => {
    if (!boutId) return;
    
    try {
      const response = await fetch(`${API}/api/events?bout_id=${boutId}&round_number=${currentRound}`);
      if (response.ok) {
        const data = await response.json();
        
        // Aggregate events by corner
        const red = {};
        const blue = {};
        
        (data.events || []).forEach(evt => {
          const corner = evt.corner || (evt.fighter === 'fighter1' ? 'RED' : 'BLUE');
          const type = evt.event_type;
          
          if (corner === 'RED') {
            red[type] = (red[type] || 0) + 1;
          } else {
            blue[type] = (blue[type] || 0) + 1;
          }
        });
        
        setRedEvents(red);
        setBlueEvents(blue);
        setRedTotal(Object.values(red).reduce((a, b) => a + b, 0));
        setBlueTotal(Object.values(blue).reduce((a, b) => a + b, 0));
        setTotalEvents(data.total_events || 0);
        setIsConnected(true);
        setLastPollTime(new Date());
      }
    } catch (error) {
      console.error('Poll error:', error);
      setIsConnected(false);
    }
  }, [boutId, currentRound]);

  // Fetch round results
  const fetchRoundResults = useCallback(async () => {
    if (!boutId) return;
    
    try {
      const response = await fetch(`${API}/api/rounds?bout_id=${boutId}`);
      if (response.ok) {
        const data = await response.json();
        setRoundResults(data.rounds || []);
        setRunningTotals({
          red: data.running_red || 0,
          blue: data.running_blue || 0
        });
        setBoutInfo({
          fighter1: data.fighter1 || 'Red Corner',
          fighter2: data.fighter2 || 'Blue Corner'
        });
      }
    } catch (error) {
      console.error('Fetch rounds error:', error);
    }
  }, [boutId]);

  // Fetch bout info
  const fetchBoutInfo = useCallback(async () => {
    if (!boutId) return;
    
    try {
      const response = await fetch(`${API}/api/bouts/${boutId}`);
      if (response.ok) {
        const data = await response.json();
        setBoutInfo({
          fighter1: data.fighter1 || 'Red Corner',
          fighter2: data.fighter2 || 'Blue Corner'
        });
        setTotalRounds(data.totalRounds || 5);
        setCurrentRound(data.currentRound || 1);
      }
    } catch (error) {
      console.error('Fetch bout error:', error);
    }
  }, [boutId]);

  // Poll every 500ms
  useEffect(() => {
    if (!boutId) return;
    
    fetchBoutInfo();
    fetchEvents();
    fetchRoundResults();
    
    const interval = setInterval(() => {
      fetchEvents();
    }, 500);
    
    return () => clearInterval(interval);
  }, [boutId, currentRound, fetchEvents, fetchRoundResults, fetchBoutInfo]);

  // End Round - compute score
  const handleEndRound = async () => {
    if (!boutId) return;
    
    setIsLoading(true);
    try {
      const response = await fetch(`${API}/api/rounds/compute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bout_id: boutId,
          round_number: currentRound
        })
      });
      
      if (response.ok) {
        const result = await response.json();
        setLastRoundResult(result);
        setShowRoundResult(true);
        
        // Refresh round results
        await fetchRoundResults();
        
        toast.success(`Round ${currentRound}: ${result.red_points}-${result.blue_points}`);
      } else {
        toast.error('Failed to compute round');
      }
    } catch (error) {
      toast.error('Error computing round');
    } finally {
      setIsLoading(false);
    }
  };

  // Next Round
  const handleNextRound = () => {
    if (currentRound < totalRounds) {
      setCurrentRound(currentRound + 1);
      setShowRoundResult(false);
      toast.success(`Moving to Round ${currentRound + 1}`);
    }
  };

  // Finalize Fight
  const handleFinalizeFight = async () => {
    if (!boutId) return;
    
    setIsLoading(true);
    try {
      const response = await fetch(`${API}/api/fights/finalize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bout_id: boutId })
      });
      
      if (response.ok) {
        const result = await response.json();
        setFinalResult(result);
        setShowFinalResult(true);
        toast.success(`Fight finalized! Winner: ${result.winner_name}`);
      } else {
        toast.error('Failed to finalize fight');
      }
    } catch (error) {
      toast.error('Error finalizing fight');
    } finally {
      setIsLoading(false);
    }
  };

  // Toggle fullscreen
  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  // If no bout ID, show setup
  if (!boutId) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center p-8">
        <Card className="p-8 bg-gray-900 border-gray-700 max-w-md w-full">
          <div className="text-center space-y-6">
            <Monitor className="w-16 h-16 text-amber-500 mx-auto" />
            <h1 className="text-2xl font-bold text-white">Supervisor Dashboard</h1>
            <p className="text-gray-400">Enter bout ID to start monitoring</p>
            <Input
              value={boutId}
              onChange={(e) => setBoutId(e.target.value)}
              placeholder="Enter Bout ID"
              className="bg-gray-800 border-gray-600 text-white text-center text-lg"
            />
            <Button 
              onClick={() => boutId && fetchBoutInfo()}
              className="w-full bg-amber-500 hover:bg-amber-600 text-black font-bold"
            >
              Start Monitoring
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Header Bar */}
      <div className="bg-gray-900 border-b border-gray-800 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Monitor className="w-6 h-6 text-amber-500" />
          <span className="font-bold text-lg">SUPERVISOR DASHBOARD</span>
          <Badge className={isConnected ? 'bg-green-500' : 'bg-red-500'}>
            {isConnected ? 'LIVE' : 'OFFLINE'}
          </Badge>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-gray-400 text-sm">
            Bout: {boutId}
          </span>
          <Button size="sm" variant="outline" onClick={toggleFullscreen}>
            <Maximize className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <div className="p-6 space-y-6">
        
        {/* Fighter Names & Round Info */}
        <div className="text-center space-y-2">
          <div className="flex items-center justify-center gap-8 text-4xl font-bold">
            <span className="text-red-500">{boutInfo.fighter1}</span>
            <span className="text-gray-500">vs</span>
            <span className="text-blue-500">{boutInfo.fighter2}</span>
          </div>
          <div className="flex items-center justify-center gap-4">
            <Badge className="bg-amber-500 text-black text-lg px-4 py-1">
              ROUND {currentRound} of {totalRounds}
            </Badge>
            {lastPollTime && (
              <span className="text-gray-500 text-sm flex items-center gap-1">
                <Clock className="w-3 h-3" />
                Last sync: {lastPollTime.toLocaleTimeString()}
              </span>
            )}
          </div>
        </div>

        {/* Live Event Counts - Split Screen */}
        <div className="grid grid-cols-2 gap-6">
          {/* RED CORNER */}
          <Card className="bg-red-950/30 border-red-800 p-6">
            <div className="text-center mb-4">
              <div className="text-red-400 text-sm font-semibold uppercase tracking-wider">Red Corner</div>
              <div className="text-3xl font-bold text-white">{boutInfo.fighter1}</div>
            </div>
            
            {/* Event Count */}
            <div className="text-center mb-6">
              <div className="text-6xl font-bold text-red-400" style={{ fontFamily: 'monospace' }}>
                {redTotal}
              </div>
              <div className="text-gray-400 text-sm">events logged</div>
            </div>
            
            {/* Event Breakdown */}
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {Object.entries(redEvents).length === 0 ? (
                <div className="text-gray-500 text-center italic">No events yet</div>
              ) : (
                Object.entries(redEvents)
                  .sort((a, b) => b[1] - a[1])
                  .map(([type, count]) => (
                    <div key={type} className="flex justify-between items-center bg-red-900/30 rounded px-3 py-2">
                      <span className="text-gray-300">{type}</span>
                      <span className="text-red-400 font-bold text-lg">{count}</span>
                    </div>
                  ))
              )}
            </div>
            
            {/* Operators */}
            <div className="mt-4 pt-4 border-t border-red-800/50">
              <div className="text-xs text-gray-500 uppercase tracking-wider mb-2">Operators</div>
              <div className="flex gap-2">
                <Badge variant="outline" className="border-red-700 text-red-400">Red Striking</Badge>
                <Badge variant="outline" className="border-red-700 text-red-400">Red Grappling</Badge>
              </div>
            </div>
          </Card>

          {/* BLUE CORNER */}
          <Card className="bg-blue-950/30 border-blue-800 p-6">
            <div className="text-center mb-4">
              <div className="text-blue-400 text-sm font-semibold uppercase tracking-wider">Blue Corner</div>
              <div className="text-3xl font-bold text-white">{boutInfo.fighter2}</div>
            </div>
            
            {/* Event Count */}
            <div className="text-center mb-6">
              <div className="text-6xl font-bold text-blue-400" style={{ fontFamily: 'monospace' }}>
                {blueTotal}
              </div>
              <div className="text-gray-400 text-sm">events logged</div>
            </div>
            
            {/* Event Breakdown */}
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {Object.entries(blueEvents).length === 0 ? (
                <div className="text-gray-500 text-center italic">No events yet</div>
              ) : (
                Object.entries(blueEvents)
                  .sort((a, b) => b[1] - a[1])
                  .map(([type, count]) => (
                    <div key={type} className="flex justify-between items-center bg-blue-900/30 rounded px-3 py-2">
                      <span className="text-gray-300">{type}</span>
                      <span className="text-blue-400 font-bold text-lg">{count}</span>
                    </div>
                  ))
              )}
            </div>
            
            {/* Operators */}
            <div className="mt-4 pt-4 border-t border-blue-800/50">
              <div className="text-xs text-gray-500 uppercase tracking-wider mb-2">Operator</div>
              <div className="flex gap-2">
                <Badge variant="outline" className="border-blue-700 text-blue-400">Blue All</Badge>
              </div>
            </div>
          </Card>
        </div>

        {/* Round Scores */}
        {roundResults.length > 0 && (
          <Card className="bg-gray-900 border-gray-700 p-6">
            <div className="text-center mb-4">
              <div className="text-gray-400 text-sm font-semibold uppercase tracking-wider">Round Scores</div>
            </div>
            <div className="flex justify-center gap-4 flex-wrap">
              {roundResults.map((round) => (
                <div key={round.round_number} className="bg-gray-800 rounded-lg px-6 py-3 text-center min-w-[120px]">
                  <div className="text-gray-400 text-xs uppercase">Round {round.round_number}</div>
                  <div className="text-2xl font-bold">
                    <span className="text-red-400">{round.red_points}</span>
                    <span className="text-gray-500 mx-2">-</span>
                    <span className="text-blue-400">{round.blue_points}</span>
                  </div>
                </div>
              ))}
            </div>
            
            {/* Running Total */}
            <div className="mt-6 pt-4 border-t border-gray-700">
              <div className="flex items-center justify-center gap-8">
                <div className="text-center">
                  <div className="text-gray-400 text-xs uppercase">Total</div>
                  <div className="text-4xl font-bold">
                    <span className="text-red-400">{runningTotals.red}</span>
                    <span className="text-gray-500 mx-3">-</span>
                    <span className="text-blue-400">{runningTotals.blue}</span>
                  </div>
                </div>
                {runningTotals.red !== runningTotals.blue && (
                  <Badge className={`text-lg px-4 py-2 ${runningTotals.red > runningTotals.blue ? 'bg-red-600' : 'bg-blue-600'}`}>
                    {runningTotals.red > runningTotals.blue ? boutInfo.fighter1 : boutInfo.fighter2} leads
                  </Badge>
                )}
              </div>
            </div>
          </Card>
        )}

        {/* Action Buttons */}
        <div className="flex justify-center gap-4">
          <Button
            onClick={handleEndRound}
            disabled={isLoading}
            className="bg-amber-500 hover:bg-amber-600 text-black font-bold text-lg px-8 py-6"
          >
            {isLoading ? <RefreshCw className="w-5 h-5 animate-spin mr-2" /> : <Flag className="w-5 h-5 mr-2" />}
            END ROUND {currentRound}
          </Button>
          
          {roundResults.length > 0 && currentRound < totalRounds && (
            <Button
              onClick={handleNextRound}
              className="bg-green-600 hover:bg-green-700 text-white font-bold text-lg px-8 py-6"
            >
              <Zap className="w-5 h-5 mr-2" />
              NEXT ROUND
            </Button>
          )}
          
          {roundResults.length > 0 && (
            <Button
              onClick={handleFinalizeFight}
              disabled={isLoading}
              className="bg-purple-600 hover:bg-purple-700 text-white font-bold text-lg px-8 py-6"
            >
              <Trophy className="w-5 h-5 mr-2" />
              FINALIZE FIGHT
            </Button>
          )}
        </div>

        {/* Status Bar */}
        <div className="text-center text-gray-500 text-sm">
          <div className="flex items-center justify-center gap-4">
            <span className="flex items-center gap-1">
              <Target className="w-4 h-4" />
              {totalEvents} total events this round
            </span>
            <span>•</span>
            <span className="flex items-center gap-1">
              <Users className="w-4 h-4" />
              3 operators connected
            </span>
            <span>•</span>
            <span>Polling every 500ms</span>
          </div>
        </div>
      </div>

      {/* Round Result Dialog */}
      <Dialog open={showRoundResult} onOpenChange={setShowRoundResult}>
        <DialogContent className="bg-gray-900 border-gray-700 text-white max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-center text-2xl flex items-center justify-center gap-2">
              <Award className="w-8 h-8 text-amber-400" />
              Round {lastRoundResult?.round_number} Complete
            </DialogTitle>
          </DialogHeader>
          
          {lastRoundResult && (
            <div className="space-y-6 py-4">
              <div className="text-center">
                <div className="text-7xl font-bold mb-4">
                  <span className="text-red-400">{lastRoundResult.red_points}</span>
                  <span className="text-gray-500 mx-4">-</span>
                  <span className="text-blue-400">{lastRoundResult.blue_points}</span>
                </div>
                <Badge className={`text-xl px-6 py-2 ${
                  lastRoundResult.winner === 'RED' ? 'bg-red-600' : 
                  lastRoundResult.winner === 'BLUE' ? 'bg-blue-600' : 'bg-gray-600'
                }`}>
                  {lastRoundResult.winner === 'RED' ? boutInfo.fighter1 :
                   lastRoundResult.winner === 'BLUE' ? boutInfo.fighter2 : 'DRAW'}
                </Badge>
              </div>
              
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div className="bg-red-900/30 rounded p-3">
                  <div className="text-red-400 font-semibold mb-2">{boutInfo.fighter1}</div>
                  {Object.entries(lastRoundResult.red_breakdown || {}).map(([type, count]) => (
                    <div key={type} className="flex justify-between text-gray-300">
                      <span>{type}</span>
                      <span>{count}</span>
                    </div>
                  ))}
                </div>
                <div className="bg-blue-900/30 rounded p-3">
                  <div className="text-blue-400 font-semibold mb-2">{boutInfo.fighter2}</div>
                  {Object.entries(lastRoundResult.blue_breakdown || {}).map(([type, count]) => (
                    <div key={type} className="flex justify-between text-gray-300">
                      <span>{type}</span>
                      <span>{count}</span>
                    </div>
                  ))}
                </div>
              </div>
              
              <div className="text-center text-gray-400">
                {lastRoundResult.total_events} events scored
              </div>
              
              <div className="flex gap-3">
                <Button onClick={() => setShowRoundResult(false)} className="flex-1 bg-gray-700">
                  Close
                </Button>
                {currentRound < totalRounds && (
                  <Button onClick={() => { setShowRoundResult(false); handleNextRound(); }} className="flex-1 bg-green-600">
                    Next Round
                  </Button>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Final Result Dialog */}
      <Dialog open={showFinalResult} onOpenChange={setShowFinalResult}>
        <DialogContent className="bg-gray-900 border-gray-700 text-white max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-center text-2xl flex items-center justify-center gap-2">
              <Trophy className="w-8 h-8 text-amber-400" />
              FIGHT RESULT
            </DialogTitle>
          </DialogHeader>
          
          {finalResult && (
            <div className="space-y-6 py-4">
              <div className="text-center">
                <div className="text-6xl font-bold mb-4">
                  <span className="text-red-400">{finalResult.final_red}</span>
                  <span className="text-gray-500 mx-4">-</span>
                  <span className="text-blue-400">{finalResult.final_blue}</span>
                </div>
                <div className="text-3xl font-bold text-amber-400 mb-2">
                  WINNER
                </div>
                <div className={`text-4xl font-bold ${
                  finalResult.winner === 'RED' ? 'text-red-400' : 
                  finalResult.winner === 'BLUE' ? 'text-blue-400' : 'text-gray-400'
                }`}>
                  {finalResult.winner_name}
                </div>
              </div>
              
              <div className="space-y-2">
                {(finalResult.rounds || []).map((round) => (
                  <div key={round.round} className="flex justify-between items-center bg-gray-800 rounded px-4 py-2">
                    <span className="text-gray-400">Round {round.round}</span>
                    <span className="font-bold">
                      <span className="text-red-400">{round.red}</span>
                      <span className="text-gray-500 mx-2">-</span>
                      <span className="text-blue-400">{round.blue}</span>
                    </span>
                  </div>
                ))}
              </div>
              
              <Button onClick={() => setShowFinalResult(false)} className="w-full bg-amber-500 text-black font-bold">
                Close
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
