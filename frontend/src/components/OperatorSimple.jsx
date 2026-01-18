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
const STRIKING_EVENTS = [
  // Basic Strikes - Neutral dark
  { type: 'Jab', category: 'strike', tier: null, key: '1' },
  { type: 'Cross', category: 'strike', tier: null, key: '2' },
  { type: 'Hook', category: 'strike', tier: null, key: '3' },
  { type: 'Uppercut', category: 'strike', tier: null, key: '4' },
  { type: 'Elbow', category: 'strike', tier: null, key: '5' },
  { type: 'Knee', category: 'strike', tier: null, key: '6' },
  { type: 'Kick', category: 'strike', tier: null, key: '7' },
  { type: 'Ground Strike', category: 'strike', tier: null, key: '8', label: 'Ground Strike' },
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
  // Control
  { type: 'Back Control', category: 'control', tier: null, label: 'Back Control' },
  { type: 'Mount Control', category: 'control', tier: null, label: 'Mount' },
  { type: 'Side Control', category: 'control', tier: null, label: 'Side Control' },
  // Submissions - Escalating danger
  { type: 'Submission Attempt', category: 'submission', tier: 'Standard', key: 'A', label: 'Sub Attempt' },
  { type: 'Submission Attempt', category: 'submission', tier: 'Deep', key: 'S', label: 'Sub Deep' },
  { type: 'Submission Attempt', category: 'submission', tier: 'Near-Finish', key: 'D', label: 'Sub Near-Finish' },
  // Ground Strike
  { type: 'Ground Strike', category: 'strike', tier: null, key: 'G', label: 'Ground Strike' },
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
    default:
      return 'bg-slate-700 hover:bg-slate-600 border-slate-600';
  }
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

  // Determine corner from role
  const corner = deviceRole.startsWith('RED') ? 'RED' : 'BLUE';
  const fighterName = corner === 'RED' ? boutInfo.fighter1 : boutInfo.fighter2;
  
  // Determine which events to show
  const getEventsForRole = () => {
    if (deviceRole === 'RED_STRIKING') return STRIKING_EVENTS;
    if (deviceRole === 'RED_GRAPPLING') return GRAPPLING_EVENTS;
    if (deviceRole === 'BLUE_ALL') return [...STRIKING_EVENTS, ...GRAPPLING_EVENTS.filter(e => e.type !== 'Ground Strike')];
    return STRIKING_EVENTS;
  };

  // Keyboard shortcuts handler
  useEffect(() => {
    const handleKeyDown = async (event) => {
      if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') return;
      if (!boutId) return;

      const key = event.key;
      const shortcutKeys = ['1', '2', '3', '4', '5', '6', '7', '8', 't', 'v', 'b', 'a', 's', 'd', 'q', 'w', 'e', 'r', 'g'];
      
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
        else if (key === '8' || key.toLowerCase() === 'g') { await logEvent('Ground Strike'); }
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
      } catch (error) {
        console.error('Keyboard shortcut error:', error);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [boutId, corner, currentRound, deviceRole, fighterName]);

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
  const logEvent = async (eventType, tier = null) => {
    try {
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
          metadata: tier ? { tier } : {}
        })
      });
      
      if (response.ok) {
        setEventCount(prev => prev + 1);
        setLastEvent({ type: eventType, tier, time: new Date() });
        setIsConnected(true);
        
        const tierLabel = tier ? ` (${tier})` : '';
        toast.success(`${eventType}${tierLabel}`, { duration: 1200 });
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
        {/* Section: Strikes */}
        {(deviceRole === 'RED_STRIKING' || deviceRole === 'BLUE_ALL') && (
          <div className="mb-4">
            <div className="text-slate-500 text-xs font-semibold uppercase tracking-wider mb-2 px-1">
              Strikes
            </div>
            <div className="grid grid-cols-4 gap-2">
              {['Jab', 'Cross', 'Hook', 'Uppercut', 'Elbow', 'Knee', 'Kick', 'Ground Strike'].map((strike, idx) => (
                <Button
                  key={strike}
                  data-testid={`btn-${strike.toLowerCase().replace(' ', '-')}`}
                  onClick={() => logEvent(strike)}
                  className={`${getButtonStyle('strike', corner)} text-white font-semibold h-14 text-sm border transition-all active:scale-95`}
                >
                  <div className="text-center">
                    <div>{strike}</div>
                    <div className="text-[10px] text-slate-400">{idx + 1 === 8 ? '8/G' : idx + 1}</div>
                  </div>
                </Button>
              ))}
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
              <div></div>
            </div>
          </div>
        )}

        {/* Section: Control */}
        {(deviceRole === 'RED_GRAPPLING' || deviceRole === 'BLUE_ALL') && (
          <div className="mb-4">
            <div className="text-slate-500 text-xs font-semibold uppercase tracking-wider mb-2 px-1">
              Control Position
            </div>
            <div className="grid grid-cols-3 gap-2">
              {['Back Control', 'Mount', 'Side Control'].map((control) => (
                <Button
                  key={control}
                  data-testid={`btn-${control.toLowerCase().replace(' ', '-')}`}
                  onClick={() => logEvent(control === 'Mount' ? 'Mount Control' : control)}
                  className={`${getButtonStyle('control', corner)} text-white font-semibold h-14 text-sm border transition-all active:scale-95`}
                >
                  {control}
                </Button>
              ))}
            </div>
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
