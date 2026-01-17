import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
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
  Tv,
  ChevronRight,
  TrendingUp,
  TrendingDown,
  Minus,
  ExternalLink
} from 'lucide-react';
import { toast } from 'sonner';
import OperatorAssignmentPanel from './OperatorAssignmentPanel';
import { BroadcastScorecard } from './lovable-broadcast/BroadcastScorecard';
import '@/styles/lovable-broadcast.css';

const API = process.env.REACT_APP_BACKEND_URL;

// Delta values for each event type (must match backend)
const EVENT_DELTAS = {
  'KD': { 'Near-Finish': 100, 'Hard': 70, 'Flash': 40, default: 40 },
  'Rocked/Stunned': 30,
  'Takedown Landed': 25,
  'Takedown Defended': 5,
  'Submission Attempt': { 'Near-Finish': 100, 'Deep': 60, 'Standard': 30, default: 30 },
  'Sweep/Reversal': 20,
  'Back Control': 15,
  'Mount Control': 15,
  'Guard Passing': 10,
  'Ground Control': 5,
  'Head Kick': 15,
  'Body Kick': 8,
  'Leg Kick': 5,
  'Cross': 14,
  'Hook': 14,
  'Uppercut': 14,
  'Elbow': 14,
  'Knee': 12,
  'Jab': 10,
  'Ground Strike': 8,
};

// Get delta value for an event
const getEventDelta = (eventType, tier) => {
  const value = EVENT_DELTAS[eventType];
  if (typeof value === 'object') {
    return value[tier] || value.default || 10;
  }
  return value || 10;
};

// Determine round score from delta
const getRoundScore = (delta) => {
  const absDelta = Math.abs(delta);
  if (absDelta <= 3) return { red: 10, blue: 10, label: 'DRAW' };
  if (absDelta < 140) return delta > 0 ? { red: 10, blue: 9, label: '10-9' } : { red: 9, blue: 10, label: '10-9' };
  if (absDelta < 200) return delta > 0 ? { red: 10, blue: 8, label: '10-8' } : { red: 8, blue: 10, label: '10-8' };
  return delta > 0 ? { red: 10, blue: 7, label: '10-7' } : { red: 7, blue: 10, label: '10-7' };
};

