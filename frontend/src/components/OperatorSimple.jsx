import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { 
  Swords, 
  Shield, 
  Target,
  Wifi,
  WifiOff,
  ArrowLeft,
  Zap,
  Keyboard
} from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

// Clean, organized event configurations with consistent styling
// Ground Strike is ONLY in grappling, NOT in striking
const STRIKING_EVENTS = [
  // Basic Strikes - Neutral dark
  { type: 'Jab', category: 'strike', tier: null, key: '1' },
  { type: 'Cross', category: 'strike', tier: null, key: '2' },
  { type: 'Hook', category: 'strike', tier: null, key: '3' },
  { type: 'Uppercut', category: 'strike', tier: null, key: '4' },
  { type: 'Elbow', category: 'strike', tier: null, key: '5' },
  { type: 'Knee', category: 'strike', tier: null, key: '6' },
  { type: 'Kick', category: 'strike', tier: null, key: '7' },
  // Damage - Escalating danger
  { type: 'Rocked/Stunned', category: 'damage', tier: null, key: 'Q', label: 'Rocked' },
  { type: 'KD', category: 'damage-kd', tier: 'Flash', key: 'W', label: 'KD Flash' },
  { type: 'KD', category: 'damage-kd', tier: 'Hard', key: 'E', label: 'KD Hard' },
  { type: 'KD', category: 'damage-kd', tier: 'Near-Finish', key: 'R', label: 'KD Near-Finish' },
];

const GRAPPLING_EVENTS = [
  // Takedowns
  { type: 'Takedown Landed', category: 'grappling', tier: null, key: 'V', label: 'TD Landed' },
  { type: 'Takedown Defended', category: 'grappling', tier: null, key: 'B', label: 'TD Defended' },
  // Ground Strike - belongs with grappling
  { type: 'Ground Strike', category: 'strike', tier: null, key: 'G', label: 'Ground Strike' },
  // Submissions - Escalating danger
  { type: 'Submission Attempt', category: 'submission', tier: 'Standard', key: 'A', label: 'Sub Attempt' },
  { type: 'Submission Attempt', category: 'submission', tier: 'Deep', key: 'S', label: 'Sub Deep' },
  { type: 'Submission Attempt', category: 'submission', tier: 'Near-Finish', key: 'D', label: 'Sub Near-Finish' },
];

// Get button style based on category - clean, professional colors
const getButtonStyle = (category, corner) => {
  const isRed = corner === 'RED';
  
  switch (category) {
    case 'strike':
      return isRed 
        ? 'bg-slate-700 hover:bg-slate-600 border-slate-600' 
        : 'bg-slate-700 hover:bg-slate-600 border-slate-600';
    case 'damage':
      return 'bg-amber-600 hover:bg-amber-500 border-amber-500';
    case 'damage-kd':
      return 'bg-red-600 hover:bg-red-500 border-red-500';
    case 'grappling':
      return 'bg-emerald-700 hover:bg-emerald-600 border-emerald-600';
    case 'control':
      return 'bg-cyan-700 hover:bg-cyan-600 border-cyan-600';
    case 'submission':
      return 'bg-purple-700 hover:bg-purple-600 border-purple-600';
    case 'control-active':
      return 'bg-green-600 hover:bg-green-500 border-green-500 animate-pulse';
    default:
      return 'bg-slate-700 hover:bg-slate-600 border-slate-600';
  }
};

