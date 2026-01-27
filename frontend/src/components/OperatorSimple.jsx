import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { toast } from 'sonner';
import { 
  Swords, 
  Shield, 
  Target,
  Wifi,
  WifiOff,
  ArrowLeft,
  Zap,
  Keyboard,
  Info,
  Clock,
  Plus,
  Minus,
  Maximize,
  Minimize
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

// Significant Strike Events (SS) - Double point value
const SS_EVENTS = [
  { type: 'SS Jab', category: 'ss', tier: null, key: '!', label: 'SS Jab' },
  { type: 'SS Cross', category: 'ss', tier: null, key: '@', label: 'SS Cross' },
  { type: 'SS Hook', category: 'ss', tier: null, key: '#', label: 'SS Hook' },
  { type: 'SS Uppercut', category: 'ss', tier: null, key: '$', label: 'SS Upper' },
  { type: 'SS Elbow', category: 'ss', tier: null, key: '%', label: 'SS Elbow' },
  { type: 'SS Knee', category: 'ss', tier: null, key: '^', label: 'SS Knee' },
  { type: 'SS Kick', category: 'ss', tier: null, key: '&', label: 'SS Kick' },
];

const GRAPPLING_EVENTS = [
  // Takedowns
  { type: 'Takedown', category: 'grappling', tier: null, key: 'V', label: 'Takedown' },
  { type: 'Takedown Stuffed', category: 'grappling', tier: null, key: 'B', label: 'TD Stuffed' },
  // Ground Strike - belongs with grappling
  { type: 'Ground Strike', category: 'strike', tier: null, key: 'G', label: 'GnP' },
  // Submissions - Escalating danger
  { type: 'Submission Attempt', category: 'submission', tier: 'Light', key: 'A', label: 'Sub Light' },
  { type: 'Submission Attempt', category: 'submission', tier: 'Deep', key: 'S', label: 'Sub Deep' },
  { type: 'Submission Attempt', category: 'submission', tier: 'Near-Finish', key: 'D', label: 'Sub NF' },
];

// Tooltips for event types (shown on hover/long-press)
const EVENT_TOOLTIPS = {
  // Basic Strikes
  'Jab': 'Quick punch with lead hand. 1.5 points.',
  'Cross': 'Straight punch with rear hand. 3 points.',
  'Hook': 'Curved punch to the side. 3 points.',
  'Uppercut': 'Upward punch to chin. 3 points.',
  'Elbow': 'Elbow strike. 4 points.',
  'Knee': 'Knee strike. 4 points.',
  'Kick': 'Any kick (body, leg, head). 3 points.',
  
  // Significant Strikes (SS)
  'SS Jab': 'SIGNIFICANT: Clean, impactful jab that visibly affects opponent. 2 points.',
  'SS Cross': 'SIGNIFICANT: Power cross that lands clean with visible impact. 4.5 points.',
  'SS Hook': 'SIGNIFICANT: Hook that lands clean with visible effect. 4.5 points.',
  'SS Uppercut': 'SIGNIFICANT: Clean uppercut with visible impact. 4.5 points.',
  'SS Elbow': 'SIGNIFICANT: Clean elbow that cuts or staggers. 6 points.',
  'SS Knee': 'SIGNIFICANT: Knee that lands clean with visible effect. 6 points.',
  'SS Kick': 'SIGNIFICANT: Clean, impactful kick with visible damage. 6 points.',
  
  // Damage Events
  'Rocked/Stunned': 'Fighter visibly hurt/wobbled but not knocked down. 60 points.',
  'KD Flash': 'Quick knockdown - fighter touches canvas but recovers immediately. 100 points. IMPACT LOCK: Winner unless opponent leads by 50+ points.',
  'KD Hard': 'Fighter goes down and needs time to recover. 150 points. IMPACT LOCK: Winner unless opponent leads by 110+ points.',
  'KD Near-Finish': 'Fighter badly hurt - referee could have stopped it. 210 points. IMPACT LOCK: Winner unless opponent leads by 150+ points.',
  
  // Grappling
  'Takedown': 'Successfully takes opponent to ground. 10 points.',
  'Takedown Stuffed': 'Defends a takedown attempt. 5 points (diminishing after 3).',
  'Ground Strike': 'Ground and pound strike. SOLID: 3 points, LIGHT: 1 point.',
  
  // Submissions
  'Submission Attempt Light': 'Light submission attempt, no real danger. 12 points.',
  'Submission Attempt Deep': 'Deep submission - opponent in danger. 28 points.',
  'Submission Attempt Near-Finish': 'Almost finished - tap or stop was imminent. 60 points. IMPACT LOCK.',
  
  // Control
  'Cage Control': 'Pressed against cage with control. 1 point per 10 seconds.',
  'Top Control': 'Dominant position on ground. 3 points per 10 seconds.',
  'Back Control': 'Back mount or back control. 5 points per 10 seconds.',
};

// Get button style based on category - clean, professional colors
const getButtonStyle = (category, corner) => {
  const isRed = corner === 'RED';
  
  switch (category) {
    case 'strike':
      return isRed 
        ? 'bg-slate-700 hover:bg-slate-600 border-slate-600' 
        : 'bg-slate-700 hover:bg-slate-600 border-slate-600';
    case 'ss':
      return 'bg-amber-700 hover:bg-amber-600 border-amber-500 ring-1 ring-amber-400/50';
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
    case 'control-bucket':
      return 'bg-cyan-800 hover:bg-cyan-700 border-cyan-600';
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
  
  // SS mode toggle - when enabled, all strikes are logged as SS
  const [ssMode, setSsMode] = useState(false);
  
  // Control bucket mode - for quick time logging
  const [showControlBuckets, setShowControlBuckets] = useState(false);

  // Determine corner from role
  const corner = deviceRole.startsWith('RED') ? 'RED' : 'BLUE';
  const fighterName = corner === 'RED' ? boutInfo.fighter1 : boutInfo.fighter2;
  
  // Determine which events to show
  const getEventsForRole = () => {
    if (deviceRole === 'RED_STRIKING' || deviceRole === 'BLUE_STRIKING') return STRIKING_EVENTS;
    if (deviceRole === 'RED_GRAPPLING' || deviceRole === 'BLUE_GRAPPLING') return GRAPPLING_EVENTS;
    if (deviceRole === 'RED_ALL' || deviceRole === 'BLUE_ALL') return [...STRIKING_EVENTS, ...GRAPPLING_EVENTS];
    return STRIKING_EVENTS;
  };
  
  // Check if role includes grappling
  const hasGrappling = deviceRole.includes('GRAPPLING') || deviceRole.includes('ALL');
  const hasStriking = deviceRole.includes('STRIKING') || deviceRole.includes('ALL');
  
  // Log control time bucket (quick add without timer)
  const logControlBucket = async (controlType, seconds) => {
    try {
      const eventType = controlType === 'Top' ? 'Ground Top Control' : 
                       controlType === 'Cage' ? 'Cage Control Time' :
                       controlType === 'Back' ? 'Ground Back Control' : controlType;
      
      const response = await fetch(`${API}/api/events`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          bout_id: boutId,
          round_number: currentRound,
          corner: corner,
          aspect: 'GRAPPLING',
          event_type: eventType,
          device_role: deviceRole,
          metadata: { 
            duration: seconds,
            bucket_entry: true
          }
        })
      });
      
      if (response.ok) {
        setEventCount(prev => prev + 1);
        setLastEvent({ type: `${controlType} Control`, tier: `${seconds}s`, time: new Date() });
        toast.success(`${controlType} Control: ${seconds}s logged`);
      }
    } catch (error) {
      toast.error('Failed to log control time');
    }
  };

  // Keyboard shortcuts handler
  useEffect(() => {
    const handleKeyDown = async (event) => {
      if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') return;
      if (!boutId) return;

      const key = event.key;
      const shiftKey = event.shiftKey;
      
      // List of shortcut keys we handle
      const shortcutKeys = ['1', '2', '3', '4', '5', '6', '7', 't', 'T', 'v', 'b', 'a', 's', 'd', 'q', 'w', 'e', 'r', 'g', 'z', 'x', 'c', 'f', '`', '~', '!', '@', '#', '$', '%', '^', 'F2', 'F3', 'F4', 'F5'];
      
      if (shortcutKeys.includes(key) || shortcutKeys.includes(key.toLowerCase())) {
        event.preventDefault();
      }

      try {
        // Toggle SS mode with backtick/tilde
        if (key === '`' || key === '~') {
          setSsMode(prev => !prev);
          toast.info(`SS Mode: ${!ssMode ? 'ON' : 'OFF'}`, { duration: 800 });
          return;
        }
        
        // SS STRIKES (Shift + number) - Red Dragon K585 layout
        if (key === '!' || (shiftKey && key === '1')) { await logEvent('SS Jab'); return; }
        if (key === '@' || (shiftKey && key === '2')) { await logEvent('SS Cross'); return; }
        if (key === '#' || (shiftKey && key === '3')) { await logEvent('SS Hook'); return; }
        if (key === '$' || (shiftKey && key === '4')) { await logEvent('SS Uppercut'); return; }
        if (key === '%' || (shiftKey && key === '5')) { await logEvent('SS Elbow'); return; }
        if (key === '^' || (shiftKey && key === '6')) { await logEvent('SS Knee'); return; }
        
        // SS Kick = Shift+T
        if (key === 'T' || (shiftKey && key.toLowerCase() === 't')) { await logEvent('SS Kick'); return; }
        
        // STRIKING (regular - no shift)
        if (key === '1' && !shiftKey) { await logEvent(ssMode ? 'SS Jab' : 'Jab'); }
        else if (key === '2' && !shiftKey) { await logEvent(ssMode ? 'SS Cross' : 'Cross'); }
        else if (key === '3' && !shiftKey) { await logEvent(ssMode ? 'SS Hook' : 'Hook'); }
        else if (key === '4' && !shiftKey) { await logEvent(ssMode ? 'SS Uppercut' : 'Uppercut'); }
        else if (key === '5' && !shiftKey) { await logEvent(ssMode ? 'SS Elbow' : 'Elbow'); }
        else if (key === '6' && !shiftKey) { await logEvent(ssMode ? 'SS Knee' : 'Knee'); }
        // Kick = T (lowercase only, Shift+T is SS Kick)
        else if (key === 't' && !shiftKey) { await logEvent(ssMode ? 'SS Kick' : 'Kick'); }
        
        // DAMAGE - G2=F2, G3=F3, G4=F4, G5=F5 (program your Red Dragon macro keys to send F2-F5)
        else if (key === 'F2') { await logEvent('Rocked'); }       // G2 -> F2
        else if (key === 'F3') { await logEvent('KD', 'Flash'); }  // G3 -> F3
        else if (key === 'F4') { await logEvent('KD', 'Hard'); }   // G4 -> F4
        else if (key === 'F5') { await logEvent('KD', 'Near-Finish'); } // G5 -> F5
        // Fallback: Q, W, E, R still work for damage
        else if (key.toLowerCase() === 'q') { await logEvent('Rocked'); }
        else if (key.toLowerCase() === 'w') { await logEvent('KD', 'Flash'); }
        else if (key.toLowerCase() === 'e') { await logEvent('KD', 'Hard'); }
        else if (key.toLowerCase() === 'r') { await logEvent('KD', 'Near-Finish'); }
        
        // Ground Strike - G for Solid, F for Light
        else if (key.toLowerCase() === 'g' && !shiftKey) { 
          if (hasGrappling) {
            await logEvent('Ground Strike', null, 'SOLID'); 
          }
        }
        else if (key.toLowerCase() === 'f' && !shiftKey) {
          if (hasGrappling) {
            await logEvent('Ground Strike', null, 'LIGHT');
          }
        }
        // GRAPPLING
        else if (key.toLowerCase() === 'v') { await logEvent('Takedown'); }
        else if (key.toLowerCase() === 'b') { await logEvent('Takedown Stuffed'); }
        // SUBMISSIONS
        else if (key.toLowerCase() === 'a') { await logEvent('Submission Attempt', 'Light'); }
        else if (key.toLowerCase() === 's') { await logEvent('Submission Attempt', 'Deep'); }
        else if (key.toLowerCase() === 'd') { await logEvent('Submission Attempt', 'Near-Finish'); }
        // Control timers - Z, X, C (only for grappling roles)
        else if (key.toLowerCase() === 'z') { 
          if (hasGrappling) handleControlToggle('Back Control'); 
        }
        else if (key.toLowerCase() === 'x') { 
          if (hasGrappling) handleControlToggle('Top Control'); 
        }
        else if (key.toLowerCase() === 'c') { 
          if (hasGrappling) handleControlToggle('Cage Control'); 
        }
      } catch (error) {
        console.error('Keyboard shortcut error:', error);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [boutId, corner, currentRound, deviceRole, fighterName, activeControl, groundStrikeQuality, ssMode, hasGrappling]);

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
      
      // Log CTRL_END event
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
              control_type: controlType === 'Top Control' ? 'TOP' : 
                           controlType === 'Cage Control' ? 'CAGE' :
                           controlType === 'Back Control' ? 'BACK' : 'TOP'
            }
          })
        });
      } catch (error) {
        console.error('Failed to log CTRL_END');
      }
      
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
      case 'RED_ALL': return 'ALL EVENTS';
      case 'RED_STRIKING': return 'STRIKING';
      case 'RED_GRAPPLING': return 'GRAPPLING';
      case 'BLUE_ALL': return 'ALL EVENTS';
      case 'BLUE_STRIKING': return 'STRIKING';
      case 'BLUE_GRAPPLING': return 'GRAPPLING';
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
      <TooltipProvider delayDuration={300}>
        <div className="p-3">
          {/* Section: Strikes - Each strike has main button + SS button */}
          {hasStriking && (
            <div className="mb-4">
              <div className="text-slate-500 text-xs font-semibold uppercase tracking-wider mb-2 px-1">
                Strikes
              </div>
              <div className="grid grid-cols-2 gap-2">
                {/* Row 1: Jab, Cross */}
                {[
                  { type: 'Jab', key: '1', ssType: 'SS Jab', ssKey: '⇧1' },
                  { type: 'Cross', key: '2', ssType: 'SS Cross', ssKey: '⇧2' },
                ].map(strike => (
                  <div key={strike.type} className="flex gap-1">
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          data-testid={`btn-${strike.type.toLowerCase()}`}
                          onClick={() => logEvent(strike.type)}
                          className={`${getButtonStyle('strike', corner)} text-white font-bold ${deviceRole.includes('ALL') ? 'h-12' : 'h-16'} text-lg flex-1 border transition-all active:scale-95`}
                        >
                          <div className="text-center">
                            <div className={deviceRole.includes('ALL') ? 'text-base' : 'text-xl'}>{strike.type}</div>
                            <div className="text-[10px] text-slate-400 font-normal">{strike.key}</div>
                          </div>
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent><p>{EVENT_TOOLTIPS[strike.type]}</p></TooltipContent>
                    </Tooltip>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          data-testid={`btn-ss-${strike.type.toLowerCase()}`}
                          onClick={() => logEvent(strike.ssType)}
                          className={`${getButtonStyle('ss', corner)} text-white font-bold ${deviceRole.includes('ALL') ? 'h-12 w-12' : 'h-16 w-14'} text-sm border transition-all active:scale-95`}
                        >
                          <div className="text-center">
                            <div className={deviceRole.includes('ALL') ? 'text-sm' : 'text-base'}>SS</div>
                          </div>
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent><p>{EVENT_TOOLTIPS[strike.ssType]}</p></TooltipContent>
                    </Tooltip>
                  </div>
                ))}
                
                {/* Row 2: Hook, Uppercut */}
                {[
                  { type: 'Hook', key: '3', ssType: 'SS Hook', ssKey: '⇧3' },
                  { type: 'Uppercut', key: '4', ssType: 'SS Uppercut', ssKey: '⇧4' },
                ].map(strike => (
                  <div key={strike.type} className="flex gap-1">
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          data-testid={`btn-${strike.type.toLowerCase()}`}
                          onClick={() => logEvent(strike.type)}
                          className={`${getButtonStyle('strike', corner)} text-white font-bold ${deviceRole.includes('ALL') ? 'h-12' : 'h-16'} text-lg flex-1 border transition-all active:scale-95`}
                        >
                          <div className="text-center">
                            <div className={deviceRole.includes('ALL') ? 'text-base' : 'text-xl'}>{strike.type}</div>
                            <div className="text-[10px] text-slate-400 font-normal">{strike.key}</div>
                          </div>
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent><p>{EVENT_TOOLTIPS[strike.type]}</p></TooltipContent>
                    </Tooltip>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          data-testid={`btn-ss-${strike.type.toLowerCase()}`}
                          onClick={() => logEvent(strike.ssType)}
                          className={`${getButtonStyle('ss', corner)} text-white font-bold ${deviceRole.includes('ALL') ? 'h-12 w-12' : 'h-16 w-14'} text-sm border transition-all active:scale-95`}
                        >
                          <div className="text-center">
                            <div className={deviceRole.includes('ALL') ? 'text-sm' : 'text-base'}>SS</div>
                          </div>
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent><p>{EVENT_TOOLTIPS[strike.ssType]}</p></TooltipContent>
                    </Tooltip>
                  </div>
                ))}
                
                {/* Row 3: Kick, Knee */}
                {[
                  { type: 'Kick', key: 'T', ssType: 'SS Kick', ssKey: '⇧T' },
                  { type: 'Knee', key: '6', ssType: 'SS Knee', ssKey: '⇧6' },
                ].map(strike => (
                  <div key={strike.type} className="flex gap-1">
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          data-testid={`btn-${strike.type.toLowerCase()}`}
                          onClick={() => logEvent(strike.type)}
                          className={`${getButtonStyle('strike', corner)} text-white font-bold ${deviceRole.includes('ALL') ? 'h-12' : 'h-16'} text-lg flex-1 border transition-all active:scale-95`}
                        >
                          <div className="text-center">
                            <div className={deviceRole.includes('ALL') ? 'text-base' : 'text-xl'}>{strike.type}</div>
                            <div className="text-[10px] text-slate-400 font-normal">{strike.key}</div>
                          </div>
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent><p>{EVENT_TOOLTIPS[strike.type]}</p></TooltipContent>
                    </Tooltip>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          data-testid={`btn-ss-${strike.type.toLowerCase()}`}
                          onClick={() => logEvent(strike.ssType)}
                          className={`${getButtonStyle('ss', corner)} text-white font-bold ${deviceRole.includes('ALL') ? 'h-12 w-12' : 'h-16 w-14'} text-sm border transition-all active:scale-95`}
                        >
                          <div className="text-center">
                            <div className={deviceRole.includes('ALL') ? 'text-sm' : 'text-base'}>SS</div>
                          </div>
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent><p>{EVENT_TOOLTIPS[strike.ssType]}</p></TooltipContent>
                    </Tooltip>
                  </div>
                ))}
                
                {/* Row 4: Elbow (single with SS) */}
                {[
                  { type: 'Elbow', key: '5', ssType: 'SS Elbow', ssKey: '⇧5' },
                ].map(strike => (
                  <div key={strike.type} className="flex gap-1">
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          data-testid={`btn-${strike.type.toLowerCase()}`}
                          onClick={() => logEvent(strike.type)}
                          className={`${getButtonStyle('strike', corner)} text-white font-bold ${deviceRole.includes('ALL') ? 'h-12' : 'h-16'} text-lg flex-1 border transition-all active:scale-95`}
                        >
                          <div className="text-center">
                            <div className={deviceRole.includes('ALL') ? 'text-base' : 'text-xl'}>{strike.type}</div>
                            <div className="text-[10px] text-slate-400 font-normal">{strike.key}</div>
                          </div>
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent><p>{EVENT_TOOLTIPS[strike.type]}</p></TooltipContent>
                    </Tooltip>
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <Button
                          data-testid={`btn-ss-${strike.type.toLowerCase()}`}
                          onClick={() => logEvent(strike.ssType)}
                          className={`${getButtonStyle('ss', corner)} text-white font-bold ${deviceRole.includes('ALL') ? 'h-12 w-12' : 'h-16 w-14'} text-sm border transition-all active:scale-95`}
                        >
                          <div className="text-center">
                            <div className={deviceRole.includes('ALL') ? 'text-sm' : 'text-base'}>SS</div>
                          </div>
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent><p>{EVENT_TOOLTIPS[strike.ssType]}</p></TooltipContent>
                    </Tooltip>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Section: Damage */}
          {hasStriking && (
            <div className="mb-4">
              <div className="text-slate-500 text-xs font-semibold uppercase tracking-wider mb-2 px-1">
                Damage
              </div>
              <div className="grid grid-cols-4 gap-2">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      data-testid="btn-rocked"
                      onClick={() => logEvent('Rocked')}
                      className={`${getButtonStyle('damage', corner)} text-white font-bold ${deviceRole.includes('ALL') ? 'h-10 text-sm' : 'h-16 text-base'} border transition-all active:scale-95`}
                    >
                      <div className="text-center">
                        <div className={deviceRole.includes('ALL') ? 'text-sm' : 'text-lg'}>Rocked</div>
                        <div className="text-[10px] text-amber-200 font-normal">G2/F2</div>
                      </div>
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{EVENT_TOOLTIPS['Rocked/Stunned']}</p>
                  </TooltipContent>
                </Tooltip>
                {[
                  { tier: 'Flash', key: 'G3/F3', label: 'KD Flash' },
                  { tier: 'Hard', key: 'G4/F4', label: 'KD Hard' },
                  { tier: 'Near-Finish', key: 'G5/F5', label: 'KD NF' }
                ].map((kd) => (
                  <Tooltip key={kd.tier}>
                    <TooltipTrigger asChild>
                      <Button
                        data-testid={`btn-kd-${kd.tier.toLowerCase()}`}
                        onClick={() => logEvent('KD', kd.tier)}
                        className={`${getButtonStyle('damage-kd', corner)} text-white font-bold ${deviceRole.includes('ALL') ? 'h-10 text-sm' : 'h-16 text-base'} border transition-all active:scale-95`}
                      >
                        <div className="text-center">
                          <div className={deviceRole.includes('ALL') ? 'text-sm' : 'text-lg'}>{kd.label}</div>
                          <div className="text-[10px] text-red-200 font-normal">{kd.key}</div>
                        </div>
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent className="max-w-xs">
                      <p>{EVENT_TOOLTIPS[`KD ${kd.tier}`]}</p>
                    </TooltipContent>
                  </Tooltip>
                ))}
              </div>
            </div>
          )}

          {/* Section: Grappling */}
          {hasGrappling && (
            <div className="mb-4">
              <div className="text-slate-500 text-xs font-semibold uppercase tracking-wider mb-2 px-1">
                Grappling
              </div>
              {/* 2x2 grid: Takedown/GnP Light on top, TD Stuffed/GnP Solid on bottom */}
              <div className="grid grid-cols-2 gap-2">
                {/* Row 1: Takedown, GnP Light */}
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      data-testid="btn-td"
                      onClick={() => logEvent('Takedown')}
                      className={`${getButtonStyle('grappling', corner)} text-white font-bold ${deviceRole.includes('ALL') ? 'h-12 text-sm' : 'h-16 text-base'} border transition-all active:scale-95`}
                    >
                      <div className="text-center">
                        <div className={deviceRole.includes('ALL') ? 'text-base' : 'text-lg'}>Takedown</div>
                        <div className="text-[10px] text-emerald-200 font-normal">V</div>
                      </div>
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{EVENT_TOOLTIPS['Takedown']}</p>
                  </TooltipContent>
                </Tooltip>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      data-testid="btn-gnp-light"
                      onClick={() => logEvent('Ground Strike', null, 'LIGHT')}
                      className={`bg-red-400 hover:bg-red-300 border-red-400 text-white font-bold ${deviceRole.includes('ALL') ? 'h-12 text-sm' : 'h-16 text-base'} border transition-all active:scale-95`}
                    >
                      <div className="text-center">
                        <div className={deviceRole.includes('ALL') ? 'text-base' : 'text-lg'}>GnP Light</div>
                        <div className="text-[10px] text-red-200 font-normal">F</div>
                      </div>
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Light ground strike, glancing blow. 1 point.</p>
                  </TooltipContent>
                </Tooltip>
                
                {/* Row 2: TD Stuffed, GnP Solid */}
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      data-testid="btn-td-stuffed"
                      onClick={() => logEvent('Takedown Stuffed')}
                      className={`${getButtonStyle('grappling', corner)} text-white font-bold ${deviceRole.includes('ALL') ? 'h-12 text-sm' : 'h-16 text-base'} border transition-all active:scale-95`}
                    >
                      <div className="text-center">
                        <div className={deviceRole.includes('ALL') ? 'text-base' : 'text-lg'}>TD Stuffed</div>
                        <div className="text-[10px] text-emerald-200 font-normal">B</div>
                      </div>
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{EVENT_TOOLTIPS['Takedown Stuffed']}</p>
                  </TooltipContent>
                </Tooltip>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      data-testid="btn-gnp-solid"
                      onClick={() => logEvent('Ground Strike', null, 'SOLID')}
                      className={`bg-red-600 hover:bg-red-500 border-red-500 text-white font-bold ${deviceRole.includes('ALL') ? 'h-12 text-sm' : 'h-16 text-base'} border transition-all active:scale-95`}
                    >
                      <div className="text-center">
                        <div className={deviceRole.includes('ALL') ? 'text-base' : 'text-lg'}>GnP Solid</div>
                        <div className="text-[10px] text-red-200 font-normal">G</div>
                      </div>
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Ground strike with solid impact. 3 points.</p>
                  </TooltipContent>
                </Tooltip>
              </div>
            </div>
          )}
          {/* Section: Control - With Timers and Buckets */}
          {hasGrappling && (
            <div className="mb-4">
              <div className="text-slate-500 text-xs font-semibold uppercase tracking-wider mb-2 px-1 flex items-center justify-between">
                <div className="flex items-center">
                  <Clock className="w-3 h-3 mr-1" />
                  Control Time 
                  {activeControl && (
                    <span className="ml-2 flex items-center text-green-400">
                      <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse mr-1"></span>
                      RECORDING
                    </span>
                  )}
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setShowControlBuckets(!showControlBuckets)}
                  className="text-cyan-400 text-xs h-5 px-2"
                >
                  {showControlBuckets ? 'Hide' : 'Quick Add'}
                </Button>
              </div>
              
              {/* Control Timer Buttons */}
              <div className="grid grid-cols-3 gap-2">
                {[
                  { name: 'Back Control', key: 'Z', short: 'Back' },
                  { name: 'Top Control', key: 'X', short: 'Top' },
                  { name: 'Cage Control', key: 'C', short: 'Cage' }
                ].map((control) => {
                  const isActive = activeControl === control.name;
                  const totalTime = controlTotals[control.name] + (isActive ? controlTime : 0);
                  
                  return (
                    <Tooltip key={control.name}>
                      <TooltipTrigger asChild>
                        <Button
                          data-testid={`btn-${control.name.toLowerCase().replace(' ', '-')}`}
                          onClick={() => handleControlToggle(control.name)}
                          className={`${isActive ? getButtonStyle('control-active', corner) : getButtonStyle('control', corner)} text-white font-semibold ${deviceRole.includes('ALL') ? 'h-12' : 'h-16'} text-sm border transition-all active:scale-95`}
                        >
                          <div className="text-center">
                            <div className="text-xs">{control.short}</div>
                            {isActive ? (
                              <>
                                <div className={`${deviceRole.includes('ALL') ? 'text-base' : 'text-lg'} font-bold text-green-200`}>{formatTime(totalTime)}</div>
                                <div className="text-[8px] text-green-300">Tap to stop</div>
                              </>
                            ) : (
                              <>
                                {totalTime > 0 ? (
                                  <div className={`${deviceRole.includes('ALL') ? 'text-xs' : 'text-sm'} font-bold text-cyan-300`}>{formatTime(totalTime)}</div>
                                ) : (
                                  <div className="text-[10px] text-cyan-200 mt-1">{control.key}</div>
                                )}
                              </>
                            )}
                          </div>
                        </Button>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>{EVENT_TOOLTIPS[control.name]}</p>
                      </TooltipContent>
                    </Tooltip>
                  );
                })}
              </div>
              
              {/* Control Bucket Quick Add (Hidden by default) */}
              {showControlBuckets && (
                <div className="mt-3 bg-slate-800/50 rounded-lg p-2">
                  <div className="text-slate-400 text-xs mb-2 text-center">Quick add control time (no timer)</div>
                  <div className="grid grid-cols-3 gap-2">
                    {['Back', 'Top', 'Cage'].map(type => (
                      <div key={type} className="space-y-1">
                        <div className="text-center text-xs text-cyan-400">{type}</div>
                        <div className="flex gap-1 justify-center">
                          {[10, 20, 30].map(secs => (
                            <Button
                              key={secs}
                              size="sm"
                              onClick={() => logControlBucket(type, secs)}
                              className={`${getButtonStyle('control-bucket', corner)} text-white text-xs h-7 px-2`}
                            >
                              +{secs}s
                            </Button>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Section: Submissions */}
          {hasGrappling && (
            <div className="mb-4">
              <div className="text-slate-500 text-xs font-semibold uppercase tracking-wider mb-2 px-1">
                Submissions
              </div>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { tier: 'Light', key: 'A', label: 'Sub Light' },
                  { tier: 'Deep', key: 'S', label: 'Sub Deep' },
                  { tier: 'Near-Finish', key: 'D', label: 'Sub NF' }
                ].map((sub) => (
                  <Tooltip key={sub.tier}>
                    <TooltipTrigger asChild>
                      <Button
                        data-testid={`btn-sub-${sub.tier.toLowerCase()}`}
                        onClick={() => logEvent('Submission Attempt', sub.tier)}
                        className={`${getButtonStyle('submission', corner)} text-white font-bold ${deviceRole.includes('ALL') ? 'h-10 text-sm' : 'h-16 text-base'} border transition-all active:scale-95`}
                      >
                        <div className="text-center">
                          <div className={deviceRole.includes('ALL') ? 'text-sm' : 'text-lg'}>{sub.label}</div>
                          <div className="text-[10px] text-purple-200 font-normal">{sub.key}</div>
                        </div>
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>
                      <p>{EVENT_TOOLTIPS[`Submission Attempt ${sub.tier}`]}</p>
                    </TooltipContent>
                  </Tooltip>
                ))}
              </div>
            </div>
          )}
        </div>
      </TooltipProvider>

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