export default function SupervisorDashboardPro() {
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
  
  // Raw events (all details)
  const [allEvents, setAllEvents] = useState([]);
  const [redEvents, setRedEvents] = useState([]);
  const [blueEvents, setBlueEvents] = useState([]);
  
  // Delta calculations
  const [redDelta, setRedDelta] = useState(0);
  const [blueDelta, setBlueDelta] = useState(0);
  const [netDelta, setNetDelta] = useState(0);
  
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
  const [showBroadcast, setShowBroadcast] = useState(false);
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
    } catch (e) {}
  }, [boutId]);

  // Poll operator count
  useEffect(() => {
    if (!boutId) return;
    fetchOperatorCount();
    const interval = setInterval(fetchOperatorCount, 5000);
    return () => clearInterval(interval);
  }, [boutId, fetchOperatorCount]);

  // Fetch events with full details
  const fetchEvents = useCallback(async () => {
    if (!boutId) return;
    
    try {
      const response = await fetch(`${API}/api/events?bout_id=${boutId}&round_number=${currentRound}`);
      if (response.ok) {
        const data = await response.json();
        const events = data.events || [];
        
        setAllEvents(events);
        
        // Separate by corner
        const red = events.filter(e => e.corner === 'RED' || e.fighter === 'fighter1');
        const blue = events.filter(e => e.corner === 'BLUE' || e.fighter === 'fighter2');
        
        setRedEvents(red);
        setBlueEvents(blue);
        
        // Calculate deltas
        let redTotal = 0;
        let blueTotal = 0;
        
        red.forEach(e => {
          const tier = e.metadata?.tier;
          redTotal += getEventDelta(e.event_type, tier);
        });
        
        blue.forEach(e => {
          const tier = e.metadata?.tier;
          blueTotal += getEventDelta(e.event_type, tier);
        });
        
        setRedDelta(redTotal);
        setBlueDelta(blueTotal);
        setNetDelta(redTotal - blueTotal);
        
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

  // End Round
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

  // Current round prediction
  const currentPrediction = getRoundScore(netDelta);
  const currentLeader = netDelta > 3 ? 'RED' : netDelta < -3 ? 'BLUE' : 'EVEN';

  // If no bout ID, show setup
  if (!boutId) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center p-8">
        <Card className="p-8 bg-gray-900 border-gray-700 max-w-md w-full">
          <div className="text-center space-y-6">
            <Monitor className="w-16 h-16 text-amber-500 mx-auto" />
            <h1 className="text-2xl font-bold text-white">Supervisor Dashboard Pro</h1>
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
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header Bar */}
      <div className="bg-black border-b border-gray-800 px-4 py-2 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Monitor className="w-5 h-5 text-amber-500" />
          <span className="font-bold">SUPERVISOR PRO</span>
          <Badge className={isConnected ? 'bg-green-500' : 'bg-red-500'}>
            {isConnected ? 'LIVE' : 'OFFLINE'}
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="outline" onClick={() => setShowAssignmentPanel(true)} className="border-amber-500 text-amber-400">
            <Users className="w-4 h-4 mr-1" /> Operators ({operatorCount}/3)
          </Button>
          <Button size="sm" variant="outline" onClick={() => setShowBroadcast(true)} className="border-purple-500 text-purple-400">
            <Tv className="w-4 h-4 mr-1" /> Arena View
          </Button>
          <Button size="sm" variant="ghost" onClick={toggleFullscreen}>
            <Maximize className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Fighter Header */}
      <div className="bg-gradient-to-r from-red-900/30 via-gray-900 to-blue-900/30 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="text-center flex-1">
            <div className="text-red-400 text-sm font-semibold">RED CORNER</div>
            <div className="text-3xl font-bold text-white">{boutInfo.fighter1}</div>
          </div>
          <div className="text-center px-8">
            <Badge className="bg-amber-500 text-black text-lg px-4">ROUND {currentRound}</Badge>
            <div className="text-gray-500 text-xs mt-1">of {totalRounds}</div>
          </div>
          <div className="text-center flex-1">
            <div className="text-blue-400 text-sm font-semibold">BLUE CORNER</div>
            <div className="text-3xl font-bold text-white">{boutInfo.fighter2}</div>
          </div>
        </div>
      </div>

      {/* Main Content - 3 Column Layout */}
      <div className="grid grid-cols-3 gap-4 p-4 h-[calc(100vh-180px)]">
        
        {/* LEFT - Red Corner Events */}
        <Card className="bg-red-950/20 border-red-900 p-4 flex flex-col">
          <div className="flex items-center justify-between mb-3">
            <div className="text-red-400 font-bold">{boutInfo.fighter1}</div>
            <Badge className="bg-red-600 text-lg">{redEvents.length} events</Badge>
          </div>
          
          {/* Delta Score */}
          <div className="bg-red-900/30 rounded-lg p-3 mb-3 text-center">
            <div className="text-gray-400 text-xs uppercase">Delta Score</div>
            <div className="text-4xl font-bold text-red-400">{redDelta.toFixed(1)}</div>
          </div>
          
          {/* Event List */}
          <ScrollArea className="flex-1">
            <div className="space-y-2">
              {redEvents.length === 0 ? (
                <div className="text-gray-500 text-center italic py-4">No events yet</div>
              ) : (
                redEvents.map((event, idx) => {
                  const tier = event.metadata?.tier;
                  const delta = getEventDelta(event.event_type, tier);
                  return (
                    <div key={idx} className="bg-red-900/30 rounded px-3 py-2 flex items-center justify-between">
                      <div>
                        <div className="text-white font-medium">{event.event_type}</div>
                        {tier && <div className="text-red-400 text-xs">{tier}</div>}
                        <div className="text-gray-500 text-xs">{event.device_role}</div>
                      </div>
                      <Badge className="bg-red-700 text-white">+{delta}</Badge>
                    </div>
                  );
                })
              )}
            </div>
          </ScrollArea>
        </Card>

        {/* CENTER - Delta Comparison & Controls */}
        <Card className="bg-gray-900 border-gray-700 p-4 flex flex-col">
          {/* Net Delta Display */}
          <div className="text-center mb-4">
            <div className="text-gray-400 text-sm uppercase tracking-wider">Net Delta</div>
            <div className={`text-6xl font-bold ${netDelta > 0 ? 'text-red-400' : netDelta < 0 ? 'text-blue-400' : 'text-gray-400'}`}>
              {netDelta > 0 ? '+' : ''}{netDelta.toFixed(1)}
            </div>
            <div className="flex items-center justify-center gap-2 mt-2">
              {currentLeader === 'RED' && <TrendingUp className="w-5 h-5 text-red-400" />}
              {currentLeader === 'BLUE' && <TrendingDown className="w-5 h-5 text-blue-400" />}
              {currentLeader === 'EVEN' && <Minus className="w-5 h-5 text-gray-400" />}
              <span className={`font-bold ${currentLeader === 'RED' ? 'text-red-400' : currentLeader === 'BLUE' ? 'text-blue-400' : 'text-gray-400'}`}>
                {currentLeader === 'RED' ? boutInfo.fighter1 : currentLeader === 'BLUE' ? boutInfo.fighter2 : 'EVEN'}
              </span>
            </div>
          </div>

          {/* Predicted Round Score */}
          <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4 mb-4 text-center">
            <div className="text-amber-400 text-sm uppercase tracking-wider mb-2">Projected Round Score</div>
            <div className="text-4xl font-bold">
              <span className="text-red-400">{currentPrediction.red}</span>
              <span className="text-gray-500 mx-2">-</span>
              <span className="text-blue-400">{currentPrediction.blue}</span>
            </div>
            <Badge className={`mt-2 ${currentPrediction.label === 'DRAW' ? 'bg-gray-600' : netDelta > 0 ? 'bg-red-600' : 'bg-blue-600'}`}>
              {currentPrediction.label} {currentPrediction.label !== 'DRAW' && (netDelta > 0 ? boutInfo.fighter1 : boutInfo.fighter2)}
            </Badge>
          </div>

          {/* Delta Breakdown */}
          <div className="bg-gray-800/50 rounded-lg p-3 mb-4">
            <div className="text-gray-400 text-xs uppercase mb-2">Delta Breakdown</div>
            <div className="flex justify-between items-center">
              <div className="text-center">
                <div className="text-red-400 font-bold text-xl">{redDelta.toFixed(1)}</div>
                <div className="text-gray-500 text-xs">RED</div>
              </div>
              <div className="text-2xl text-gray-600">vs</div>
              <div className="text-center">
                <div className="text-blue-400 font-bold text-xl">{blueDelta.toFixed(1)}</div>
                <div className="text-gray-500 text-xs">BLUE</div>
              </div>
            </div>
          </div>

          {/* Round Results */}
          {roundResults.length > 0 && (
            <div className="bg-gray-800/50 rounded-lg p-3 mb-4 flex-1">
              <div className="text-gray-400 text-xs uppercase mb-2">Completed Rounds</div>
              <div className="space-y-1">
                {roundResults.map((round) => (
                  <div key={round.round_number} className="flex items-center justify-between bg-gray-900/50 rounded px-3 py-2">
                    <span className="text-gray-400">R{round.round_number}</span>
                    <div className="font-bold">
                      <span className="text-red-400">{round.red_points}</span>
                      <span className="text-gray-500 mx-1">-</span>
                      <span className="text-blue-400">{round.blue_points}</span>
                    </div>
                    <Badge className={round.red_points > round.blue_points ? 'bg-red-600' : round.blue_points > round.red_points ? 'bg-blue-600' : 'bg-gray-600'}>
                      {round.red_points > round.blue_points ? 'RED' : round.blue_points > round.red_points ? 'BLUE' : 'DRAW'}
                    </Badge>
                  </div>
                ))}
              </div>
              {/* Running Total */}
              <div className="mt-3 pt-3 border-t border-gray-700 flex items-center justify-between">
                <span className="text-amber-400 font-bold">TOTAL</span>
                <div className="text-xl font-bold">
                  <span className="text-red-400">{runningTotals.red}</span>
                  <span className="text-gray-500 mx-2">-</span>
                  <span className="text-blue-400">{runningTotals.blue}</span>
                </div>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="space-y-2 mt-auto">
            <Button onClick={handleEndRound} disabled={isLoading} className="w-full bg-amber-500 hover:bg-amber-600 text-black font-bold h-12">
              {isLoading ? <RefreshCw className="w-5 h-5 animate-spin mr-2" /> : <Flag className="w-5 h-5 mr-2" />}
              END ROUND {currentRound}
            </Button>
            
            <div className="grid grid-cols-2 gap-2">
              {roundResults.length > 0 && currentRound < totalRounds && (
                <Button onClick={handleNextRound} className="bg-green-600 hover:bg-green-700">
                  <ChevronRight className="w-4 h-4 mr-1" /> Next Round
                </Button>
              )}
              {roundResults.length > 0 && (
                <Button onClick={handleFinalizeFight} disabled={isLoading} className="bg-purple-600 hover:bg-purple-700">
                  <Trophy className="w-4 h-4 mr-1" /> Finalize
                </Button>
              )}
            </div>
          </div>
        </Card>

        {/* RIGHT - Blue Corner Events */}
        <Card className="bg-blue-950/20 border-blue-900 p-4 flex flex-col">
          <div className="flex items-center justify-between mb-3">
            <div className="text-blue-400 font-bold">{boutInfo.fighter2}</div>
            <Badge className="bg-blue-600 text-lg">{blueEvents.length} events</Badge>
          </div>
          
          {/* Delta Score */}
          <div className="bg-blue-900/30 rounded-lg p-3 mb-3 text-center">
            <div className="text-gray-400 text-xs uppercase">Delta Score</div>
            <div className="text-4xl font-bold text-blue-400">{blueDelta.toFixed(1)}</div>
          </div>
          
          {/* Event List */}
          <ScrollArea className="flex-1">
            <div className="space-y-2">
              {blueEvents.length === 0 ? (
                <div className="text-gray-500 text-center italic py-4">No events yet</div>
              ) : (
                blueEvents.map((event, idx) => {
                  const tier = event.metadata?.tier;
                  const delta = getEventDelta(event.event_type, tier);
                  return (
                    <div key={idx} className="bg-blue-900/30 rounded px-3 py-2 flex items-center justify-between">
                      <div>
                        <div className="text-white font-medium">{event.event_type}</div>
                        {tier && <div className="text-blue-400 text-xs">{tier}</div>}
                        <div className="text-gray-500 text-xs">{event.device_role}</div>
                      </div>
                      <Badge className="bg-blue-700 text-white">+{delta}</Badge>
                    </div>
                  );
                })
              )}
            </div>
          </ScrollArea>
        </Card>
      </div>

      {/* Status Bar */}
      <div className="fixed bottom-0 left-0 right-0 bg-black/90 border-t border-gray-800 px-4 py-2">
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-4 text-gray-400">
            <span className="flex items-center gap-1">
              <Zap className="w-4 h-4 text-amber-400" />
              {allEvents.length} events
            </span>
            <span className="flex items-center gap-1">
              <Users className="w-4 h-4" />
              {operatorCount} operators
            </span>
          </div>
          <div className="flex items-center gap-1 text-gray-500">
            <Clock className="w-3 h-3" />
            {lastPollTime?.toLocaleTimeString()}
          </div>
        </div>
      </div>

      {/* Assignment Panel Dialog */}
      <Dialog open={showAssignmentPanel} onOpenChange={setShowAssignmentPanel}>
        <DialogContent className="bg-gray-900 border-gray-700 text-white max-w-2xl max-h-[90vh] overflow-y-auto">
          <OperatorAssignmentPanel boutId={boutId} onClose={() => setShowAssignmentPanel(false)} />
        </DialogContent>
      </Dialog>

      {/* Arena Broadcast View */}
      <Dialog open={showBroadcast} onOpenChange={setShowBroadcast}>
        <DialogContent className="bg-black border-none text-white max-w-4xl p-0">
          <ArenaBroadcastView 
            boutInfo={boutInfo}
            currentRound={currentRound}
            totalRounds={totalRounds}
            roundResults={roundResults}
            runningTotals={runningTotals}
            lastRoundResult={lastRoundResult}
            finalResult={finalResult}
          />
        </DialogContent>
      </Dialog>

      {/* Round Result Dialog */}
      <Dialog open={showRoundResult} onOpenChange={setShowRoundResult}>
        <DialogContent className="bg-gray-900 border-gray-700 text-white max-w-md">
          <DialogHeader>
            <DialogTitle className="text-center text-2xl flex items-center justify-center gap-2">
              <Award className="w-8 h-8 text-amber-400" />
              Round {lastRoundResult?.round_number} Complete
            </DialogTitle>
          </DialogHeader>
          {lastRoundResult && (
            <div className="space-y-4 py-4 text-center">
              <div className="text-6xl font-bold">
                <span className="text-red-400">{lastRoundResult.red_points}</span>
                <span className="text-gray-500 mx-3">-</span>
                <span className="text-blue-400">{lastRoundResult.blue_points}</span>
              </div>
              <Badge className={`text-lg px-4 py-2 ${lastRoundResult.winner === 'RED' ? 'bg-red-600' : lastRoundResult.winner === 'BLUE' ? 'bg-blue-600' : 'bg-gray-600'}`}>
                {lastRoundResult.winner === 'RED' ? boutInfo.fighter1 : lastRoundResult.winner === 'BLUE' ? boutInfo.fighter2 : 'DRAW'}
              </Badge>
              <div className="text-gray-400 text-sm">
                Delta: {lastRoundResult.delta?.toFixed(1)} | {lastRoundResult.total_events} events
              </div>
              <div className="flex gap-2 mt-4">
                <Button onClick={() => setShowRoundResult(false)} variant="outline" className="flex-1">Close</Button>
                {currentRound < totalRounds && (
                  <Button onClick={() => { setShowRoundResult(false); handleNextRound(); }} className="flex-1 bg-green-600">Next Round</Button>
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Final Result Dialog */}
      <Dialog open={showFinalResult} onOpenChange={setShowFinalResult}>
        <DialogContent className="bg-black border-amber-500 text-white max-w-lg">
          <div className="text-center space-y-6 py-6">
            <Trophy className="w-16 h-16 text-amber-400 mx-auto" />
            <div className="text-3xl font-bold text-amber-400">FIGHT RESULT</div>
            {finalResult && (
              <>
                <div className="text-5xl font-bold">
                  <span className="text-red-400">{finalResult.final_red}</span>
                  <span className="text-gray-500 mx-3">-</span>
                  <span className="text-blue-400">{finalResult.final_blue}</span>
                </div>
                <div>
                  <div className="text-xl text-gray-400">WINNER</div>
                  <div className={`text-4xl font-bold ${finalResult.winner === 'RED' ? 'text-red-400' : 'text-blue-400'}`}>
                    {finalResult.winner_name}
                  </div>
                </div>
              </>
            )}
            <Button onClick={() => setShowFinalResult(false)} className="bg-amber-500 text-black font-bold">Close</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

// Arena Broadcast Component - For Big Screen
function ArenaBroadcastView({ boutInfo, currentRound, totalRounds, roundResults, runningTotals, lastRoundResult, finalResult }) {
  return (
    <div className="bg-gradient-to-b from-gray-900 to-black p-8 min-h-[500px]">
      {/* Title */}
      <div className="text-center mb-8">
        <div className="text-amber-400 text-sm font-semibold tracking-widest">OFFICIAL SCORING</div>
      </div>

      {/* Fighters */}
      <div className="flex items-center justify-center gap-12 mb-8">
        <div className="text-center">
          <div className="text-red-400 text-sm uppercase tracking-wider">Red Corner</div>
          <div className="text-4xl font-bold text-white">{boutInfo.fighter1}</div>
        </div>
        <div className="text-gray-600 text-3xl">VS</div>
        <div className="text-center">
          <div className="text-blue-400 text-sm uppercase tracking-wider">Blue Corner</div>
          <div className="text-4xl font-bold text-white">{boutInfo.fighter2}</div>
        </div>
      </div>

      {/* Round Scores */}
      {roundResults.length > 0 && (
        <div className="space-y-3 mb-8">
          {roundResults.map((round) => (
            <div key={round.round_number} className="flex items-center justify-center gap-8 bg-gray-800/50 rounded-lg py-3 px-6">
              <span className="text-gray-400 text-xl w-32">ROUND {round.round_number}</span>
              <div className="text-3xl font-bold">
                <span className="text-red-400">{round.red_points}</span>
                <span className="text-gray-600 mx-4">-</span>
                <span className="text-blue-400">{round.blue_points}</span>
              </div>
              <Badge className={`w-24 justify-center ${round.red_points > round.blue_points ? 'bg-red-600' : round.blue_points > round.red_points ? 'bg-blue-600' : 'bg-gray-600'}`}>
                {round.red_points > round.blue_points ? boutInfo.fighter1.split(' ')[0] : round.blue_points > round.red_points ? boutInfo.fighter2.split(' ')[0] : 'DRAW'}
              </Badge>
            </div>
          ))}
        </div>
      )}

      {/* Total Score */}
      {roundResults.length > 0 && (
        <div className="bg-gradient-to-r from-red-900/30 via-amber-900/30 to-blue-900/30 rounded-xl p-6 text-center border border-amber-500/30">
          <div className="text-amber-400 text-sm font-semibold tracking-widest mb-2">TOTAL SCORE</div>
          <div className="text-6xl font-bold">
            <span className="text-red-400">{runningTotals.red}</span>
            <span className="text-gray-600 mx-4">-</span>
            <span className="text-blue-400">{runningTotals.blue}</span>
          </div>
          {runningTotals.red !== runningTotals.blue && (
            <div className="mt-4">
              <Badge className={`text-xl px-6 py-2 ${runningTotals.red > runningTotals.blue ? 'bg-red-600' : 'bg-blue-600'}`}>
                {runningTotals.red > runningTotals.blue ? boutInfo.fighter1 : boutInfo.fighter2} LEADING
              </Badge>
            </div>
          )}
        </div>
      )}

      {/* Final Result */}
      {finalResult && (
        <div className="mt-8 text-center">
          <div className="text-amber-400 text-2xl font-bold mb-4">🏆 WINNER 🏆</div>
          <div className={`text-5xl font-bold ${finalResult.winner === 'RED' ? 'text-red-400' : 'text-blue-400'}`}>
            {finalResult.winner_name}
          </div>
        </div>
      )}
    </div>
  );
}