// Format seconds to MM:SS
const formatTime = (seconds) => {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

/**
 * OperatorSimple - Professional event logging for operators
 */
export default function OperatorSimple() {
  const { boutId } = useParams();
  const navigate = useNavigate();
  
  const [deviceRole, setDeviceRole] = useState(localStorage.getItem('device_role') || 'RED_STRIKING');
  const [operatorName, setOperatorName] = useState(localStorage.getItem('sync_device_name') || 'Operator');
  const [currentRound, setCurrentRound] = useState(1);
  const [totalRounds, setTotalRounds] = useState(5);
  const [isConnected, setIsConnected] = useState(true);
  const [eventCount, setEventCount] = useState(0);
  const [lastEvent, setLastEvent] = useState(null);
  const [boutInfo, setBoutInfo] = useState({ fighter1: 'Red Corner', fighter2: 'Blue Corner' });
  const [roundJustChanged, setRoundJustChanged] = useState(false);
  
  // Control timer state - tracks cumulative time per control type for the round
  const [activeControl, setActiveControl] = useState(null); // 'Back Control', 'Top Control', 'Cage Control'
  const [controlTime, setControlTime] = useState(0); // Current session time
  const [controlTotals, setControlTotals] = useState({
    'Back Control': 0,
    'Top Control': 0,
    'Cage Control': 0
  }); // Cumulative time per control type for the round
  
  // Ground strike quality toggle state
  const [groundStrikeQuality, setGroundStrikeQuality] = useState('SOLID'); // 'SOLID' or 'LIGHT'

  // Determine corner from role
  const corner = deviceRole.startsWith('RED') ? 'RED' : 'BLUE';
  const fighterName = corner === 'RED' ? boutInfo.fighter1 : boutInfo.fighter2;
  
  // Determine which events to show
  const getEventsForRole = () => {
    if (deviceRole === 'RED_STRIKING') return STRIKING_EVENTS;
    if (deviceRole === 'RED_GRAPPLING') return GRAPPLING_EVENTS;
    if (deviceRole === 'BLUE_ALL') return [...STRIKING_EVENTS, ...GRAPPLING_EVENTS];
    return STRIKING_EVENTS;
  };

  // Keyboard shortcuts handler
  useEffect(() => {
    const handleKeyDown = async (event) => {
      if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') return;
      if (!boutId) return;

      const key = event.key;
      const shortcutKeys = ['1', '2', '3', '4', '5', '6', '7', 't', 'v', 'b', 'a', 's', 'd', 'q', 'w', 'e', 'r', 'g', 'z', 'x', 'c', 'f'];
      
      if (shortcutKeys.includes(key.toLowerCase())) {
        event.preventDefault();
      }

      try {
        // STRIKING
        if (key === '1') { await logEvent('Jab'); }
        else if (key === '2') { await logEvent('Cross'); }
        else if (key === '3') { await logEvent('Hook'); }
        else if (key === '4') { await logEvent('Uppercut'); }
        else if (key === '5') { await logEvent('Elbow'); }
        else if (key === '6') { await logEvent('Knee'); }
        else if (key === '7' || key.toLowerCase() === 't') { await logEvent('Kick'); }
        // Ground Strike - ONLY for grappling roles (RED_GRAPPLING or BLUE_ALL)
        // Uses current quality setting (SOLID/LIGHT toggle)
        else if (key.toLowerCase() === 'g') { 
          if (deviceRole === 'RED_GRAPPLING' || deviceRole === 'BLUE_ALL') {
            await logEvent('Ground Strike', null, groundStrikeQuality); 
          }
        }
        // Toggle ground strike quality with 'F' key
        else if (key.toLowerCase() === 'f') {
          if (deviceRole === 'RED_GRAPPLING' || deviceRole === 'BLUE_ALL') {
            setGroundStrikeQuality(prev => prev === 'SOLID' ? 'LIGHT' : 'SOLID');
            toast.info(`Ground strike quality: ${groundStrikeQuality === 'SOLID' ? 'LIGHT' : 'SOLID'}`, { duration: 800 });
          }
        }
        // GRAPPLING
        else if (key.toLowerCase() === 'v') { await logEvent('Takedown Landed'); }
        else if (key.toLowerCase() === 'b') { await logEvent('Takedown Defended'); }
        // SUBMISSIONS
        else if (key.toLowerCase() === 'a') { await logEvent('Submission Attempt', 'Standard'); }
        else if (key.toLowerCase() === 's') { await logEvent('Submission Attempt', 'Deep'); }
        else if (key.toLowerCase() === 'd') { await logEvent('Submission Attempt', 'Near-Finish'); }
        // DAMAGE
        else if (key.toLowerCase() === 'q') { await logEvent('Rocked/Stunned'); }
        else if (key.toLowerCase() === 'w') { await logEvent('KD', 'Flash'); }
        else if (key.toLowerCase() === 'e') { await logEvent('KD', 'Hard'); }
        else if (key.toLowerCase() === 'r') { await logEvent('KD', 'Near-Finish'); }
        // Control timers - Z, X, C (only for grappling roles)
        else if (key.toLowerCase() === 'z') { 
          if (deviceRole === 'RED_GRAPPLING' || deviceRole === 'BLUE_ALL') handleControlToggle('Back Control'); 
        }
        else if (key.toLowerCase() === 'x') { 
          if (deviceRole === 'RED_GRAPPLING' || deviceRole === 'BLUE_ALL') handleControlToggle('Top Control'); 
        }
        else if (key.toLowerCase() === 'c') { 
          if (deviceRole === 'RED_GRAPPLING' || deviceRole === 'BLUE_ALL') handleControlToggle('Cage Control'); 
        }
      } catch (error) {
        console.error('Keyboard shortcut error:', error);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [boutId, corner, currentRound, deviceRole, fighterName, activeControl, groundStrikeQuality]);

  // Control timer - increment every second when active
  useEffect(() => {
    if (!activeControl) return;
    
    const interval = setInterval(() => {
      setControlTime(prev => prev + 1);
    }, 1000);
    
    return () => clearInterval(interval);
  }, [activeControl]);

  // Reset control totals when round changes
  useEffect(() => {
    // Log any active control time and reset totals for new round
    if (activeControl && controlTime > 0) {
      // Add current session to totals before resetting
      setControlTotals(prev => ({
        ...prev,
        [activeControl]: prev[activeControl] + controlTime
      }));
    }
    // Reset for new round
    setActiveControl(null);
    setControlTime(0);
    setControlTotals({
      'Back Control': 0,
      'Top Control': 0,
      'Cage Control': 0
    });
  }, [currentRound]);

  // Handle control toggle (start/stop timer) - accumulates time within round
  const handleControlToggle = async (controlType) => {
    if (activeControl === controlType) {
      // Stop the timer - add current session to cumulative total
      const sessionTime = controlTime;
      const newTotal = controlTotals[controlType] + sessionTime;
      
      // Update cumulative totals
      setControlTotals(prev => ({
        ...prev,
        [controlType]: newTotal
      }));
      
      setActiveControl(null);
      setControlTime(0);
      
      // Log the cumulative control time for this round
      try {
        const response = await fetch(`${API}/api/events`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            bout_id: boutId,
            round_number: currentRound,
            corner: corner,
            aspect: 'GRAPPLING',
            event_type: controlType === 'Top Control' ? 'Ground Top Control' : 
                       controlType === 'Cage Control' ? 'Cage Control Time' :
                       controlType === 'Back Control' ? 'Ground Back Control' : controlType,
            device_role: deviceRole,
            metadata: { 
              duration: newTotal,
              session_time: sessionTime,
              is_cumulative: true
            }
          })
        });
        
        if (response.ok) {
          setEventCount(prev => prev + 1);
          setLastEvent({ type: controlType, tier: `${newTotal}s total`, time: new Date() });
          toast.success(`${controlType}: ${formatTime(newTotal)} total logged`);
        }
      } catch (error) {
        toast.error('Failed to log control time');
      }
    } else {
      // Start new timer (stop any existing one first and save its time)
      if (activeControl) {
        // Save the previous control's time to totals
        const prevSessionTime = controlTime;
        const prevTotal = controlTotals[activeControl] + prevSessionTime;
        
        setControlTotals(prev => ({
          ...prev,
          [activeControl]: prevTotal
        }));
        
        // Log CTRL_END for previous control
        try {
          await fetch(`${API}/api/events`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              bout_id: boutId,
              round_number: currentRound,
              corner: corner,
              aspect: 'GRAPPLING',
              event_type: 'CTRL_END',
              device_role: deviceRole,
              metadata: { 
                control_type: activeControl === 'Top Control' ? 'TOP' : 
                             activeControl === 'Cage Control' ? 'CAGE' :
                             activeControl === 'Back Control' ? 'BACK' : 'TOP'
              }
            })
          });
        } catch (error) {
          console.error('Failed to log CTRL_END');
        }
        
        // Log the previous control with duration
        try {
          await fetch(`${API}/api/events`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              bout_id: boutId,
              round_number: currentRound,
              corner: corner,
              aspect: 'GRAPPLING',
              event_type: activeControl === 'Top Control' ? 'Ground Top Control' : 
                         activeControl === 'Cage Control' ? 'Cage Control Time' :
                         activeControl === 'Back Control' ? 'Ground Back Control' : activeControl,
              device_role: deviceRole,
              metadata: { 
                duration: prevTotal,
                session_time: prevSessionTime,
                is_cumulative: true
              }
            })
          });
          toast.info(`${activeControl}: ${formatTime(prevTotal)} total logged`);
        } catch (error) {
          console.error('Failed to log previous control');
        }
      }
      
      // Log CTRL_START for new control
      try {
        await fetch(`${API}/api/events`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            bout_id: boutId,
            round_number: currentRound,
            corner: corner,
            aspect: 'GRAPPLING',
            event_type: 'CTRL_START',
            device_role: deviceRole,
            metadata: { 
              control_type: controlType === 'Top Control' ? 'TOP' : 
                           controlType === 'Cage Control' ? 'CAGE' :
                           controlType === 'Back Control' ? 'BACK' : 'TOP'
            }
          })
        });
      } catch (error) {
        console.error('Failed to log CTRL_START');
      }
      
      // Start the new control timer (continue from previous total if any)
      setActiveControl(controlType);
      setControlTime(0); // Start fresh session, total is in controlTotals
      toast.info(`${controlType} timer started (${formatTime(controlTotals[controlType])} already logged)`);
    }
  };

  // Poll for round changes from supervisor
  useEffect(() => {
    if (!boutId) return;
    
    const syncRound = async () => {
      try {
        const response = await fetch(`${API}/api/bouts/${boutId}/current-round`);
        if (response.ok) {
          const data = await response.json();
          setIsConnected(true);
          setBoutInfo({
            fighter1: data.fighter1 || 'Red Corner',
            fighter2: data.fighter2 || 'Blue Corner'
          });
          setTotalRounds(data.total_rounds || 5);
          
          if (data.current_round !== currentRound) {
            setCurrentRound(data.current_round);
            setEventCount(0);
            setRoundJustChanged(true);
            toast.success(`Round ${data.current_round} started!`, { duration: 3000 });
            setTimeout(() => setRoundJustChanged(false), 2000);
          }
        }
      } catch (error) {
        setIsConnected(false);
      }
    };
    
    const interval = setInterval(syncRound, 1000);
    syncRound();
    return () => clearInterval(interval);
  }, [boutId, currentRound]);

  // Fetch bout info
  useEffect(() => {
    const fetchBout = async () => {
      try {
        const response = await fetch(`${API}/api/bouts/${boutId}`);
        if (response.ok) {
          const data = await response.json();
          setBoutInfo({
            fighter1: data.fighter1 || 'Red Corner',
            fighter2: data.fighter2 || 'Blue Corner'
          });
          setCurrentRound(data.currentRound || 1);
        }
      } catch (error) {
        console.error('Error fetching bout:', error);
      }
    };
    if (boutId) fetchBout();
  }, [boutId]);

  // Log event to server
  const logEvent = async (eventType, tier = null, quality = null) => {
    try {
      const metadata = {};
      if (tier) metadata.tier = tier;
      if (quality) metadata.quality = quality;
      
      const response = await fetch(`${API}/api/events`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bout_id: boutId,
          round_number: currentRound,
          corner: corner,
          aspect: deviceRole.includes('GRAPPLING') ? 'GRAPPLING' : 
                  deviceRole === 'BLUE_ALL' ? 'ALL' : 'STRIKING',
          event_type: eventType,
          device_role: deviceRole,
          metadata: Object.keys(metadata).length > 0 ? metadata : {}
        })
      });
      
      if (response.ok) {
        setEventCount(prev => prev + 1);
        setLastEvent({ type: eventType, tier, quality, time: new Date() });
        setIsConnected(true);
        
        const tierLabel = tier ? ` (${tier})` : '';
        const qualityLabel = quality ? ` [${quality}]` : '';
        toast.success(`${eventType}${tierLabel}${qualityLabel}`, { duration: 1200 });
      } else {
        throw new Error('Server error');
      }
    } catch (error) {
      setIsConnected(false);
      toast.error('Failed to log event');
    }
  };

  const getRoleLabel = () => {
    switch (deviceRole) {
      case 'RED_STRIKING': return 'STRIKING';
      case 'RED_GRAPPLING': return 'GRAPPLING';
      case 'BLUE_ALL': return 'ALL EVENTS';
      default: return deviceRole;
    }
  };

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Role Banner - Large, clear indicator */}
      <div className={`${corner === 'RED' ? 'bg-red-600' : 'bg-blue-600'} py-2 text-center`}>
        <span className="text-white font-black text-lg tracking-wider">
          {corner} CORNER — {getRoleLabel()}
        </span>
      </div>

      {/* Header */}
      <div className="bg-slate-900 border-b border-slate-700 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button 
              size="sm" 
              variant="ghost" 
              onClick={() => navigate('/operator-setup')}
              className="text-slate-400 hover:text-white"
            >
              <ArrowLeft className="w-4 h-4" />
            </Button>
            <div>
              <div className="text-white font-semibold">{operatorName}</div>
              <div className="text-slate-400 text-xs flex items-center gap-1">
                <Keyboard className="w-3 h-3" /> Keyboard enabled
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge className={`${isConnected ? 'bg-green-600' : 'bg-red-600'} text-white`}>
              {isConnected ? <Wifi className="w-3 h-3 mr-1" /> : <WifiOff className="w-3 h-3 mr-1" />}
              {isConnected ? 'LIVE' : 'OFFLINE'}
            </Badge>
          </div>
        </div>
      </div>

      {/* Fighter Name & Round */}
      <div className="bg-slate-900 px-4 py-4 border-b border-slate-800">
        <div className="text-center">
          <div className={`text-3xl font-black ${corner === 'RED' ? 'text-red-400' : 'text-blue-400'}`}>
            {fighterName}
          </div>
          <div className="flex items-center justify-center gap-4 mt-2">
            <span className="text-slate-400">Round</span>
            <span className={`text-2xl font-bold ${roundJustChanged ? 'text-green-400 animate-pulse' : 'text-white'}`}>
              {currentRound}
            </span>
            <span className="text-slate-500">of {totalRounds}</span>
            <span className="text-slate-600">•</span>
            <span className="text-slate-400">{eventCount} events</span>
          </div>
        </div>
      </div>

      {/* Event Buttons - Clean grid */}
      <div className="p-3">
        {/* Section: Strikes - Arranged in pairs: Jab/Cross, Hook/Uppercut, Kick/Knee, Elbow */}
        {(deviceRole === 'RED_STRIKING' || deviceRole === 'BLUE_ALL') && (
          <div className="mb-4">
            <div className="text-slate-500 text-xs font-semibold uppercase tracking-wider mb-2 px-1">
              Strikes
            </div>
            <div className="grid grid-cols-4 gap-2">
              {/* Row 1: Jab, Hook, Kick, Elbow */}
              <Button
                data-testid="btn-jab"
                onClick={() => logEvent('Jab')}
                className={`${getButtonStyle('strike', corner)} text-white font-semibold h-14 text-sm border transition-all active:scale-95`}
              >
                <div className="text-center">
                  <div>Jab</div>
                  <div className="text-[10px] text-slate-400">1</div>
                </div>
              </Button>
              <Button
                data-testid="btn-hook"
                onClick={() => logEvent('Hook')}
                className={`${getButtonStyle('strike', corner)} text-white font-semibold h-14 text-sm border transition-all active:scale-95`}
              >
                <div className="text-center">
                  <div>Hook</div>
                  <div className="text-[10px] text-slate-400">3</div>
                </div>
              </Button>
              <Button
                data-testid="btn-kick"
                onClick={() => logEvent('Kick')}
                className={`${getButtonStyle('strike', corner)} text-white font-semibold h-14 text-sm border transition-all active:scale-95`}
              >
                <div className="text-center">
                  <div>Kick</div>
                  <div className="text-[10px] text-slate-400">7</div>
                </div>
              </Button>
              <Button
                data-testid="btn-elbow"
                onClick={() => logEvent('Elbow')}
                className={`${getButtonStyle('strike', corner)} text-white font-semibold h-14 text-sm border transition-all active:scale-95`}
              >
                <div className="text-center">
                  <div>Elbow</div>
                  <div className="text-[10px] text-slate-400">5</div>
                </div>
              </Button>
              
              {/* Row 2: Cross, Uppercut, Knee */}
              <Button
                data-testid="btn-cross"
                onClick={() => logEvent('Cross')}
                className={`${getButtonStyle('strike', corner)} text-white font-semibold h-14 text-sm border transition-all active:scale-95`}
              >
                <div className="text-center">
                  <div>Cross</div>
                  <div className="text-[10px] text-slate-400">2</div>
                </div>
              </Button>
              <Button
                data-testid="btn-uppercut"
                onClick={() => logEvent('Uppercut')}
                className={`${getButtonStyle('strike', corner)} text-white font-semibold h-14 text-sm border transition-all active:scale-95`}
              >
                <div className="text-center">
                  <div>Uppercut</div>
                  <div className="text-[10px] text-slate-400">4</div>
                </div>
              </Button>
              <Button
                data-testid="btn-knee"
                onClick={() => logEvent('Knee')}
                className={`${getButtonStyle('strike', corner)} text-white font-semibold h-14 text-sm border transition-all active:scale-95`}
              >
                <div className="text-center">
                  <div>Knee</div>
                  <div className="text-[10px] text-slate-400">6</div>
                </div>
              </Button>
            </div>
          </div>
        )}

        {/* Section: Damage */}
        {(deviceRole === 'RED_STRIKING' || deviceRole === 'BLUE_ALL') && (
          <div className="mb-4">
            <div className="text-slate-500 text-xs font-semibold uppercase tracking-wider mb-2 px-1">
              Damage
            </div>
            <div className="grid grid-cols-4 gap-2">
              <Button
                data-testid="btn-rocked"
                onClick={() => logEvent('Rocked/Stunned')}
                className={`${getButtonStyle('damage', corner)} text-white font-semibold h-14 text-sm border transition-all active:scale-95`}
              >
                <div className="text-center">
                  <div>Rocked</div>
                  <div className="text-[10px] text-amber-200">Q</div>
                </div>
              </Button>
              {[
                { tier: 'Flash', key: 'W' },
                { tier: 'Hard', key: 'E' },
                { tier: 'Near-Finish', key: 'R' }
              ].map((kd) => (
                <Button
                  key={kd.tier}
                  data-testid={`btn-kd-${kd.tier.toLowerCase()}`}
                  onClick={() => logEvent('KD', kd.tier)}
                  className={`${getButtonStyle('damage-kd', corner)} text-white font-semibold h-14 text-sm border transition-all active:scale-95`}
                >
                  <div className="text-center">
                    <div>KD {kd.tier}</div>
                    <div className="text-[10px] text-red-200">{kd.key}</div>
                  </div>
                </Button>
              ))}
            </div>
          </div>
        )}

        {/* Section: Grappling */}
        {(deviceRole === 'RED_GRAPPLING' || deviceRole === 'BLUE_ALL') && (
          <div className="mb-4">
            <div className="text-slate-500 text-xs font-semibold uppercase tracking-wider mb-2 px-1">
              Grappling
            </div>
            <div className="grid grid-cols-3 gap-2">
              <Button
                data-testid="btn-td-landed"
                onClick={() => logEvent('Takedown Landed')}
                className={`${getButtonStyle('grappling', corner)} text-white font-semibold h-14 text-sm border transition-all active:scale-95`}
              >
                <div className="text-center">
                  <div>TD Landed</div>
                  <div className="text-[10px] text-emerald-200">V</div>
                </div>
              </Button>
              <Button
                data-testid="btn-td-defended"
                onClick={() => logEvent('Takedown Defended')}
                className={`${getButtonStyle('grappling', corner)} text-white font-semibold h-14 text-sm border transition-all active:scale-95`}
              >
                <div className="text-center">
                  <div>TD Defended</div>
                  <div className="text-[10px] text-emerald-200">B</div>
                </div>
              </Button>
              {/* Ground Strike with quality indicator */}
              <div className="flex flex-col gap-1">
                <Button
                  data-testid="btn-ground-strike"
                  onClick={() => logEvent('Ground Strike', null, groundStrikeQuality)}
                  className={`${groundStrikeQuality === 'SOLID' ? 'bg-red-600 hover:bg-red-500 border-red-500' : 'bg-red-400 hover:bg-red-300 border-red-400'} text-white font-semibold h-10 text-sm border transition-all active:scale-95`}
                >
                  <div className="text-center">
                    <div>{groundStrikeQuality === 'SOLID' ? 'GnP Solid' : 'GnP Light'}</div>
                    <div className="text-[10px] text-white/80">G</div>
                  </div>
                </Button>
                <Button
                  data-testid="btn-ground-strike-toggle"
                  onClick={() => setGroundStrikeQuality(prev => prev === 'SOLID' ? 'LIGHT' : 'SOLID')}
                  className={`${groundStrikeQuality === 'SOLID' ? 'bg-red-800 hover:bg-red-700' : 'bg-red-600 hover:bg-red-500'} text-white font-medium h-6 text-[10px] border-0 transition-all`}
                >
                  Switch to {groundStrikeQuality === 'SOLID' ? 'Light' : 'Solid'} (F)
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Section: Control - With Timers */}
        {(deviceRole === 'RED_GRAPPLING' || deviceRole === 'BLUE_ALL') && (
          <div className="mb-4">
            <div className="text-slate-500 text-xs font-semibold uppercase tracking-wider mb-2 px-1 flex items-center">
              Control Time 
              {activeControl && (
                <span className="ml-2 flex items-center text-green-400">
                  <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse mr-1"></span>
                  RECORDING {activeControl.toUpperCase()}
                </span>
              )}
            </div>
            <div className="grid grid-cols-3 gap-2">
              {[
                { name: 'Back Control', key: 'Z' },
                { name: 'Top Control', key: 'X' },
                { name: 'Cage Control', key: 'C' }
              ].map((control) => {
                const isActive = activeControl === control.name;
                const totalTime = controlTotals[control.name] + (isActive ? controlTime : 0);
                
                return (
                  <Button
                    key={control.name}
                    data-testid={`btn-${control.name.toLowerCase().replace(' ', '-')}`}
                    onClick={() => handleControlToggle(control.name)}
                    className={`${isActive ? getButtonStyle('control-active', corner) : getButtonStyle('control', corner)} text-white font-semibold h-20 text-sm border transition-all active:scale-95`}
                  >
                    <div className="text-center">
                      <div className="text-xs">{control.name}</div>
                      {isActive ? (
                        <>
                          <div className="text-xl font-bold text-green-200">{formatTime(totalTime)}</div>
                          <div className="text-[9px] text-green-300">Tap to stop</div>
                        </>
                      ) : (
                        <>
                          {totalTime > 0 ? (
                            <div className="text-lg font-bold text-cyan-300">{formatTime(totalTime)}</div>
                          ) : (
                            <div className="text-[10px] text-cyan-200 mt-1">{control.key}</div>
                          )}
                          <div className="text-[9px] text-slate-400">{totalTime > 0 ? 'Tap to add more' : 'Tap to start'}</div>
                        </>
                      )}
                    </div>
                  </Button>
                );
              })}
            </div>
            {activeControl && (
              <div className="mt-2 text-center text-sm text-green-400">
                Tap the active button again to stop and log the control time
              </div>
            )}
          </div>
        )}

        {/* Section: Submissions */}
        {(deviceRole === 'RED_GRAPPLING' || deviceRole === 'BLUE_ALL') && (
          <div className="mb-4">
            <div className="text-slate-500 text-xs font-semibold uppercase tracking-wider mb-2 px-1">
              Submissions
            </div>
            <div className="grid grid-cols-3 gap-2">
              {[
                { tier: 'Standard', key: 'A', label: 'Sub Attempt' },
                { tier: 'Deep', key: 'S', label: 'Sub Deep' },
                { tier: 'Near-Finish', key: 'D', label: 'Sub Near-Finish' }
              ].map((sub) => (
                <Button
                  key={sub.tier}
                  data-testid={`btn-sub-${sub.tier.toLowerCase()}`}
                  onClick={() => logEvent('Submission Attempt', sub.tier)}
                  className={`${getButtonStyle('submission', corner)} text-white font-semibold h-14 text-sm border transition-all active:scale-95`}
                >
                  <div className="text-center">
                    <div>{sub.label}</div>
                    <div className="text-[10px] text-purple-200">{sub.key}</div>
                  </div>
                </Button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Last Event - Fixed at bottom */}
      <div className="fixed bottom-0 left-0 right-0 bg-slate-900 border-t border-slate-700 p-3">
        {lastEvent ? (
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber-400" />
              <span className="text-white font-medium">
                {lastEvent.type}{lastEvent.tier ? ` (${lastEvent.tier})` : ''}
              </span>
            </div>
            <span className="text-slate-400 text-sm">
              {lastEvent.time.toLocaleTimeString()}
            </span>
          </div>
        ) : (
          <div className="text-slate-500 text-center text-sm">
            No events logged yet — tap a button or use keyboard shortcuts
          </div>
        )}
      </div>
    </div>
  );
}
