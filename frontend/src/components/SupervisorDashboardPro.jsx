import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
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
  TrendingUp,
  TrendingDown,
  Minus,
  ExternalLink,
  ChevronRight,
  Home,
  Plus,
  Trash2,
  Edit3
} from 'lucide-react';
import { toast } from 'sonner';
import OperatorAssignmentPanel from './OperatorAssignmentPanel';
import { BroadcastScorecard } from './lovable-broadcast/BroadcastScorecard';
import { FinalResult, RoundWinner, transformFinalResult } from './broadcast/FightJudgeAI';
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
// Delta is the sum of event values for the round
// 10-8 requires EXTREME one-sided dominance (multiple near-finishes)
// 10-7 is practically impossible (should almost never happen)
const getRoundScore = (delta) => {
  const absDelta = Math.abs(delta);
  if (absDelta <= 3) return { red: 10, blue: 10, label: 'DRAW' };
  if (absDelta < 500) return delta > 0 ? { red: 10, blue: 9, label: '10-9' } : { red: 9, blue: 10, label: '10-9' };
  if (absDelta < 700) return delta > 0 ? { red: 10, blue: 8, label: '10-8' } : { red: 8, blue: 10, label: '10-8' };
  return delta > 0 ? { red: 10, blue: 7, label: '10-7' } : { red: 7, blue: 10, label: '10-7' };
};

// Convert our data format to Lovable BroadcastScorecard format
const convertToLovableFormat = (boutInfo, roundResults, runningTotals, finalResult) => {
  // Build rounds array in Lovable format
  const rounds = [];
  for (let i = 0; i < 5; i++) {
    const roundData = roundResults.find(r => r.round_number === i + 1);
    if (roundData) {
      rounds.push({
        red: roundData.red_points,
        blue: roundData.blue_points,
        winner: roundData.red_points > roundData.blue_points ? 'red' : 
                roundData.blue_points > roundData.red_points ? 'blue' : null
      });
    } else {
      rounds.push({ red: null, blue: null, winner: null });
    }
  }
  
  // Determine winner
  let winner = null;
  if (finalResult) {
    winner = finalResult.winner === 'RED' ? 'red' : finalResult.winner === 'BLUE' ? 'blue' : null;
  }
  
  return {
    event: "PFC 50",
    division: "Main Event",
    status: finalResult ? "completed" : roundResults.length > 0 ? "in_progress" : "pending",
    red: {
      name: boutInfo.fighter1 || "Red Corner",
      photo: ""
    },
    blue: {
      name: boutInfo.fighter2 || "Blue Corner", 
      photo: ""
    },
    rounds: rounds,
    unified_total: {
      red: runningTotals.red || 0,
      blue: runningTotals.blue || 0
    },
    winner: winner
  };
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
  
  // Active control timers (from operators)
  const [activeControls, setActiveControls] = useState({ red: null, blue: null });
  
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
  const [nextFight, setNextFight] = useState(null);
  const [showFinishMethodDialog, setShowFinishMethodDialog] = useState(false);
  const [finishMethod, setFinishMethod] = useState(null);
  const [showResultBroadcast, setShowResultBroadcast] = useState(false);
  
  // Round Review state
  const [showRoundReview, setShowRoundReview] = useState(false);
  const [reviewRoundNumber, setReviewRoundNumber] = useState(null);
  const [reviewRoundData, setReviewRoundData] = useState(null);
  const [reviewRoundEvents, setReviewRoundEvents] = useState([]);
  
  // Round Broadcast state
  const [showRoundBroadcast, setShowRoundBroadcast] = useState(false);
  
  // Supervisor Event Management state
  const [showEventManager, setShowEventManager] = useState(false);
  const [selectedCorner, setSelectedCorner] = useState('RED');
  
  const navigate = useNavigate();

  // Quick event types for supervisor to add
  const QUICK_EVENTS = {
    striking: [
      { type: 'Jab', label: 'Jab' },
      { type: 'Cross', label: 'Cross' },
      { type: 'Hook', label: 'Hook' },
      { type: 'Uppercut', label: 'Upper' },
      { type: 'Kick', label: 'Kick' },
      { type: 'Knee', label: 'Knee' },
      { type: 'Elbow', label: 'Elbow' },
    ],
    significant: [
      { type: 'SS Jab', label: 'SS Jab' },
      { type: 'SS Cross', label: 'SS Cross' },
      { type: 'SS Hook', label: 'SS Hook' },
      { type: 'SS Kick', label: 'SS Kick' },
      { type: 'SS Knee', label: 'SS Knee' },
      { type: 'SS Elbow', label: 'SS Elbow' },
    ],
    damage: [
      { type: 'Rocked', label: 'Rocked' },
      { type: 'KD', label: 'KD Flash', metadata: { tier: 'Flash' } },
      { type: 'KD', label: 'KD Hard', metadata: { tier: 'Hard' } },
      { type: 'KD', label: 'KD NF', metadata: { tier: 'Near-Finish' } },
    ],
    grappling: [
      { type: 'Takedown', label: 'Takedown' },
      { type: 'Takedown Stuffed', label: 'TD Stuffed' },
      { type: 'Ground Strike', label: 'GnP Light', metadata: { quality: 'LIGHT' } },
      { type: 'Ground Strike', label: 'GnP Hard', metadata: { quality: 'SOLID' } },
    ],
    submissions: [
      { type: 'Submission Attempt', label: 'Sub Light', metadata: { tier: 'Light' } },
      { type: 'Submission Attempt', label: 'Sub Deep', metadata: { tier: 'Deep' } },
      { type: 'Submission Attempt', label: 'Sub NF', metadata: { tier: 'Near-Finish' } },
    ],
  };

  // Add event as supervisor
  const handleSupervisorAddEvent = async (eventType, metadata = {}) => {
    if (!boutId) return;
    
    try {
      const response = await fetch(`${API}/api/events/supervisor`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bout_id: boutId,
          round_number: currentRound,
          corner: selectedCorner,
          event_type: eventType,
          metadata: metadata
        })
      });
      
      if (response.ok) {
        toast.success(`Added ${eventType} for ${selectedCorner}`);
        fetchEvents(); // Refresh events
      } else {
        toast.error('Failed to add event');
      }
    } catch (error) {
      toast.error('Error adding event');
    }
  };

  // Delete event as supervisor
  const handleDeleteEvent = async (event) => {
    if (!boutId) return;
    
    try {
      const response = await fetch(`${API}/api/events/by-id/${encodeURIComponent(event.created_at)}?bout_id=${boutId}`, {
        method: 'DELETE'
      });
      
      if (response.ok) {
        toast.success(`Deleted ${event.event_type}`);
        fetchEvents(); // Refresh events
      } else {
        toast.error('Failed to delete event');
      }
    } catch (error) {
      toast.error('Error deleting event');
    }
  };

  // Fetch round data for review
  const fetchRoundForReview = async (roundNum) => {
    if (!boutId || !roundNum) return;
    
    try {
      // Fetch events for the specific round
      const eventsResponse = await fetch(`${API}/api/events?bout_id=${boutId}&round_number=${roundNum}`);
      if (eventsResponse.ok) {
        const eventsData = await eventsResponse.json();
        setReviewRoundEvents(eventsData.events || []);
      }
      
      // Fetch round score
      const scoreResponse = await fetch(`${API}/api/rounds/compute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bout_id: boutId, round_number: roundNum })
      });
      
      if (scoreResponse.ok) {
        const scoreData = await scoreResponse.json();
        setReviewRoundData(scoreData);
      }
      
      setReviewRoundNumber(roundNum);
      setShowRoundReview(true);
    } catch (error) {
      console.error('Error fetching round for review:', error);
      toast.error('Failed to load round data');
    }
  };

  // Fetch next fight in the event
  const fetchNextFight = useCallback(async () => {
    if (!boutId) return;
    try {
      // Get event ID from current bout
      const boutResponse = await fetch(`${API}/api/bouts/${boutId}`);
      if (!boutResponse.ok) return;
      const boutData = await boutResponse.json();
      const eventId = boutData.event_id;
      
      if (!eventId) return;
      
      // Get all fights for this event
      const fightsResponse = await fetch(`${API}/api/supervisor/fights?event_id=${eventId}`);
      if (!fightsResponse.ok) return;
      const fightsData = await fightsResponse.json();
      const fights = fightsData.fights || [];
      
      // Find current fight index and get next one
      const currentIndex = fights.findIndex(f => f.bout_id === boutId);
      if (currentIndex >= 0 && currentIndex < fights.length - 1) {
        const next = fights[currentIndex + 1];
        setNextFight(next);
      }
    } catch (error) {
      console.error('Error fetching next fight:', error);
    }
  }, [boutId]);

  // Fetch next fight when final result is shown
  useEffect(() => {
    if (showFinalResult) {
      fetchNextFight();
    }
  }, [showFinalResult, fetchNextFight]);

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
      // Silently ignore operator count fetch errors
    }
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
        
        // Detect active control timers (CTRL_START without matching CTRL_END)
        const detectActiveControl = (cornerEvents) => {
          const ctrlStarts = {};
          const ctrlEnds = {};
          
          cornerEvents.forEach(e => {
            const ctrlType = e.metadata?.control_type || 'TOP';
            if (e.event_type === 'CTRL_START') {
              ctrlStarts[ctrlType] = e;
            } else if (e.event_type === 'CTRL_END') {
              ctrlEnds[ctrlType] = e;
            }
          });
          
          // Return the control type that has a start but no end
          for (const ctrlType of Object.keys(ctrlStarts)) {
            if (!ctrlEnds[ctrlType]) {
              return ctrlType;
            }
          }
          return null;
        };
        
        setActiveControls({
          red: detectActiveControl(red),
          blue: detectActiveControl(blue)
        });
        
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

  // End Round - compute and auto-advance
  const handleEndRound = async () => {
    if (!boutId) return;
    
    setIsLoading(true);
    try {
      // 1. Compute the round score
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
        await fetchRoundResults();
        
        toast.success(`Round ${currentRound}: ${result.red_points}-${result.blue_points} (${result.winner === 'RED' ? boutInfo.fighter1 : result.winner === 'BLUE' ? boutInfo.fighter2 : 'DRAW'})`);
        
        // 2. Auto-advance to next round if not final
        if (currentRound < totalRounds) {
          const advanceResponse = await fetch(`${API}/api/bouts/${boutId}/advance-round`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
          });
          
          if (advanceResponse.ok) {
            const advanceData = await advanceResponse.json();
            if (advanceData.success) {
              setCurrentRound(advanceData.current_round);
              toast.success(`Moving to Round ${advanceData.current_round}`, { duration: 2000 });
            }
          }
        } else {
          toast.info('Final round completed! Click "Finalize" to declare winner.');
        }
        
        setShowRoundResult(true);
      } else {
        toast.error('Failed to compute round');
      }
    } catch (error) {
      toast.error('Error computing round');
    } finally {
      setIsLoading(false);
    }
  };

  // Show finish method dialog
  const handleFinalizeFight = () => {
    setShowFinishMethodDialog(true);
  };

  // Actually finalize the fight with selected method
  const confirmFinalizeFight = async (method) => {
    if (!boutId) return;
    
    setFinishMethod(method);
    setIsLoading(true);
    try {
      const response = await fetch(`${API}/api/fights/finalize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ bout_id: boutId, finish_method: method })
      });
      
      if (response.ok) {
        const result = await response.json();
        // Add finish method to result
        result.finish_method = method;
        setFinalResult(result);
        setShowFinishMethodDialog(false);
        setShowFinalResult(true);
        toast.success(`Fight finalized! Winner: ${result.winner_name} by ${method}`);
      } else {
        toast.error('Failed to finalize fight');
      }
    } catch (error) {
      toast.error('Error finalizing fight');
    } finally {
      setIsLoading(false);
    }
  };

  // Show result on arena broadcast
  const showOnArena = () => {
    setShowResultBroadcast(true);
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
          <Button size="sm" variant="outline" onClick={() => setShowEventManager(true)} className="border-green-500 text-green-400">
            <Edit3 className="w-4 h-4 mr-1" /> Edit Events
          </Button>
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
          
          {/* Active Control Timer Indicator */}
          {activeControls.red && (
            <div className="bg-green-900/50 border border-green-500 rounded-lg p-2 mb-3 flex items-center justify-center animate-pulse">
              <span className="w-3 h-3 bg-green-400 rounded-full mr-2 animate-ping"></span>
              <span className="text-green-400 font-bold text-sm uppercase">
                {activeControls.red} Control Active
              </span>
            </div>
          )}
          
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
                    <div key={idx} className="bg-red-900/30 rounded px-3 py-2 flex items-center justify-between group">
                      <div className="flex-1">
                        <div className="text-white font-medium">{event.event_type}</div>
                        {tier && <div className="text-red-400 text-xs">{tier}</div>}
                        <div className="text-gray-500 text-xs">{event.device_role}</div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge className="bg-red-700 text-white">+{delta}</Badge>
                        <Button 
                          size="sm" 
                          variant="ghost" 
                          onClick={() => handleDeleteEvent(event)}
                          className="opacity-0 group-hover:opacity-100 transition-opacity h-6 w-6 p-0 text-red-400 hover:text-red-300 hover:bg-red-900/50"
                        >
                          <Trash2 className="w-3 h-3" />
                        </Button>
                      </div>
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
              <div className="flex items-center justify-between mb-2">
                <div className="text-gray-400 text-xs uppercase">Completed Rounds</div>
                <div className="text-gray-500 text-xs">Click to review</div>
              </div>
              <div className="space-y-1">
                {roundResults.map((round) => (
                  <div 
                    key={round.round_number} 
                    onClick={() => fetchRoundForReview(round.round_number)}
                    className="flex items-center justify-between bg-gray-900/50 rounded px-3 py-2 cursor-pointer hover:bg-gray-800/70 transition-colors"
                  >
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
            <Button onClick={handleEndRound} disabled={isLoading || currentRound > totalRounds} className="w-full bg-amber-500 hover:bg-amber-600 text-black font-bold h-12">
              {isLoading ? <RefreshCw className="w-5 h-5 animate-spin mr-2" /> : <Flag className="w-5 h-5 mr-2" />}
              END ROUND {currentRound}
            </Button>
            
            {roundResults.length > 0 && (
              <Button onClick={handleFinalizeFight} disabled={isLoading} className="w-full bg-purple-600 hover:bg-purple-700">
                <Trophy className="w-4 h-4 mr-2" /> Finalize Fight
              </Button>
            )}
          </div>
        </Card>

        {/* RIGHT - Blue Corner Events */}
        <Card className="bg-blue-950/20 border-blue-900 p-4 flex flex-col">
          <div className="flex items-center justify-between mb-3">
            <div className="text-blue-400 font-bold">{boutInfo.fighter2}</div>
            <Badge className="bg-blue-600 text-lg">{blueEvents.length} events</Badge>
          </div>
          
          {/* Active Control Timer Indicator */}
          {activeControls.blue && (
            <div className="bg-green-900/50 border border-green-500 rounded-lg p-2 mb-3 flex items-center justify-center animate-pulse">
              <span className="w-3 h-3 bg-green-400 rounded-full mr-2 animate-ping"></span>
              <span className="text-green-400 font-bold text-sm uppercase">
                {activeControls.blue} Control Active
              </span>
            </div>
          )}
          
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
                    <div key={idx} className="bg-blue-900/30 rounded px-3 py-2 flex items-center justify-between group">
                      <div className="flex-1">
                        <div className="text-white font-medium">{event.event_type}</div>
                        {tier && <div className="text-blue-400 text-xs">{tier}</div>}
                        <div className="text-gray-500 text-xs">{event.device_role}</div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge className="bg-blue-700 text-white">+{delta}</Badge>
                        <Button 
                          size="sm" 
                          variant="ghost" 
                          onClick={() => handleDeleteEvent(event)}
                          className="opacity-0 group-hover:opacity-100 transition-opacity h-6 w-6 p-0 text-blue-400 hover:text-blue-300 hover:bg-blue-900/50"
                        >
                          <Trash2 className="w-3 h-3" />
                        </Button>
                      </div>
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

      {/* Arena Broadcast View - Using Lovable Frontend */}
      <Dialog open={showBroadcast} onOpenChange={setShowBroadcast}>
        <DialogContent className="bg-black border-lb-gold/30 text-white max-w-5xl p-0 overflow-hidden">
          <div className="h-[600px]">
            <BroadcastScorecard
              data={convertToLovableFormat(boutInfo, roundResults, runningTotals, finalResult)}
              connectionStatus="connected"
              isLoading={false}
              displayMode={finalResult ? "final" : "scores"}
            />
          </div>
          <div className="absolute top-2 right-12 flex gap-2">
            <Button 
              size="sm" 
              variant="ghost" 
              onClick={() => window.open(`/pfc50?bout=${boutId}`, '_blank')}
              className="text-amber-400 hover:text-amber-300"
            >
              <ExternalLink className="w-4 h-4 mr-1" /> Open Fullscreen
            </Button>
          </div>
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
              {currentRound <= totalRounds ? (
                <div className="text-green-400 text-sm">
                  Auto-advancing to Round {currentRound}...
                </div>
              ) : (
                <div className="text-amber-400 text-sm">
                  Final round complete! Click &quot;Finalize Fight&quot; to declare winner.
                </div>
              )}
              {/* Show Round on Arena Button */}
              <Button 
                onClick={() => {
                  setShowRoundBroadcast(true);
                  setShowRoundResult(false);
                }}
                className="w-full bg-amber-500 hover:bg-amber-600 text-black font-bold"
              >
                <Tv className="w-5 h-5 mr-2" />
                Show Round Result on Arena
              </Button>
              <Button onClick={() => setShowRoundResult(false)} className="w-full bg-gray-700 hover:bg-gray-600 mt-2">
                Close
              </Button>
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
                  <div className="text-xl text-gray-400">WINNER BY {finalResult.finish_method || finishMethod}</div>
                  <div className={`text-4xl font-bold ${finalResult.winner === 'RED' ? 'text-red-400' : 'text-blue-400'}`}>
                    {finalResult.winner_name}
                  </div>
                </div>
              </>
            )}
            
            {/* Show on Arena Button */}
            <Button 
              onClick={showOnArena}
              className="w-full bg-amber-500 hover:bg-amber-600 text-black font-bold py-3"
            >
              <Tv className="w-5 h-5 mr-2" />
              Show Result on Arena Screen
            </Button>
            
            <div className="flex gap-3 justify-center pt-2">
              {nextFight ? (
                <Button 
                  onClick={() => {
                    setShowFinalResult(false);
                    navigate(`/supervisor/${nextFight.bout_id}`);
                  }} 
                  className="bg-green-600 hover:bg-green-700 text-white font-bold px-6"
                >
                  <ChevronRight className="w-4 h-4 mr-2" />
                  Next Fight: {nextFight.fighter1} vs {nextFight.fighter2}
                </Button>
              ) : (
                <Button 
                  onClick={() => {
                    setShowFinalResult(false);
                    navigate('/control');
                  }} 
                  className="bg-blue-600 hover:bg-blue-700 text-white font-bold px-6"
                >
                  <Home className="w-4 h-4 mr-2" />
                  Back to Control Panel
                </Button>
              )}
              <Button onClick={() => setShowFinalResult(false)} variant="outline" className="border-gray-600 text-gray-300">
                Close
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Finish Method Selection Dialog */}
      <Dialog open={showFinishMethodDialog} onOpenChange={setShowFinishMethodDialog}>
        <DialogContent className="bg-gray-900 border-amber-500 text-white max-w-md">
          <DialogHeader>
            <DialogTitle className="text-2xl text-center text-amber-400">How Did The Fight End?</DialogTitle>
          </DialogHeader>
          <div className="grid grid-cols-2 gap-4 py-6">
            <Button 
              onClick={() => confirmFinalizeFight('KO')}
              disabled={isLoading}
              className="h-20 text-xl font-bold bg-red-600 hover:bg-red-700 text-white"
            >
              KO
              <span className="block text-xs font-normal opacity-75">Knockout</span>
            </Button>
            <Button 
              onClick={() => confirmFinalizeFight('TKO')}
              disabled={isLoading}
              className="h-20 text-xl font-bold bg-orange-600 hover:bg-orange-700 text-white"
            >
              TKO
              <span className="block text-xs font-normal opacity-75">Technical KO</span>
            </Button>
            <Button 
              onClick={() => confirmFinalizeFight('SUB')}
              disabled={isLoading}
              className="h-20 text-xl font-bold bg-purple-600 hover:bg-purple-700 text-white"
            >
              SUB
              <span className="block text-xs font-normal opacity-75">Submission</span>
            </Button>
            <Button 
              onClick={() => confirmFinalizeFight('DEC')}
              disabled={isLoading}
              className="h-20 text-xl font-bold bg-blue-600 hover:bg-blue-700 text-white"
            >
              DEC
              <span className="block text-xs font-normal opacity-75">Decision</span>
            </Button>
          </div>
          <Button 
            onClick={() => setShowFinishMethodDialog(false)} 
            variant="outline" 
            className="w-full border-gray-600 text-gray-400"
          >
            Cancel
          </Button>
        </DialogContent>
      </Dialog>

      {/* Arena Result Broadcast - Using FJAI Component */}
      <Dialog open={showResultBroadcast} onOpenChange={setShowResultBroadcast}>
        <DialogContent className="bg-black border-none text-white max-w-2xl p-0 fjai-broadcast">
          <div className="relative w-full bg-gradient-to-b from-gray-900 to-black p-2">
            {/* Close button */}
            <Button 
              onClick={() => setShowResultBroadcast(false)}
              className="absolute top-2 right-2 bg-gray-800 hover:bg-gray-700 z-10"
              size="sm"
            >
              Close
            </Button>
            
            {/* FJAI Final Result Component */}
            <FinalResult
              total={{
                red: finalResult?.final_red || runningTotals.red,
                blue: finalResult?.final_blue || runningTotals.blue
              }}
              winner={finalResult?.winner?.toLowerCase() || null}
              redName={boutInfo.fighter1}
              blueName={boutInfo.fighter2}
              isVisible={true}
              finishMethod={finalResult?.finish_method || finishMethod}
              totalRounds={totalRounds}
            />
          </div>
        </DialogContent>
      </Dialog>

      {/* Round Winner Broadcast Dialog */}
      <Dialog open={showRoundBroadcast} onOpenChange={setShowRoundBroadcast}>
        <DialogContent className="bg-black border-none text-white max-w-2xl p-0 fjai-broadcast">
          <div className="relative w-full bg-gradient-to-b from-gray-900 to-black p-2">
            {/* Close button */}
            <Button 
              onClick={() => setShowRoundBroadcast(false)}
              className="absolute top-2 right-2 bg-gray-800 hover:bg-gray-700 z-10"
              size="sm"
            >
              Close
            </Button>
            
            {/* FJAI Round Winner Component */}
            {lastRoundResult && (
              <RoundWinner
                round={{
                  unified_red: lastRoundResult.red_points,
                  unified_blue: lastRoundResult.blue_points
                }}
                roundNumber={lastRoundResult.round_number}
                redName={boutInfo.fighter1}
                blueName={boutInfo.fighter2}
                isVisible={true}
              />
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Round Review Dialog */}
      <Dialog open={showRoundReview} onOpenChange={setShowRoundReview}>
        <DialogContent className="bg-gray-900 border-gray-700 text-white max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-xl flex items-center gap-2">
              <Clock className="w-5 h-5 text-amber-400" />
              Round {reviewRoundNumber} Review
            </DialogTitle>
          </DialogHeader>
          
          {reviewRoundData && (
            <div className="space-y-4">
              {/* Round Score Summary */}
              <div className="bg-gray-800 rounded-lg p-4">
                <div className="text-center mb-4">
                  <div className="text-gray-400 text-sm uppercase mb-2">Round {reviewRoundNumber} Score</div>
                  <div className="flex items-center justify-center gap-8">
                    <div className="text-center">
                      <div className="text-red-400 text-4xl font-bold">{reviewRoundData.red_points}</div>
                      <div className="text-gray-400 text-sm">{boutInfo.fighter1}</div>
                    </div>
                    <div className="text-gray-600 text-2xl">-</div>
                    <div className="text-center">
                      <div className="text-blue-400 text-4xl font-bold">{reviewRoundData.blue_points}</div>
                      <div className="text-gray-400 text-sm">{boutInfo.fighter2}</div>
                    </div>
                  </div>
                  <Badge className={`mt-3 ${
                    reviewRoundData.winner === 'RED' ? 'bg-red-600' : 
                    reviewRoundData.winner === 'BLUE' ? 'bg-blue-600' : 'bg-gray-600'
                  }`}>
                    {reviewRoundData.winner === 'RED' ? `${boutInfo.fighter1} wins round` : 
                     reviewRoundData.winner === 'BLUE' ? `${boutInfo.fighter2} wins round` : 'DRAW'}
                  </Badge>
                </div>
                
                {/* Delta Breakdown */}
                <div className="grid grid-cols-2 gap-4 mt-4">
                  <div className="bg-red-900/30 rounded p-3">
                    <div className="text-red-400 text-sm font-semibold mb-1">Red Delta</div>
                    <div className="text-white text-2xl font-bold">{reviewRoundData.red_total?.toFixed(1) || 0}</div>
                  </div>
                  <div className="bg-blue-900/30 rounded p-3">
                    <div className="text-blue-400 text-sm font-semibold mb-1">Blue Delta</div>
                    <div className="text-white text-2xl font-bold">{reviewRoundData.blue_total?.toFixed(1) || 0}</div>
                  </div>
                </div>
              </div>
              
              {/* Event Breakdown */}
              <div className="grid grid-cols-2 gap-4">
                {/* Red Events */}
                <div className="bg-red-950/30 rounded-lg p-3">
                  <div className="text-red-400 font-semibold mb-2 flex items-center gap-2">
                    {boutInfo.fighter1}
                    <Badge className="bg-red-700">{reviewRoundData.red_breakdown ? Object.values(reviewRoundData.red_breakdown).reduce((a, b) => a + b, 0) : 0} events</Badge>
                  </div>
                  <div className="space-y-1 max-h-48 overflow-y-auto">
                    {reviewRoundData.red_breakdown && Object.entries(reviewRoundData.red_breakdown).map(([eventType, count]) => (
                      <div key={eventType} className="flex justify-between text-sm bg-red-900/30 rounded px-2 py-1">
                        <span className="text-gray-300">{eventType}</span>
                        <span className="text-red-400 font-semibold">x{count}</span>
                      </div>
                    ))}
                    {(!reviewRoundData.red_breakdown || Object.keys(reviewRoundData.red_breakdown).length === 0) && (
                      <div className="text-gray-500 text-sm italic">No events</div>
                    )}
                  </div>
                </div>
                
                {/* Blue Events */}
                <div className="bg-blue-950/30 rounded-lg p-3">
                  <div className="text-blue-400 font-semibold mb-2 flex items-center gap-2">
                    {boutInfo.fighter2}
                    <Badge className="bg-blue-700">{reviewRoundData.blue_breakdown ? Object.values(reviewRoundData.blue_breakdown).reduce((a, b) => a + b, 0) : 0} events</Badge>
                  </div>
                  <div className="space-y-1 max-h-48 overflow-y-auto">
                    {reviewRoundData.blue_breakdown && Object.entries(reviewRoundData.blue_breakdown).map(([eventType, count]) => (
                      <div key={eventType} className="flex justify-between text-sm bg-blue-900/30 rounded px-2 py-1">
                        <span className="text-gray-300">{eventType}</span>
                        <span className="text-blue-400 font-semibold">x{count}</span>
                      </div>
                    ))}
                    {(!reviewRoundData.blue_breakdown || Object.keys(reviewRoundData.blue_breakdown).length === 0) && (
                      <div className="text-gray-500 text-sm italic">No events</div>
                    )}
                  </div>
                </div>
              </div>
              
              {/* All Events Timeline */}
              {reviewRoundEvents.length > 0 && (
                <div className="bg-gray-800 rounded-lg p-3">
                  <div className="text-gray-400 text-sm font-semibold mb-2">Event Timeline ({reviewRoundEvents.length} events)</div>
                  <ScrollArea className="max-h-48">
                    <div className="space-y-1">
                      {reviewRoundEvents.map((event, idx) => (
                        <div key={idx} className={`flex items-center justify-between text-sm rounded px-2 py-1 ${
                          event.corner === 'RED' ? 'bg-red-900/20' : 'bg-blue-900/20'
                        }`}>
                          <div className="flex items-center gap-2">
                            <span className={event.corner === 'RED' ? 'text-red-400' : 'text-blue-400'}>
                              {event.corner}
                            </span>
                            <span className="text-white">{event.event_type}</span>
                            {event.metadata?.tier && <span className="text-gray-400 text-xs">({event.metadata.tier})</span>}
                          </div>
                          <span className="text-gray-500 text-xs">{event.device_role}</span>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </div>
              )}
            </div>
          )}
          
          <div className="flex justify-end mt-4">
            <Button onClick={() => setShowRoundReview(false)} variant="outline" className="border-gray-600">
              Close
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
